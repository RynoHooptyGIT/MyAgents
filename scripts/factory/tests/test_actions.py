import base64
import gzip
import json
import os
import subprocess
from pathlib import Path

import pytest

from .. import actions as A
from .. import gates as G
from .. import launcher as Lc
from .. import policy as pol
from ..proc import ProcResult, run as real_run

REPO = Path(__file__).resolve().parents[3]
POLICY = pol.load(REPO)
RID = "a1b2c3d4e5f60718"


def git(cwd, *args):
    env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t",
               GIT_COMMITTER_EMAIL="t@t")
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True, env=env).stdout


class Clock:
    def __init__(self):
        self.t = 0.0
        self.sleeps = []

    def now(self):
        return self.t

    def sleep(self, s):
        self.sleeps.append(s)
        self.t += s


class FakeGh:
    """Scripted `gh`: every other command goes to the real subprocess seam (real git)."""

    def __init__(self, artifacts=None, appear_after=0, conclusion="success", complete_after=0,
                 dispatch_rc=0, download_rc=0, title_override=None):
        self.calls = []
        self.dispatched = []
        self.artifacts = artifacts          # callable(fields) -> {filename: bytes} or None
        self.appear_after = appear_after
        self.complete_after = complete_after
        self.conclusion = conclusion
        self.dispatch_rc = dispatch_rc
        self.download_rc = download_rc
        self.title_override = title_override
        self.list_polls = 0
        self.view_polls = 0
        self.last_download_dir = None

    def __call__(self, argv, cwd=None, input_text=None, timeout=None, env=None):
        self.calls.append(list(argv))
        if argv[0] != "gh":
            return real_run(argv, cwd=cwd, input_text=input_text, timeout=timeout, env=env)
        args = argv[1:]
        if args[:2] == ["workflow", "run"]:
            fields = {}
            i = 0
            while i < len(args):
                if args[i] == "-f":
                    k, _, v = args[i + 1].partition("=")
                    fields[k] = v
                    i += 1
                i += 1
            self.dispatched.append(dict(workflow=args[2], fields=fields))
            return ProcResult(self.dispatch_rc, "", "boom" if self.dispatch_rc else "")
        if args[:2] == ["run", "list"]:
            self.list_polls += 1
            if self.list_polls <= self.appear_after or not self.dispatched:
                return ProcResult(0, "[]", "")
            wf = self.dispatched[-1]["workflow"]
            prefix = "factory-worker" if "worker" in wf else "factory-gates"
            title = self.title_override or f"{prefix} {self.dispatched[-1]['fields']['request_id']}"
            other = {"databaseId": 1, "displayTitle": "factory-worker deadbeefdeadbeef",
                     "status": "completed", "conclusion": "success"}
            mine = {"databaseId": 4242, "displayTitle": title, "status": "queued", "conclusion": ""}
            return ProcResult(0, json.dumps([other, mine]), "")
        if args[:2] == ["run", "view"]:
            self.view_polls += 1
            done = self.view_polls > self.complete_after
            return ProcResult(0, json.dumps({"status": "completed" if done else "in_progress",
                                             "conclusion": self.conclusion if done else ""}), "")
        if args[:2] == ["run", "download"]:
            d = Path(args[args.index("-D") + 1])
            self.last_download_dir = d
            if self.download_rc:
                return ProcResult(self.download_rc, "", "no artifact")
            files = self.artifacts(self.dispatched[-1]["fields"]) if self.artifacts else None
            if files is None:
                return ProcResult(1, "", "no valid artifacts found")
            d.mkdir(parents=True, exist_ok=True)
            for name, data in files.items():
                (d / name).write_bytes(data)
            return ProcResult(0, "", "")
        if args[:2] == ["run", "cancel"]:
            return ProcResult(0, "", "")
        return ProcResult(1, "", f"unexpected gh call {args}")

    def gh_calls(self):
        return [c for c in self.calls if c[0] == "gh"]


def client(gh, tmp_path, repo=None, timeout_s=600, clock=None):
    clock = clock or Clock()
    return A.ActionsClient(runner=gh, state_dir=tmp_path / "state", repo=repo, poll_seconds=5,
                           timeout_s=timeout_s, sleep=clock.sleep, clock=clock.now), clock


# --- ActionsClient ---------------------------------------------------------------------------

def test_dispatch_argv_ref_is_main_and_no_force(tmp_path):
    gh = FakeGh()
    c, _ = client(gh, tmp_path)
    c.dispatch("factory-worker.yml", {"branch": "factory/1-x", "request_id": RID})
    argv = gh.gh_calls()[0]
    assert argv[:4] == ["gh", "workflow", "run", "factory-worker.yml"]
    assert argv[argv.index("--ref") + 1] == "main"
    assert "-f" in argv and "branch=factory/1-x" in argv and f"request_id={RID}" in argv
    assert not any("force" in a for a in argv)


def test_repo_flag_passed_only_when_set(tmp_path):
    gh = FakeGh()
    c, _ = client(gh, tmp_path, repo="own/name")
    c.dispatch("w.yml", {"request_id": RID})
    argv = gh.gh_calls()[0]
    assert argv[argv.index("-R") + 1] == "own/name"
    gh2 = FakeGh()
    c2, _ = client(gh2, tmp_path)
    c2.dispatch("w.yml", {"request_id": RID})
    assert "-R" not in gh2.gh_calls()[0]


def test_dispatch_failure_raises(tmp_path):
    c, _ = client(FakeGh(dispatch_rc=1), tmp_path)
    with pytest.raises(A.ActionsError, match="dispatch"):
        c.dispatch("w.yml", {"request_id": RID})


def test_locate_matches_run_name_and_ignores_other_runs(tmp_path):
    gh = FakeGh(appear_after=2)
    c, clk = client(gh, tmp_path)
    c.dispatch("factory-worker.yml", {"request_id": RID})
    deadline = clk.now() + 600
    run_id = c.find_run("factory-worker.yml", f"factory-worker {RID}", deadline)
    assert run_id == 4242 and clk.sleeps == [5, 5]
    lst = [x for x in gh.gh_calls() if x[1:3] == ["run", "list"]][0]
    assert lst[lst.index("--workflow") + 1] == "factory-worker.yml"
    assert lst[lst.index("--json") + 1] == "databaseId,displayTitle,status,conclusion"


def test_run_never_appears_times_out(tmp_path):
    gh = FakeGh(appear_after=10**6)
    c, _ = client(gh, tmp_path, timeout_s=60)
    with pytest.raises(A.ActionsTimeout):
        c.run_workflow("factory-worker.yml", "factory-worker", {"request_id": RID}, f"factory-worker-{RID}")


def test_wrong_title_never_matches(tmp_path):
    gh = FakeGh(title_override="factory-worker 0000000000000000")
    c, _ = client(gh, tmp_path, timeout_s=30)
    with pytest.raises(A.ActionsTimeout):
        c.run_workflow("factory-worker.yml", "factory-worker", {"request_id": RID}, "x")


def test_run_times_out_while_in_progress_and_cancels(tmp_path):
    gh = FakeGh(complete_after=10**6)
    c, _ = client(gh, tmp_path, timeout_s=60)
    with pytest.raises(A.ActionsTimeout):
        c.run_workflow("factory-worker.yml", "factory-worker", {"request_id": RID}, "x")
    assert any(x[1:3] == ["run", "cancel"] for x in gh.gh_calls())


def test_download_goes_under_state_dir_not_repo(tmp_path):
    gh = FakeGh(artifacts=lambda f: {"result.json": b"{}"}, appear_after=0)
    c, _ = client(gh, tmp_path)
    conclusion, d = c.run_workflow("factory-worker.yml", "factory-worker", {"request_id": RID}, f"factory-result-{RID}")
    assert conclusion == "success"
    assert (tmp_path / "state") in d.parents and (d / "result.json").exists()
    dl = [x for x in gh.gh_calls() if x[1:3] == ["run", "download"]][0]
    assert dl[dl.index("-n") + 1] == f"factory-result-{RID}"
    d2 = c.new_download_dir()
    assert d2 != d


def test_missing_artifact_returns_none_dir(tmp_path):
    gh = FakeGh(artifacts=None)
    c, _ = client(gh, tmp_path)
    conclusion, d = c.run_workflow("factory-worker.yml", "factory-worker", {"request_id": RID}, "x")
    assert d is None


# --- ActionsLauncher with real git -------------------------------------------------------------

BRANCH = "factory/7-add-thing"


@pytest.fixture
def world(tmp_path):
    origin = tmp_path / "origin.git"
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(origin))
    seed = tmp_path / "seed"
    git(tmp_path, "clone", "-q", str(origin), str(seed))
    git(seed, "checkout", "-q", "-b", "main")
    (seed / "a.txt").write_text("a\n")
    (seed / "docs").mkdir()
    (seed / "docs" / "x.md").write_text("x\n")
    git(seed, "add", "-A")
    git(seed, "commit", "-qm", "init")
    git(seed, "push", "-q", "origin", "main")
    wt = tmp_path / "wt"
    git(tmp_path, "clone", "-q", str(origin), str(wt))
    git(wt, "checkout", "-q", "-b", BRANCH)
    return wt


def make_patch(wt, tmp_path, mutate):
    scratch = tmp_path / "scratch"
    if scratch.exists():
        subprocess.run(["rm", "-rf", str(scratch)], check=True)
    git(tmp_path, "clone", "-q", str(wt), str(scratch))
    mutate(scratch)
    git(scratch, "add", "-A")
    return git(scratch, "diff", "--cached", "--binary", "HEAD").encode()


def good_result(fields, start_sha, **over):
    d = {"returncode": 0, "result": "did it", "input_tokens": 11, "output_tokens": 7,
         "total_cost_usd": 0.25, "model": "sonnet", "start_sha": start_sha, "request_id": fields["request_id"]}
    d.update(over)
    return d


def artifacts_for(wt, patch=b"", **over):
    start = git(wt, "rev-parse", "HEAD").strip()

    def make(fields):
        res = good_result(fields, start, **over)
        files = {"changes.patch": patch}
        if res is not None:
            files["result.json"] = json.dumps(res).encode()
        return files
    return make


def launcher(gh, tmp_path, rid=RID, timeout_s=600):
    c, clk = client(gh, tmp_path, timeout_s=timeout_s)
    return A.ActionsLauncher(POLICY, c, runner=gh, new_request_id=lambda: rid), gh


def test_happy_path_applies_patch_commits_and_pushes(world, tmp_path):
    patch = make_patch(world, tmp_path, lambda s: (s / "new.py").write_text("print(1)\n"))
    gh = FakeGh(artifacts=artifacts_for(world, patch))
    l, _ = launcher(gh, tmp_path)
    r = l.run("build", "SECRET PROMPT TEXT", world, max_budget_usd=1.5)
    assert r.ok and r.cost_known and r.cost_usd == 0.25 and r.input_tokens == 11 and r.text == "did it"
    assert r.model == "sonnet"
    assert (world / "new.py").read_text() == "print(1)\n"
    assert git(world, "log", "-1", "--format=%s").strip() == "factory: worker output (build)"
    assert git(world, "status", "--porcelain").strip() == ""
    remote_sha = git(world, "ls-remote", "origin", f"refs/heads/{BRANCH}").split()[0]
    assert remote_sha == git(world, "rev-parse", "HEAD").strip()


def test_argv_hygiene_ref_main_no_force_prompt_encoded(world, tmp_path):
    patch = make_patch(world, tmp_path, lambda s: (s / "new.py").write_text("1\n"))
    gh = FakeGh(artifacts=artifacts_for(world, patch))
    l, _ = launcher(gh, tmp_path)
    prompt = "SECRET PROMPT TEXT " * 5
    l.run("build", prompt, world, max_budget_usd=1.5)
    for argv in gh.calls:
        assert not any(a in ("--force", "-f=force", "--force-with-lease", "+") or a.startswith("--force")
                       for a in argv)
        assert not any(prompt in a or "SECRET PROMPT" in a for a in argv)
    disp = gh.dispatched[0]
    assert disp["workflow"] == "factory-worker.yml"
    f = disp["fields"]
    assert f["branch"] == BRANCH and f["role"] == "build" and f["model"] == "sonnet"
    assert f["max_budget_usd"] == "1.50" and f["request_id"] == RID
    assert gzip.decompress(base64.b64decode(f["prompt_b64"])).decode() == prompt
    run_argv = [c for c in gh.gh_calls() if c[1:3] == ["workflow", "run"]][0]
    assert run_argv[run_argv.index("--ref") + 1] == "main"
    pushes = [c for c in gh.calls if c[:2] == ["git", "push"]]
    assert len(pushes) == 2 and all(c[2] == "origin" for c in pushes)


def test_branch_is_pushed_before_dispatch_and_start_sha_matches(world, tmp_path):
    seen = {}

    class Spy(FakeGh):
        def __call__(self, argv, **kw):
            if argv[1:3] == ["workflow", "run"]:
                seen["remote"] = git(world, "ls-remote", "origin", f"refs/heads/{BRANCH}").split()
            return super().__call__(argv, **kw)
    gh = Spy(artifacts=artifacts_for(world))
    l, _ = launcher(gh, tmp_path)
    l.run("build", "p", world)
    assert seen["remote"][0] == git(world, "rev-parse", "HEAD").strip()


def test_empty_patch_makes_no_commit(world, tmp_path):
    before = git(world, "rev-parse", "HEAD").strip()
    gh = FakeGh(artifacts=artifacts_for(world, b""))
    l, _ = launcher(gh, tmp_path)
    r = l.run("spec", "p", world)
    assert r.ok and git(world, "rev-parse", "HEAD").strip() == before


def test_rejected_push_is_error_not_force_retry(world, tmp_path):
    # make the remote branch diverge so a plain push is rejected
    other = tmp_path / "other"
    git(tmp_path, "clone", "-q", str(tmp_path / "origin.git"), str(other))
    git(other, "checkout", "-q", "-b", BRANCH)
    (other / "z").write_text("z\n")
    git(other, "add", "-A")
    git(other, "commit", "-qm", "z")
    git(other, "push", "-q", "origin", BRANCH)
    gh = FakeGh(artifacts=artifacts_for(world))
    l, _ = launcher(gh, tmp_path)
    r = l.run("build", "p", world)
    assert not r.ok and not r.cost_known and "push" in r.text.lower()
    assert gh.dispatched == []
    assert not any("force" in " ".join(c) for c in gh.calls)
    assert len([c for c in gh.calls if c[:2] == ["git", "push"]]) == 1


def test_oversize_prompt_fails_without_dispatch_or_push(world, tmp_path):
    import random
    rnd = random.Random(1)
    prompt = "".join(chr(rnd.randrange(33, 126)) for _ in range(80000))   # incompressible
    gh = FakeGh(artifacts=artifacts_for(world))
    l, _ = launcher(gh, tmp_path)
    r = l.run("build", prompt, world)
    assert not r.ok and "too large" in r.text and gh.dispatched == []
    assert not any(c[:2] == ["git", "push"] for c in gh.calls)


def test_dirty_worktree_refused(world, tmp_path):
    (world / "dirty.txt").write_text("x")
    gh = FakeGh(artifacts=artifacts_for(world))
    r = launcher(gh, tmp_path)[0].run("build", "p", world)
    assert not r.ok and "clean" in r.text and gh.dispatched == []


@pytest.mark.parametrize("name", ["main", "feature/x", "factory/x-y", "factory/1-Bad", "factory/1-a;rm",
                                  "factory/1-"])
def test_non_factory_branch_refused(world, tmp_path, name):
    git(world, "checkout", "-q", "-b", name.replace(";", "_"))
    gh = FakeGh(artifacts=artifacts_for(world))
    r = launcher(gh, tmp_path)[0].run("build", "p", world)
    assert not r.ok and "branch" in r.text and gh.dispatched == []
    assert not any(c[:2] == ["git", "push"] for c in gh.calls)


def test_unknown_role_raises(world, tmp_path):
    gh = FakeGh()
    with pytest.raises(Lc.LauncherError):
        launcher(gh, tmp_path)[0].run("nope", "p", world)


# --- hostile patches ---------------------------------------------------------------------------

def run_with_patch(world, tmp_path, patch):
    gh = FakeGh(artifacts=artifacts_for(world, patch))
    l, _ = launcher(gh, tmp_path)
    before = git(world, "rev-parse", "HEAD").strip()
    r = l.run("build", "p", world)
    return r, gh, before


def assert_rejected(world, r, before, gh):
    assert not r.ok and r.returncode != 0
    assert git(world, "rev-parse", "HEAD").strip() == before
    assert git(world, "status", "--porcelain").strip() == ""
    assert len([c for c in gh.calls if c[:2] == ["git", "push"]]) == 1     # only the pre-dispatch push


HDR = ("diff --git a/{p} b/{p}\nnew file mode 100644\nindex 0000000..e69de29\n"
       "--- /dev/null\n+++ b/{p}\n@@ -0,0 +1 @@\n+owned\n")


@pytest.mark.parametrize("path", ["../escape.txt", "sub/../../escape.txt", ".git/hooks/pre-commit",
                                  "x/.git/config", ".GIT/hooks/post-commit", "/etc/passwd"])
def test_hostile_paths_rejected(world, tmp_path, path):
    r, gh, before = run_with_patch(world, tmp_path, HDR.format(p=path).encode())
    assert_rejected(world, r, before, gh)
    assert not (tmp_path / "escape.txt").exists()


def test_new_symlink_rejected(world, tmp_path):
    def mutate(s):
        os.symlink("/etc/passwd", s / "link")
    patch = make_patch(world, tmp_path, mutate)
    assert b"120000" in patch
    r, gh, before = run_with_patch(world, tmp_path, patch)
    assert_rejected(world, r, before, gh)
    assert "symlink" in r.text


def test_gitlink_rejected(world, tmp_path):
    patch = (b"diff --git a/sub b/sub\nnew file mode 160000\nindex 0000000..1111111\n"
             b"--- /dev/null\n+++ b/sub\n@@ -0,0 +1 @@\n+Subproject commit 1111111111111111111111111111111111111111\n")
    r, gh, before = run_with_patch(world, tmp_path, patch)
    assert_rejected(world, r, before, gh)


def test_mode_change_to_symlink_rejected(world, tmp_path):
    patch = (b"diff --git a/a.txt b/a.txt\nold mode 100644\nnew mode 120000\n")
    r, gh, before = run_with_patch(world, tmp_path, patch)
    assert_rejected(world, r, before, gh)


def test_garbage_patch_rejected(world, tmp_path):
    r, gh, before = run_with_patch(world, tmp_path, b"this is not a patch\n+++ b/../x\n")
    assert_rejected(world, r, before, gh)


def test_oversize_patch_rejected(world, tmp_path):
    r, gh, before = run_with_patch(world, tmp_path, b"x" * (A.MAX_PATCH_BYTES + 1))
    assert_rejected(world, r, before, gh)


def test_binary_patch_applies(world, tmp_path):
    patch = make_patch(world, tmp_path, lambda s: (s / "b.bin").write_bytes(bytes(range(256)) * 8))
    r, gh, before = run_with_patch(world, tmp_path, patch)
    assert r.ok and (world / "b.bin").read_bytes() == bytes(range(256)) * 8


def test_rename_and_delete_apply(world, tmp_path):
    def mutate(s):
        git(s, "mv", "a.txt", "docs/renamed.txt")
        (s / "docs" / "x.md").unlink()
    patch = make_patch(world, tmp_path, mutate)
    r, gh, before = run_with_patch(world, tmp_path, patch)
    assert r.ok and (world / "docs" / "renamed.txt").exists() and not (world / "a.txt").exists()


# --- hostile result.json -------------------------------------------------------------------------

def run_with_result(world, tmp_path, mutate_result=None, raw=None, drop=None, conclusion="success"):
    start = git(world, "rev-parse", "HEAD").strip()

    def make(fields):
        res = good_result(fields, start)
        if mutate_result:
            mutate_result(res)
        if drop:
            res.pop(drop)
        text = raw if raw is not None else json.dumps(res)
        return {"changes.patch": b"", "result.json": text.encode()}
    gh = FakeGh(artifacts=make, conclusion=conclusion)
    return launcher(gh, tmp_path)[0].run("build", "p", world), gh


@pytest.mark.parametrize("mutate", [
    lambda r: r.update(request_id="ffffffffffffffff"),
    lambda r: r.update(start_sha="0" * 40),
    lambda r: r.update(total_cost_usd="free"),
    lambda r: r.update(total_cost_usd=-1),
    lambda r: r.update(total_cost_usd=float("nan")),
    lambda r: r.update(total_cost_usd=True),
    lambda r: r.update(returncode="0"),
    lambda r: r.update(returncode=True),
    lambda r: r.update(input_tokens=-5),
    lambda r: r.update(output_tokens="7"),
    lambda r: r.update(result=None),
    lambda r: r.update(model=3),
])
def test_malformed_result_fields_fail_unknown_cost(world, tmp_path, mutate):
    r, gh = run_with_result(world, tmp_path, mutate)
    assert not r.ok and not r.cost_known


@pytest.mark.parametrize("key", ["returncode", "result", "input_tokens", "output_tokens", "total_cost_usd",
                                 "model", "start_sha", "request_id"])
def test_missing_result_field_fails(world, tmp_path, key):
    r, gh = run_with_result(world, tmp_path, drop=key)
    assert not r.ok and not r.cost_known


@pytest.mark.parametrize("raw", ["", "not json", "[]", "null", '{"returncode": 0}'])
def test_unparseable_result_fails(world, tmp_path, raw):
    r, gh = run_with_result(world, tmp_path, raw=raw)
    assert not r.ok and not r.cost_known


def test_null_cost_means_unknown_not_failure_of_validation(world, tmp_path):
    r, gh = run_with_result(world, tmp_path, lambda r: r.update(total_cost_usd=None))
    assert r.ok and not r.cost_known


def test_failed_run_conclusion_is_nonzero_even_if_result_says_zero(world, tmp_path):
    r, gh = run_with_result(world, tmp_path, conclusion="failure")
    assert not r.ok


def test_worker_nonzero_returncode_is_passed_through(world, tmp_path):
    r, gh = run_with_result(world, tmp_path, lambda r: r.update(returncode=3))
    assert r.returncode == 3 and r.cost_known


def test_missing_artifact_is_failed_result(world, tmp_path):
    gh = FakeGh(artifacts=None)
    r = launcher(gh, tmp_path)[0].run("build", "p", world)
    assert not r.ok and not r.cost_known


def test_timeout_maps_to_124_unknown_cost(world, tmp_path):
    gh = FakeGh(complete_after=10**6)
    l, _ = launcher(gh, tmp_path, timeout_s=60)
    r = l.run("build", "p", world)
    assert r.returncode == 124 and not r.cost_known


def test_run_never_appears_maps_to_124(world, tmp_path):
    gh = FakeGh(appear_after=10**6)
    l, _ = launcher(gh, tmp_path, timeout_s=60)
    assert l.run("build", "p", world).returncode == 124


def test_dispatch_error_is_failed_unknown_cost(world, tmp_path):
    gh = FakeGh(dispatch_rc=1)
    r = launcher(gh, tmp_path)[0].run("build", "p", world)
    assert not r.ok and not r.cost_known


def test_result_text_is_truncated(world, tmp_path):
    r, gh = run_with_result(world, tmp_path, lambda r: r.update(result="x" * 500000))
    assert r.ok and len(r.text) <= A.MAX_TEXT_CHARS


# --- ActionsGateRunner ---------------------------------------------------------------------------

def gate_runner(gh, tmp_path, timeout_s=600):
    c, _ = client(gh, tmp_path, timeout_s=timeout_s)
    return A.ActionsGateRunner(c, runner=gh, new_request_id=lambda: RID)


def gates_artifacts(world, text, sha=None):
    def make(fields):
        return {"gates-output.txt": text.encode(),
                "gates-sha.txt": (sha or git(world, "rev-parse", "HEAD").strip()).encode()}
    return make


def test_gates_pass_roundtrip(world, tmp_path):
    gh = FakeGh(artifacts=gates_artifacts(world, "ok\nFACTORY-GATES: PASS\n"))
    res = gate_runner(gh, tmp_path).run(world)
    assert res.verdict == "PASS" and "ok" in res.output
    d = gh.dispatched[0]
    assert d["workflow"] == "factory-gates.yml" and d["fields"] == {"branch": BRANCH, "request_id": RID}
    assert git(world, "ls-remote", "origin", f"refs/heads/{BRANCH}").split()[0] == git(world, "rev-parse", "HEAD").strip()
    assert not any("--force" in " ".join(c) for c in gh.calls)


def test_gates_fail_verdict_passes_through(world, tmp_path):
    gh = FakeGh(artifacts=gates_artifacts(world, "boom\nFACTORY-GATES: FAIL\n"))
    assert gate_runner(gh, tmp_path).run(world).verdict == "FAIL"


def test_forged_extra_pass_line_is_misconfigured(world, tmp_path):
    text = "FACTORY-GATES: PASS\nsome output\nFACTORY-GATES: FAIL\n"
    gh = FakeGh(artifacts=gates_artifacts(world, text))
    assert gate_runner(gh, tmp_path).run(world).verdict == "MISCONFIGURED"
    text = "FACTORY-GATES: PASS\nFACTORY-GATES: PASS\n"
    gh = FakeGh(artifacts=gates_artifacts(world, text))
    assert gate_runner(gh, tmp_path).run(world).verdict == "MISCONFIGURED"


def test_gates_pushes_when_behind_and_never_forces(world, tmp_path):
    (world / "n.txt").write_text("n\n")
    git(world, "add", "-A")
    git(world, "commit", "-qm", "local only")
    gh = FakeGh(artifacts=gates_artifacts(world, "FACTORY-GATES: PASS\n"))
    assert gate_runner(gh, tmp_path).run(world).verdict == "PASS"
    assert any(c[:2] == ["git", "push"] for c in gh.calls)


def test_gates_diverged_remote_is_misconfigured(world, tmp_path):
    git(world, "push", "-q", "origin", BRANCH)
    other = tmp_path / "other"
    git(tmp_path, "clone", "-q", str(tmp_path / "origin.git"), str(other))
    git(other, "checkout", "-q", BRANCH)
    (other / "z").write_text("z\n")
    git(other, "add", "-A")
    git(other, "commit", "-qm", "z")
    git(other, "push", "-q", "origin", BRANCH)
    (world / "n.txt").write_text("n\n")
    git(world, "add", "-A")
    git(world, "commit", "-qm", "diverge")
    gh = FakeGh(artifacts=gates_artifacts(world, "FACTORY-GATES: PASS\n"))
    assert gate_runner(gh, tmp_path).run(world).verdict == "MISCONFIGURED"
    assert gh.dispatched == [] and not any("force" in " ".join(c) for c in gh.calls)


def test_gates_timeout_error_missing_artifact_are_misconfigured(world, tmp_path):
    for gh in (FakeGh(complete_after=10**6), FakeGh(appear_after=10**6), FakeGh(artifacts=None),
               FakeGh(dispatch_rc=1), FakeGh(conclusion="failure",
                                             artifacts=gates_artifacts(world, "FACTORY-GATES: PASS\n"))):
        assert gate_runner(gh, tmp_path, timeout_s=60).run(world).verdict == "MISCONFIGURED"


def test_gates_sha_mismatch_is_misconfigured(world, tmp_path):
    gh = FakeGh(artifacts=gates_artifacts(world, "FACTORY-GATES: PASS\n", sha="0" * 40))
    assert gate_runner(gh, tmp_path).run(world).verdict == "MISCONFIGURED"


def test_gates_missing_sha_file_is_misconfigured(world, tmp_path):
    gh = FakeGh(artifacts=lambda f: {"gates-output.txt": b"FACTORY-GATES: PASS\n"})
    assert gate_runner(gh, tmp_path).run(world).verdict == "MISCONFIGURED"


def test_gates_oversize_output_is_misconfigured(world, tmp_path):
    gh = FakeGh(artifacts=gates_artifacts(world, "x" * (A.MAX_GATES_BYTES + 1) + "\nFACTORY-GATES: PASS\n"))
    assert gate_runner(gh, tmp_path).run(world).verdict == "MISCONFIGURED"


def test_gates_dirty_or_bad_branch_is_misconfigured(world, tmp_path):
    (world / "dirty").write_text("x")
    gh = FakeGh(artifacts=gates_artifacts(world, "FACTORY-GATES: PASS\n"))
    assert gate_runner(gh, tmp_path).run(world).verdict == "MISCONFIGURED"
    (world / "dirty").unlink()
    git(world, "checkout", "-q", "-b", "wip")
    assert gate_runner(gh, tmp_path).run(world).verdict == "MISCONFIGURED"


def test_gate_runner_is_a_gaterunner_and_launcher_is_a_launcher():
    assert issubclass(A.ActionsGateRunner, G.GateRunner) and issubclass(A.ActionsLauncher, Lc.Launcher)
