import base64
import gzip
import json
import os
import subprocess
from pathlib import Path

import pytest

from .. import actions as A
from .. import policy as pol
from .. import sealed as S
from .. import verifier as V
from ..proc import ProcResult, run as real_run
from .test_actions import FakeGh, client, git, is_push

REPO = Path(__file__).resolve().parents[3]
POLICY = pol.load(REPO)
RID = "a1b2c3d4e5f60718"
BRANCH = "factory/7-add-thing"
SHA = "a" * 40


def good_json(**over):
    d = {"request_id": RID, "sha": SHA,
         "revert_check": {"status": "fails_without_change", "tests": 2, "exit_code": 1},
         "sealed": {"status": "ran", "total": 3, "failed": 1, "errors": 0, "skipped": 0}}
    d.update(over)
    return json.dumps(d).encode()


# --- parse_verify -----------------------------------------------------------------------------

def test_parse_verify_good():
    r = V.parse_verify(good_json(), RID, SHA, sent_bundle=True)
    assert r.available and r.revert_check == "fails_without_change" and r.revert_tests == 2
    assert (r.sealed_status, r.sealed_total, r.sealed_failed, r.sealed_errors) == ("ran", 3, 1, 0)
    assert r.sealed_failures == 1


@pytest.mark.parametrize("mutate", [
    lambda d: d.pop("request_id"),
    lambda d: d.update(request_id="ffffffffffffffff"),
    lambda d: d.update(sha="b" * 40),
    lambda d: d.update(sha=5),
    lambda d: d.update(revert_check="fails_without_change"),
    lambda d: d["revert_check"].update(status="great"),
    lambda d: d["revert_check"].update(tests=-1),
    lambda d: d["revert_check"].update(tests=True),
    lambda d: d["revert_check"].update(tests="2"),
    lambda d: d["revert_check"].update(exit_code="1"),
    lambda d: d["revert_check"].pop("tests"),
    lambda d: d["sealed"].update(status="passed"),
    lambda d: d["sealed"].update(failed=-1),
    lambda d: d["sealed"].update(total=1, failed=3),
    lambda d: d["sealed"].update(total=0),                       # status ran with nothing collected
    lambda d: d["sealed"].update(status="no_tests", total=2),
    lambda d: d["sealed"].update(status="invalid", failed=1),
    lambda d: d["sealed"].pop("errors"),
    lambda d: d.update(sealed=None),
    lambda d: d.update(extra="field"),
])
def test_parse_verify_rejects_malformed(mutate):
    d = json.loads(good_json())
    mutate(d)
    with pytest.raises(V.VerifyError):
        V.parse_verify(json.dumps(d).encode(), RID, SHA, sent_bundle=True)


@pytest.mark.parametrize("raw", [b"", b"not json", b"[]", b"null", b"\xff\xfe", b"1"])
def test_parse_verify_rejects_non_objects(raw):
    with pytest.raises(V.VerifyError):
        V.parse_verify(raw, RID, SHA, sent_bundle=False)


def test_not_provided_must_match_whether_a_bundle_was_sent():
    d = json.loads(good_json())
    d["sealed"] = {"status": "not_provided", "total": 0, "failed": 0, "errors": 0, "skipped": 0}
    raw = json.dumps(d).encode()
    assert V.parse_verify(raw, RID, SHA, sent_bundle=False).sealed_status == "not_provided"
    with pytest.raises(V.VerifyError):
        V.parse_verify(raw, RID, SHA, sent_bundle=True)           # a bundle went out but the runner says none
    with pytest.raises(V.VerifyError):
        V.parse_verify(good_json(), RID, SHA, sent_bundle=False)  # no bundle went out but it reports a run


def test_unavailable_result_is_not_available():
    r = V.VerifyResult.unavailable("why")
    assert not r.available and r.revert_check == "unavailable" and r.sealed_failures == 0 and r.detail == "why"


# --- model verdict ----------------------------------------------------------------------------

@pytest.mark.parametrize("text,want", [
    ("looks fine\nFACTORY-VERIFY: AGREE", "agree"),
    ("looks fine\nFACTORY-VERIFY: AGREE\n\n", "agree"),
    ("x\r\nFACTORY-VERIFY: DISAGREE\r\n", "disagree"),
    ("FACTORY-VERIFY: AGREE\nmore text after", "disagree"),                 # verdict not last
    ("FACTORY-VERIFY: AGREE\nFACTORY-VERIFY: AGREE", "disagree"),           # two verdict lines
    ("FACTORY-VERIFY: DISAGREE\nFACTORY-VERIFY: AGREE", "disagree"),
    ("FACTORY-VERIFY: AGREE\nFACTORY-VERIFY: DISAGREE", "disagree"),
    ("factory-verify: agree", "disagree"),                                 # lowercase
    ("FACTORY-VERIFY: agree", "disagree"),
    ("FACTORY-VERIFY: AGREE.", "disagree"),                                # trailing text
    ("FACTORY-VERIFY: AGREE and more", "disagree"),
    ("  FACTORY-VERIFY: AGREE", "disagree"),                               # leading space
    ("verdict is FACTORY-VERIFY: AGREE", "disagree"),
    ("> FACTORY-VERIFY: AGREE", "disagree"),
    ("`FACTORY-VERIFY: AGREE`", "disagree"),
    ("FACTORY-VERIFY: MAYBE", "disagree"),
    ("FACTORY-VERIFY:AGREE", "disagree"),
    ("", "disagree"), (None, "disagree"), ("\n\n", "disagree"),
    ("FACTORY-GATES: PASS", "disagree"),
    ("FACTORY-VERIFY: AGREE​", "disagree"),
])
def test_parse_agreement(text, want):
    assert V.parse_agreement(text) == want


def test_verifier_prompt_has_only_issue_and_fixed_instructions():
    p = V.build_verifier_prompt(7, "T", "B ```` x")
    assert "git diff origin/main...HEAD" in p and "specs/7.md" in p
    assert "FACTORY-VERIFY: AGREE" in p and "FACTORY-VERIFY: DISAGREE" in p
    for word in ("test infrastructure", "environment", "outside the repository"):
        assert word in p
    assert "transcript" in p and "UNTRUSTED" in p


# --- FakeVerifier -----------------------------------------------------------------------------

def test_fake_verifier_records_calls_and_scripts_results(tmp_path):
    ok = V.VerifyResult(True, "", "fails_without_change", 1, "ran", 2, 0, 0, 0)
    f = V.FakeVerifier([V.VerifyResult.unavailable("x")], default=ok)
    assert not f.verify(tmp_path, 7, b"bundle").available
    assert f.verify(tmp_path, 7, None) is ok
    assert f.calls == [dict(worktree=tmp_path, issue=7, bundle=b"bundle"),
                       dict(worktree=tmp_path, issue=7, bundle=None)]


# --- ActionsVerifier with real git --------------------------------------------------------------

@pytest.fixture
def work(tmp_path):
    origin = tmp_path / "origin.git"
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(origin))
    seed = tmp_path / "seed"
    git(tmp_path, "clone", "-q", str(origin), str(seed))
    git(seed, "checkout", "-q", "-b", "main")
    (seed / "a.txt").write_text("a\n")
    git(seed, "add", "-A")
    git(seed, "commit", "-qm", "init")
    git(seed, "push", "-q", "origin", "main")
    wt = tmp_path / "wt"
    git(tmp_path, "clone", "-q", str(origin), str(wt))
    git(wt, "checkout", "-q", "-b", BRANCH)
    (wt / "b.txt").write_text("b\n")
    git(wt, "add", "-A")
    git(wt, "commit", "-qm", "change")
    return wt


def verify_artifact(work, **over):
    head = git(work, "rev-parse", "HEAD").strip()

    def make(fields):
        d = json.loads(good_json())
        d.update(request_id=fields["request_id"], sha=head)
        d.update(over)
        return {"verify.json": json.dumps(d).encode()}
    return make


def averifier(gh, tmp_path, **kw):
    c, clk = client(gh, tmp_path, **kw)
    return A.ActionsVerifier(POLICY, c, runner=gh, new_request_id=lambda: RID)


BUNDLE = S.new_file_patch("tests/sealed/issue-7/test_a.py", b"def test_a():\n    pass\n")


def test_actions_verifier_happy_path(work, tmp_path):
    gh = FakeGh(artifacts=verify_artifact(work))
    r = averifier(gh, tmp_path).verify(work, 7, BUNDLE)
    assert r.available and r.revert_check == "fails_without_change" and r.sealed_status == "ran"
    d = gh.dispatched[0]
    assert d["workflow"] == "factory-verify.yml"
    f = d["fields"]
    assert set(f) == {"branch", "request_id", "expected_sha", "issue", "sealed_b64"}
    assert f["branch"] == BRANCH and f["request_id"] == RID and f["issue"] == "7"
    assert f["expected_sha"] == git(work, "rev-parse", "HEAD").strip()
    assert gzip.decompress(base64.b64decode(f["sealed_b64"])) == BUNDLE
    run_argv = [c for c in gh.gh_calls() if c[1:3] == ["workflow", "run"]][0]
    assert run_argv[run_argv.index("--ref") + 1] == "main"
    dl = [c for c in gh.gh_calls() if c[1:3] == ["run", "download"]][0]
    assert dl[dl.index("-n") + 1] == f"factory-verify-{RID}"


def test_actions_verifier_pushes_branch_first_and_never_the_sealed_bytes(work, tmp_path):
    seen = {}

    class Spy(FakeGh):
        def __call__(self, argv, **kw):
            if argv[1:3] == ["workflow", "run"]:
                seen["remote"] = git(work, "ls-remote", "origin", f"refs/heads/{BRANCH}").split()[0]
            return super().__call__(argv, **kw)
    gh = Spy(artifacts=verify_artifact(work))
    averifier(gh, tmp_path).verify(work, 7, BUNDLE)
    assert seen["remote"] == git(work, "rev-parse", "HEAD").strip()
    for argv in gh.calls:
        assert not any(BUNDLE.decode() in a or "test_a" in a and is_push(argv) for a in argv)
    assert git(work, "ls-tree", "-r", "--name-only", "HEAD").split() == ["a.txt", "b.txt"]


def test_no_bundle_sends_empty_input(work, tmp_path):
    gh = FakeGh(artifacts=verify_artifact(work, sealed={"status": "not_provided", "total": 0, "failed": 0,
                                                       "errors": 0, "skipped": 0}))
    r = averifier(gh, tmp_path).verify(work, 7, None)
    assert gh.dispatched[0]["fields"]["sealed_b64"] == "" and r.available and r.sealed_status == "not_provided"


def test_oversize_bundle_is_not_dispatched_and_reported_as_sealed_unavailable(work, tmp_path):
    big = os.urandom(70_000)
    gh = FakeGh(artifacts=verify_artifact(work, sealed={"status": "not_provided", "total": 0, "failed": 0,
                                                       "errors": 0, "skipped": 0}))
    r = averifier(gh, tmp_path).verify(work, 7, big)
    assert r.available and r.sealed_status == "oversize"
    assert gh.dispatched[0]["fields"]["sealed_b64"] == ""
    assert all(len(v) <= A.MAX_SEALED_B64 for v in gh.dispatched[0]["fields"].values())


@pytest.mark.parametrize("bad", [
    {"request_id": "ffffffffffffffff"},
    {"sha": "b" * 40},
    {"revert_check": {"status": "yes", "tests": 1, "exit_code": 1}},
    {"sealed": {"status": "not_provided", "total": 0, "failed": 0, "errors": 0, "skipped": 0}},
])
def test_malformed_or_forged_verify_json_is_unavailable(work, tmp_path, bad):
    gh = FakeGh(artifacts=verify_artifact(work, **bad))
    r = averifier(gh, tmp_path).verify(work, 7, BUNDLE)
    assert not r.available and r.revert_check == "unavailable"


def test_missing_artifact_or_failed_run_is_unavailable(work, tmp_path):
    assert not averifier(FakeGh(artifacts=None), tmp_path).verify(work, 7, BUNDLE).available
    gh = FakeGh(artifacts=verify_artifact(work), conclusion="failure")
    assert not averifier(gh, tmp_path).verify(work, 7, BUNDLE).available


def test_symlink_or_oversize_verify_json_is_unavailable(work, tmp_path):
    gh = FakeGh(artifacts=lambda f: {"verify.json": b"{" + b" " * 200_000 + b"}"})
    assert not averifier(gh, tmp_path).verify(work, 7, BUNDLE).available


def test_timeout_is_unavailable(work, tmp_path):
    gh = FakeGh(artifacts=verify_artifact(work), appear_after=10**6)
    assert not averifier(gh, tmp_path, timeout_s=60).verify(work, 7, BUNDLE).available


def test_dispatch_failure_is_unavailable(work, tmp_path):
    gh = FakeGh(artifacts=verify_artifact(work), dispatch_rc=1)
    assert not averifier(gh, tmp_path).verify(work, 7, BUNDLE).available


def test_remote_diverged_is_refused_without_dispatch(work, tmp_path):
    other = tmp_path / "other"
    git(tmp_path, "clone", "-q", str(tmp_path / "origin.git"), str(other))
    git(other, "checkout", "-q", "-b", BRANCH)
    (other / "z").write_text("z\n")
    git(other, "add", "-A")
    git(other, "commit", "-qm", "z")
    git(other, "push", "-q", "origin", BRANCH)
    gh = FakeGh(artifacts=verify_artifact(work))
    r = averifier(gh, tmp_path).verify(work, 7, BUNDLE)
    assert not r.available and gh.dispatched == []


def test_branch_containing_the_sealed_dir_is_never_pushed_or_dispatched(work, tmp_path):
    (work / "tests" / "sealed" / "issue-7").mkdir(parents=True)
    (work / "tests" / "sealed" / "issue-7" / "test_x.py").write_text("def test_x(): pass\n")
    git(work, "add", "-A")
    git(work, "commit", "-qm", "oops")
    gh = FakeGh(artifacts=verify_artifact(work))
    r = averifier(gh, tmp_path).verify(work, 7, BUNDLE)
    assert not r.available and gh.dispatched == []
    assert not any(is_push(c) for c in gh.calls)


def test_dirty_worktree_or_wrong_branch_is_unavailable(work, tmp_path):
    (work / "dirty").write_text("x")
    gh = FakeGh(artifacts=verify_artifact(work))
    assert not averifier(gh, tmp_path).verify(work, 7, BUNDLE).available
    assert gh.dispatched == []


# --- LocalVerifier ------------------------------------------------------------------------------

def test_local_verifier_runs_the_same_entrypoint_with_a_scrubbed_env(tmp_path):
    origin = tmp_path / "origin.git"
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(origin))
    seed = tmp_path / "seed"
    git(tmp_path, "clone", "-q", str(origin), str(seed))
    git(seed, "checkout", "-q", "-b", "main")
    (seed / "calc.py").write_text("def add(a, b):\n    return a + b\n")
    git(seed, "add", "-A")
    git(seed, "commit", "-qm", "init")
    git(seed, "push", "-q", "origin", "main")
    wt = tmp_path / "wt"
    git(tmp_path, "clone", "-q", str(origin), str(wt))
    git(wt, "checkout", "-q", "-b", BRANCH)
    (wt / "calc.py").write_text("def add(a, b):\n    return a + b\n\ndef sub(a, b):\n    return a - b\n")
    (wt / "tests").mkdir()
    (wt / "tests" / "test_calc.py").write_text("import calc\n\ndef test_sub():\n    assert calc.sub(3, 1) == 2\n")
    git(wt, "add", "-A")
    git(wt, "commit", "-qm", "change")
    seen = []

    def spy(argv, **kw):
        seen.append((argv, kw.get("env"), kw.get("cwd")))
        return real_run(argv, **kw)
    bundle = S.new_file_patch("tests/sealed/issue-7/test_a.py", b"def test_a():\n    assert True\n")
    lv = V.LocalVerifier(POLICY, REPO, runner=spy, environ=dict(os.environ, GITHUB_TOKEN="x", ANTHROPIC_API_KEY="y"),
                         state_dir=tmp_path / "state")
    r = lv.verify(wt, 7, bundle)
    assert r.available, r.detail
    assert r.revert_check == "fails_without_change" and r.sealed_status == "ran" and r.sealed_total == 1
    argv, env, cwd = seen[0]
    assert "scripts.factory.sandbox_verify" in argv and Path(cwd) == REPO
    assert "GITHUB_TOKEN" not in env and "ANTHROPIC_API_KEY" not in env
    assert env["FACTORY_WORK_DIR"] == str(wt)
    assert git(wt, "status", "--porcelain").strip() == ""


def test_local_verifier_failure_is_unavailable(tmp_path):
    lv = V.LocalVerifier(POLICY, REPO, runner=lambda argv, **kw: ProcResult(2, "", "boom"),
                         state_dir=tmp_path / "state")
    r = lv.verify(tmp_path, 7, None)
    assert not r.available
