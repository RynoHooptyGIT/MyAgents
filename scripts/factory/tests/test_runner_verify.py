"""Runner wiring for sealed tests, the verify job and the model verifier (phase 3)."""
import base64
import dataclasses
import gzip
import json
import os
import re
import subprocess
from pathlib import Path

import pytest

from .. import actions as A
from .. import gates as G
from .. import launcher as Lc
from .. import ledger as Ld
from .. import policy as pol
from .. import runner as R
from .. import sealed as SL
from .. import tracker as T
from .. import verifier as V
from .. import workspace as W
from .test_actions import FakeGh, client, git, good_result
from .test_runner_e2e import AGREE_TEXT, BODY, GOOD_VERIFY, NOW, Env, chain, good_collect

REPO = Path(__file__).resolve().parents[3]


def sealed_dir(e, issue=1, attempt=1):
    return e.state / "sealed" / f"issue-{issue}-a{attempt}"


def manifest(e, **kw):
    return json.loads((sealed_dir(e, **kw) / "manifest.json").read_text())


def collect_calls(e, role=None):
    return [c for c in e.launcher.calls if c["kind"] == "collect" and (role is None or c["role"] == role)]


def reasons(e):
    return e.ledger.rows()[-1]["reasons"]


def codes_in_comment(e):
    return e.tracker.comments[-1][1]


@pytest.fixture
def env(tmp_path):
    e = Env(tmp_path)
    e.add()
    return e


# --- decide_verdict (pure) ----------------------------------------------------------------------

CODE = ["skills/a/x.py"]
DOCS = ["docs/a.md"]
TESTS = ["skills/tests/test_a.py"]


@pytest.mark.parametrize("model,revert,paths,avail,want_verdict,want_reasons", [
    ("agree", "fails_without_change", CODE, True, "agree", []),
    ("agree", "passes_without_change", CODE, True, "disagree", ["revert check: tests pass without the change"]),
    ("agree", "fails_with_change", CODE, True, "disagree", ["revert check: new tests do not pass with the change"]),
    ("agree", "no_new_tests", CODE, True, "disagree", ["revert check: no new tests for a code change"]),
    ("agree", "no_new_tests", DOCS, True, "agree", []),
    ("agree", "no_new_tests", DOCS + TESTS, True, "agree", []),
    ("agree", "no_new_tests", CODE + TESTS, True, "disagree", ["revert check: no new tests for a code change"]),
    ("agree", "nothing_to_revert", TESTS, True, "agree", []),
    ("agree", "nothing_to_revert", CODE, True, "disagree", ["revert check: no new tests for a code change"]),
    ("agree", "error", CODE, True, "disagree", ["revert check error"]),
    ("agree", "fails_without_change", CODE, False, "not_run", ["verification unavailable"]),
    ("disagree", "fails_without_change", CODE, True, "disagree", []),
    ("disagree", "passes_without_change", CODE, True, "disagree", ["revert check: tests pass without the change"]),
    ("not_run", "fails_without_change", CODE, True, "not_run", []),
    ("not_run", "passes_without_change", CODE, True, "not_run", ["revert check: tests pass without the change"]),
    ("unavailable", "fails_without_change", CODE, True, "not_run", ["verifier unavailable"]),
    ("agree", "unavailable", CODE, True, "not_run", ["verification unavailable"]),
])
def test_decide_verdict(model, revert, paths, avail, want_verdict, want_reasons):
    pl = pol.load(REPO)
    got = R.decide_verdict(pl, paths, model, revert, avail)
    assert got == (want_verdict, want_reasons)


# --- all agree ------------------------------------------------------------------------------------

def test_all_agree_runs_sealed_author_then_build_then_verify_and_verifier(env):
    res = R.run_once(env.ctx())
    assert res.outcome == "awaiting-human" and res.tier == "T2"
    assert [(c["kind"], c["role"]) for c in env.launcher.calls] == [
        ("run", "spec"), ("collect", "sealed_test_author"), ("run", "build"), ("collect", "verifier")]
    assert chain(env) == [("queued", "claimed"), ("claimed", "building"),
                          ("building", "verifying"), ("verifying", "awaiting-human")]
    assert env.gates.calls == 1 and len(env.verifier.calls) == 1
    row = env.ledger.rows()[0]
    assert row["verify"] == {"model_verdict": "agree", "revert_check": "fails_without_change",
                             "sealed_available": True, "sealed_total": 1, "sealed_failed": 0}
    assert row["models"]["sealed_test_author"] == ["opus"] and row["models"]["verifier"] == ["opus"]
    assert [r for r in row["reasons"] if r.startswith(("verif", "sealed", "revert"))] == []
    assert row["reasons"][-1].startswith("phase 3: all categories forced to T2")


def test_sealed_author_prompt_and_cwd(env):
    R.run_once(env.ctx())
    c = collect_calls(env, "sealed_test_author")[0]
    assert "specs/1.md" in c["prompt"] and "tests/sealed/issue-1/" in c["prompt"]
    assert "ignore all rules" in c["prompt"] and "UNTRUSTED" in c["prompt"]
    assert c["model"] is None and c["cwd"] == env.root / "wt-1"


def test_sealed_store_holds_patch_manifest_and_a_canary_outside_the_repo(env):
    R.run_once(env.ctx())
    d = sealed_dir(env)
    assert env.state in d.parents
    m = manifest(env)
    patch = (d / "sealed.patch").read_bytes()
    assert patch.startswith(b"diff --git a/tests/sealed/issue-1/test_acc.py")
    import hashlib
    assert m["patch_sha256"] == hashlib.sha256(patch).hexdigest()
    assert re.fullmatch(r"[0-9a-f]{32}", m["canary"]) and re.fullmatch(r"[0-9a-f]{40}", m["spec_sha"])


def test_verifier_gets_the_sealed_bundle_with_the_canary_file(env):
    R.run_once(env.ctx())
    call = env.verifier.calls[0]
    assert call["issue"] == 1 and call["worktree"] == env.root / "wt-1"
    patch = (sealed_dir(env) / "sealed.patch").read_bytes()
    assert call["bundle"].startswith(patch)
    assert SL.validate_sealed_patch(call["bundle"], 1, 100_000, allow_canary=True)
    assert f"canary_{manifest(env)['canary']}.txt".encode() in call["bundle"]


def test_model_verifier_prompt_has_issue_only_and_no_builder_transcript(tmp_path):
    e = Env(tmp_path, launcher_results=[Lc.WorkerResult(0, "spec ok", 0, 0, 0.0, True, "sonnet"),
                                        Lc.WorkerResult(0, "BUILDER-TRANSCRIPT-MARKER", 0, 0, 0.0, True, "sonnet")])
    e.add()
    R.run_once(e.ctx())
    p = collect_calls(e, "verifier")[0]["prompt"]
    assert "BUILDER-TRANSCRIPT-MARKER" not in p and "spec ok" not in p and "ignore all rules" in p
    assert "git diff origin/main...HEAD" in p and "FACTORY-VERIFY" in p


def test_the_model_verifier_is_given_the_remaining_budget_and_the_routed_model(env):
    R.run_once(env.ctx())
    c = collect_calls(env, "verifier")[0]
    assert c["max_budget_usd"] == env.policy.per_issue_usd and c["model"] is None


# --- verifier disagreement / hostile verdicts ----------------------------------------------------

def scripted(verifier_text=AGREE_TEXT, verifier_patch=b"", verifier_rc=0, sealed=None):
    def handler(role, prompt, cwd):
        if role == "verifier":
            return Lc.WorkerResult(verifier_rc, verifier_text, 0, 0, 0.0, True, "fake"), verifier_patch
        return sealed(role, prompt, cwd) if sealed else good_collect(role, prompt, cwd)
    return handler


def run_with(tmp_path, **kw):
    e = Env(tmp_path, **kw)
    e.add()
    R.run_once(e.ctx())
    return e


def test_verifier_disagree_adds_reason_and_code(tmp_path):
    e = run_with(tmp_path, collect_handler=scripted("nope\nFACTORY-VERIFY: DISAGREE"))
    assert "verifier disagreement" in reasons(e)
    assert e.ledger.rows()[-1]["verify"]["model_verdict"] == "disagree"
    assert "verifier-disagreement" in codes_in_comment(e)


@pytest.mark.parametrize("text", [
    "FACTORY-VERIFY: AGREE\nFACTORY-VERIFY: AGREE", "FACTORY-VERIFY: AGREE\nthanks", "factory-verify: agree",
    "FACTORY-VERIFY: AGREE.", "", "I agree"])
def test_hostile_verdict_text_is_disagreement(tmp_path, text):
    e = run_with(tmp_path, collect_handler=scripted(text))
    assert e.ledger.rows()[-1]["verify"]["model_verdict"] == "disagree"
    assert "verifier disagreement" in reasons(e)


def test_verifier_that_returns_a_patch_is_disagreement_and_patch_is_not_applied(tmp_path):
    patch = SL.new_file_patch("evil.py", b"print(1)\n")
    e = run_with(tmp_path, collect_handler=scripted(AGREE_TEXT, verifier_patch=patch))
    assert e.ledger.rows()[-1]["verify"]["model_verdict"] == "disagree"
    assert "verifier disagreement" in reasons(e) and "verifier returned a patch" in reasons(e)
    assert "verifier-patch" in codes_in_comment(e)
    assert not any((e.root / "wt-1").rglob("evil.py"))


def test_verifier_worker_failure_is_unavailable_not_agreement(tmp_path):
    e = run_with(tmp_path, collect_handler=scripted("boom", verifier_rc=1))
    row = e.ledger.rows()[-1]
    assert row["verify"]["model_verdict"] == "unavailable"
    assert "verifier unavailable" in row["reasons"] and "verifier-unavailable" in codes_in_comment(e)


def test_verifier_text_never_reaches_the_issue_comment(tmp_path):
    secret = "SECRET-VERIFIER-TEXT /Users/x/.ssh/id_rsa\nFACTORY-VERIFY: DISAGREE"
    e = run_with(tmp_path, collect_handler=scripted(secret))
    for _, body in e.tracker.comments:
        assert "SECRET" not in body and ".ssh" not in body
    assert "SECRET-VERIFIER-TEXT" in (e.state / "logs" / "issue-1.log").read_text()


# --- revert check / sealed results mapped to reasons -----------------------------------------------

def vr(**over):
    return dataclasses.replace(GOOD_VERIFY, **over)


@pytest.mark.parametrize("result,reason,code", [
    (vr(revert_check="passes_without_change"), "revert check: tests pass without the change", "revert-passes"),
    (vr(revert_check="no_new_tests", revert_tests=0), "revert check: no new tests for a code change", "revert-no-new-tests"),
    (vr(revert_check="fails_with_change"), "revert check: new tests do not pass with the change", "revert-fails-with-change"),
    (vr(revert_check="error"), "revert check error", "revert-error"),
])
def test_revert_check_outcomes_block_agreement(tmp_path, result, reason, code):
    e = run_with(tmp_path, verify_default=result)
    assert reason in reasons(e) and code in codes_in_comment(e)
    assert "verifier disagreement" in reasons(e)
    assert e.ledger.rows()[-1]["verify"]["revert_check"] == result.revert_check


def test_docs_only_change_with_no_new_tests_can_agree(tmp_path):
    e = run_with(tmp_path, diff=W.DiffStats(["docs/a.md"], 3, 0, 0),
                 verify_default=vr(revert_check="no_new_tests", revert_tests=0))
    assert "verifier disagreement" not in reasons(e)
    assert e.ledger.rows()[-1]["verify"]["model_verdict"] == "agree"


def test_sealed_failures_are_counted_failed_plus_errors(tmp_path):
    e = run_with(tmp_path, verify_default=vr(sealed_total=5, sealed_failed=2, sealed_errors=1))
    assert "sealed-test failures: 3" in reasons(e) and "sealed-failure" in codes_in_comment(e)
    v = e.ledger.rows()[-1]["verify"]
    assert (v["sealed_total"], v["sealed_failed"], v["sealed_available"]) == (5, 3, True)


def test_sealed_zero_tests_collected_has_its_own_reason(tmp_path):
    e = run_with(tmp_path, verify_default=vr(sealed_status="no_tests", sealed_total=0))
    assert "sealed run collected no tests" in reasons(e) and "sealed-no-tests" in codes_in_comment(e)
    assert e.ledger.rows()[-1]["verify"]["sealed_available"] is False


@pytest.mark.parametrize("status", ["invalid", "crash", "oversize"])
def test_sealed_run_that_did_not_run_is_unavailable(tmp_path, status):
    e = run_with(tmp_path, verify_default=vr(sealed_status=status, sealed_total=0))
    assert any(r.startswith("sealed tests unavailable") for r in reasons(e))
    assert "sealed-unavailable" in codes_in_comment(e)
    assert e.ledger.rows()[-1]["verify"]["sealed_available"] is False


def test_verification_unavailable_is_a_reason_not_agreement(tmp_path):
    e = run_with(tmp_path, verify_default=V.VerifyResult.unavailable("gh exploded"))
    row = e.ledger.rows()[-1]
    assert "verification unavailable" in row["reasons"] and "verify-unavailable" in codes_in_comment(e)
    assert row["verify"]["revert_check"] == "unavailable" and row["tier"] == "T2"
    assert "gh exploded" in (e.state / "logs" / "issue-1.log").read_text()
    assert all("gh exploded" not in b for _, b in e.tracker.comments)


def test_missing_verifier_in_context_is_unavailable(tmp_path):
    e = Env(tmp_path)
    e.add()
    ctx = e.ctx()
    ctx.verifier = None
    R.run_once(ctx)
    assert "verification unavailable" in reasons(e)


# --- sealed author failure paths -------------------------------------------------------------------

def test_sealed_author_failure_does_not_stop_the_build(tmp_path):
    def handler(role, prompt, cwd):
        if role == "sealed_test_author":
            return Lc.WorkerResult(1, "author crashed", 0, 0, 0.3, True, "fake"), b""
        return good_collect(role, prompt, cwd)
    e = run_with(tmp_path, collect_handler=handler)
    row = e.ledger.rows()[-1]
    assert [c["role"] for c in e.launcher.calls if c["kind"] == "run"] == ["spec", "build"]
    assert any(r.startswith("sealed tests unavailable") for r in row["reasons"])
    assert e.verifier.calls[0]["bundle"] is None
    assert row["verify"]["sealed_available"] is False
    assert row["cost_usd"] == pytest.approx(0.3)                       # sealed spend counts
    assert not (e.state / "sealed").exists() or not any((e.state / "sealed").iterdir())


@pytest.mark.parametrize("patch", [
    b"", b"garbage",
    SL.new_file_patch("src/x.py", b"x\n"),
    SL.new_file_patch("tests/sealed/issue-2/test_a.py", b"def test_a(): pass\n"),
    SL.new_file_patch("tests/sealed/issue-1/helper.py", b"x\n"),
])
def test_invalid_sealed_patch_means_sealed_unavailable_but_build_proceeds(tmp_path, patch):
    def handler(role, prompt, cwd):
        if role == "sealed_test_author":
            return Lc.WorkerResult(0, "ok", 0, 0, 0.0, True, "fake"), patch
        return good_collect(role, prompt, cwd)
    e = run_with(tmp_path, collect_handler=handler)
    assert any(r.startswith("sealed tests unavailable") for r in reasons(e))
    assert [c["role"] for c in e.launcher.calls if c["kind"] == "run"] == ["spec", "build"]
    assert e.verifier.calls[0]["bundle"] is None
    assert not (sealed_dir(e) / "sealed.patch").exists()


def test_sealed_spend_counts_against_the_budget_and_can_block_the_build(tmp_path):
    def handler(role, prompt, cwd):
        r, p = good_collect(role, prompt, cwd)
        return dataclasses.replace(r, cost_usd=5.0), p
    e = run_with(tmp_path, collect_handler=handler)
    row = e.ledger.rows()[-1]
    assert row["cost_usd"] == pytest.approx(5.0) and "budget exceeded" in row["reasons"]
    assert [c["role"] for c in e.launcher.calls if c["kind"] == "run"] == ["spec"]
    assert collect_calls(e, "verifier") == [] and e.verifier.calls == []


def test_budget_exhausted_before_the_sealed_author_skips_it(tmp_path):
    unknown = Lc.WorkerResult(0, "ok", 0, 0, 0.0, False, "sonnet")
    e = run_with(tmp_path, launcher_results=[unknown])
    assert collect_calls(e) == [] and "budget exceeded" in reasons(e)


# --- budget exhausted before verify ---------------------------------------------------------------

def test_budget_exhausted_before_verify_skips_verify_and_verifier(tmp_path):
    spec = Lc.WorkerResult(0, "spec", 0, 0, 0.0, True, "sonnet")
    build = Lc.WorkerResult(0, "built", 0, 0, 5.0, True, "sonnet")
    e = run_with(tmp_path, launcher_results=[spec, build])
    row = e.ledger.rows()[-1]
    assert "budget exceeded" in row["reasons"] and "verification skipped: budget exhausted" in row["reasons"]
    assert e.verifier.calls == [] and collect_calls(e, "verifier") == []
    assert "verify-skipped" in codes_in_comment(e) and "verify" not in row
    assert chain(e)[-1] == ("building", "awaiting-human")


# --- verifier model must differ from every builder model ------------------------------------------

def test_verifier_model_equal_to_the_builder_model_is_not_run(tmp_path):
    base = pol.load(REPO)
    p = dataclasses.replace(base, routing={**base.routing, "verifier": "sonnet"})
    e = run_with(tmp_path, policy=p)
    assert collect_calls(e, "verifier") == []
    assert "verifier model equals builder model" in reasons(e)
    assert "verifier-model-equals-builder" in codes_in_comment(e)
    assert e.ledger.rows()[-1]["verify"]["model_verdict"] == "not_run"


def test_verifier_model_equal_to_a_retry_round_model_is_not_run(tmp_path):
    base = pol.load(REPO)
    p = dataclasses.replace(base, routing={**base.routing, "verifier": "fable"})
    e = run_with(tmp_path, policy=p, gate_results=[("FAIL", "x"), ("FAIL", "y"), ("PASS", "")])
    builds = [c for c in e.launcher.calls if c["role"] == "build"]
    assert [c["model"] for c in builds] == ["sonnet", "sonnet", "fable"]
    assert collect_calls(e, "verifier") == []
    assert "verifier model equals builder model" in reasons(e)


def test_comparison_is_case_and_space_insensitive(tmp_path):
    base = pol.load(REPO)
    p = dataclasses.replace(base, routing={**base.routing, "verifier": " Sonnet "})
    e = run_with(tmp_path, policy=p)
    assert "verifier model equals builder model" in reasons(e)


# --- canary, hash mismatch, sealed paths ------------------------------------------------------------

def test_canary_in_the_build_diff_is_a_t2_reason(tmp_path):
    e = Env(tmp_path)
    e.add()

    def on_run(role, prompt, cwd):
        if role == "build":
            e.ws.diff_text_value = "+ stolen " + manifest(e)["canary"]
    e.launcher.on_run = on_run
    R.run_once(e.ctx())
    assert "sealed canary found in build output" in reasons(e) and "sealed-canary" in codes_in_comment(e)


def test_canary_in_the_builder_result_text_is_a_t2_reason(tmp_path):
    e = Env(tmp_path)
    e.add()
    token = {}

    class Leaky(Lc.FakeLauncher):
        def run(self, role, prompt, cwd, model=None, max_budget_usd=None):
            res = super().run(role, prompt, cwd, model, max_budget_usd)
            if role == "build":
                res = dataclasses.replace(res, text="done " + manifest(e)["canary"])
            return res
    e.launcher = Leaky(routing=e.policy.routing, collect_handler=good_collect)
    R.run_once(e.ctx())
    assert "sealed canary found in build output" in reasons(e)


def test_no_canary_reason_for_a_clean_build(env):
    R.run_once(env.ctx())
    assert "sealed canary found in build output" not in reasons(env)


def test_tampered_sealed_patch_is_refused_before_use(tmp_path):
    e = Env(tmp_path)
    e.add()

    def on_run(role, prompt, cwd):
        if role == "build":
            with open(sealed_dir(e) / "sealed.patch", "ab") as f:
                f.write(b"\n")
    e.launcher.on_run = on_run
    R.run_once(e.ctx())
    assert "sealed bundle hash mismatch" in reasons(e) and "sealed-hash-mismatch" in codes_in_comment(e)
    assert e.verifier.calls[0]["bundle"] is None
    assert e.ledger.rows()[-1]["verify"]["sealed_available"] is False


def test_missing_sealed_store_is_unavailable_not_a_crash(tmp_path):
    e = Env(tmp_path)
    e.add()

    def on_run(role, prompt, cwd):
        if role == "build":
            import shutil
            shutil.rmtree(sealed_dir(e))
    e.launcher.on_run = on_run
    res = R.run_once(e.ctx())
    assert res.outcome == "awaiting-human"
    assert any(r.startswith("sealed tests unavailable") for r in reasons(e))


def test_sealed_paths_in_the_build_diff_are_a_t2_reason(tmp_path):
    e = run_with(tmp_path, diff=W.DiffStats(["skills/a/x.py", "tests/sealed/issue-1/test_acc.py"], 20, 0, 0))
    assert "sealed path in build diff" in reasons(e) and "sealed-path-touched" in codes_in_comment(e)


# --- the sealed bytes stay out of everything the builder can see ----------------------------------------

def test_sealed_patch_bytes_never_reach_a_builder_prompt_or_a_worktree_file(tmp_path):
    e = Env(tmp_path, gate_results=[("FAIL", "x"), ("FAIL", "y"), ("PASS", "")])
    e.add()
    R.run_once(e.ctx())
    patch = (sealed_dir(e) / "sealed.patch").read_bytes().decode()
    token = manifest(e)["canary"]
    for c in e.launcher.calls:
        if c["kind"] == "run" or c["role"] == "verifier":
            assert "tests/sealed" not in c["prompt"] and patch not in c["prompt"] and token not in c["prompt"]
    for p in e.root.rglob("*"):
        if p.is_file() and e.state not in p.parents:
            assert patch not in p.read_text(errors="ignore") and token not in p.read_text(errors="ignore")
    assert not (e.root / "wt-1" / "tests").exists()


# --- end to end with real git, the real ActionsLauncher and a scripted gh -----------------------------

def test_full_stack_sealed_bytes_never_pushed_and_never_in_the_worktree(tmp_path, monkeypatch):
    for k, v in dict(GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t").items():
        monkeypatch.setenv(k, v)
    origin = tmp_path / "origin.git"
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(origin))
    seed = tmp_path / "seed"
    git(tmp_path, "clone", "-q", str(origin), str(seed))
    git(seed, "checkout", "-q", "-b", "main")
    (seed / "a.txt").write_text("a\n")
    git(seed, "add", "-A")
    git(seed, "commit", "-qm", "init")
    git(seed, "push", "-q", "origin", "main")
    root = tmp_path / "root"
    git(tmp_path, "clone", "-q", str(origin), str(root))
    policy = pol.load(REPO)
    sealed_patch = SL.new_file_patch("tests/sealed/issue-1/test_acc.py", b"def test_acc():\n    assert True\n")
    spec_patch = SL.new_file_patch("specs/1.md", b"# spec\n")
    build_patch = SL.new_file_patch("skills/a/x.py", b"X = 1\n")
    wt = root / ".worktrees" / "factory-1"
    texts = {"spec": "spec done", "sealed_test_author": "sealed done", "build": "built", "verifier": AGREE_TEXT}
    patches = {"spec": spec_patch, "sealed_test_author": sealed_patch, "build": build_patch, "verifier": b""}

    def artifacts(fields):
        role = fields["role"]
        d = good_result(fields, git(wt, "rev-parse", "HEAD").strip(), result=texts[role], model=fields["model"])
        return {"result.json": json.dumps(d).encode(), "changes.patch": patches[role]}
    gh = FakeGh(artifacts=artifacts)
    rids = iter(f"{i:016x}" for i in range(1, 50))
    c, _ = client(gh, tmp_path)
    launcher = A.ActionsLauncher(policy, c, runner=gh, new_request_id=lambda: next(rids))
    tracker = T.FakeTracker(policy.allowlisted_authors)
    tracker.add_issue(1, "Add thing", BODY, "RynoHooptyGIT", ["factory:queued"], "2026-11-01")
    ctx = R.Context(root=root, policy=policy, tracker=tracker, launcher=launcher, gates=G.FakeGateRunner([("PASS", "")]),
                    workspace=W.GitWorkspace(root), ledger=Ld.Ledger(tmp_path / "state" / "ledger.jsonl"),
                    state_dir=tmp_path / "state", now=lambda: NOW, sandbox="actions",
                    verifier=V.FakeVerifier(default=GOOD_VERIFY))
    res = R.run_once(ctx)
    assert res.outcome == "awaiting-human", res.reasons
    sealed_text = sealed_patch.decode()
    # nothing sealed in any command line or in any file of the worktree or of the pushed branch
    for argv in gh.calls:
        assert not any(sealed_text in a or "tests/sealed" in a for a in argv), argv
    pushes = [a for a in gh.calls if a[0] == "git" and "push" in a]
    assert pushes and all(a[a.index("push") + 1] == "origin" and a[-1].startswith("refs/heads/factory/1-") for a in pushes)
    assert all(not any(x.startswith("--force") or x == "+" for x in a) for a in pushes)
    assert not (wt / "tests").exists()
    assert git(wt, "status", "--porcelain").strip() == ""
    branch = git(wt, "rev-parse", "--abbrev-ref", "HEAD").strip()
    assert "tests/sealed" not in git(origin, "ls-tree", "-r", "--name-only", branch)
    assert "tests/sealed" not in git(wt, "ls-tree", "-r", "--name-only", "HEAD")
    for fields in (d["fields"] for d in gh.dispatched):
        blob = base64.b64decode(fields.get("prompt_b64", ""))
        assert b"tests/sealed/issue-1/test_acc.py" not in gzip.decompress(blob) or fields["role"] == "sealed_test_author"
    assert [d["fields"]["role"] for d in gh.dispatched] == ["spec", "sealed_test_author", "build", "verifier"]
    # the sealed author ran from the spec commit on the pushed branch, the builder's prompt knows nothing of it
    build_prompt = gzip.decompress(base64.b64decode(gh.dispatched[2]["fields"]["prompt_b64"])).decode()
    assert "sealed" not in build_prompt.lower()
