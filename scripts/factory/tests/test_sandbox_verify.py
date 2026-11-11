import base64
import gzip
import json
import os
import subprocess
from pathlib import Path

import pytest

from .. import policy as pol
from .. import sandbox_verify as V
from .. import sealed as S

REPO = Path(__file__).resolve().parents[3]
POLICY = pol.load(REPO)
RID = "0123456789abcdef"
BRANCH = "factory/7-thing"

CALC = "def add(a, b):\n    return a + b\n"
CALC_SUB = CALC + "\ndef sub(a, b):\n    return a - b\n"


def git(cwd, *args):
    env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t",
               GIT_COMMITTER_EMAIL="t@t")
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True, env=env).stdout


def world(tmp_path, change, main_files=None):
    """A clone on a factory branch whose origin/main is the base. `change(work)` edits the tree."""
    origin = tmp_path / "origin.git"
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(origin))
    seed = tmp_path / "seed"
    git(tmp_path, "clone", "-q", str(origin), str(seed))
    git(seed, "checkout", "-q", "-b", "main")
    files = {"calc.py": CALC, "docs/a.md": "a\n"}
    files.update(main_files or {})
    for name, text in files.items():
        p = seed / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    git(seed, "add", "-A")
    git(seed, "commit", "-qm", "init")
    git(seed, "push", "-q", "origin", "main")
    work = tmp_path / "work"
    git(tmp_path, "clone", "-q", str(origin), str(work))
    git(work, "checkout", "-q", "-b", BRANCH)
    change(work)
    git(work, "add", "-A")
    git(work, "commit", "-qm", "change")
    return work


def write(work, name, text):
    p = work / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


def sub_change(work):
    write(work, "calc.py", CALC_SUB)
    write(work, "tests/test_calc.py", "import calc\n\ndef test_sub():\n    assert calc.sub(3, 1) == 2\n")


def env_for(tmp_path, work, bundle=None, sha=None, **over):
    e = {"FACTORY_BRANCH": BRANCH, "FACTORY_REQUEST_ID": RID, "FACTORY_ISSUE": "7",
         "FACTORY_EXPECTED_SHA": sha or git(work, "rev-parse", "HEAD").strip(),
         "FACTORY_SEALED_B64": base64.b64encode(gzip.compress(bundle, mtime=0)).decode() if bundle else "",
         "FACTORY_WORK_DIR": str(work), "FACTORY_OUT_DIR": str(tmp_path / "out"),
         "PATH": os.environ["PATH"], "HOME": str(tmp_path), "LANG": "C", "GITHUB_TOKEN": "ghs_nope"}
    e.update(over)
    return e


def go(tmp_path, work, bundle=None, **over):
    rc = V.run(env_for(tmp_path, work, bundle, **over), POLICY)
    out = tmp_path / "out" / "verify.json"
    return rc, (json.loads(out.read_text()) if out.exists() else None)


def sealed_bundle(files, issue=7):
    return b"".join(S.new_file_patch(f"tests/sealed/issue-{issue}/{n}", t.encode()) for n, t in files.items())


# --- revert check -----------------------------------------------------------------------------

def test_new_test_fails_without_the_change(tmp_path):
    w = world(tmp_path, sub_change)
    rc, d = go(tmp_path, w)
    assert rc == 0
    assert d["revert_check"]["status"] == "fails_without_change" and d["revert_check"]["tests"] == 1
    assert d["request_id"] == RID and d["sha"] == git(w, "rev-parse", "HEAD").strip()


def test_new_test_that_passes_without_the_change_is_reported(tmp_path):
    def change(w):
        write(w, "calc.py", CALC + "\n# comment\n")
        write(w, "tests/test_calc.py", "import calc\n\ndef test_add():\n    assert calc.add(1, 2) == 3\n")
    w = world(tmp_path, change)
    rc, d = go(tmp_path, w)
    assert d["revert_check"]["status"] == "passes_without_change"


def test_import_error_without_the_change_counts_as_failing(tmp_path):
    def change(w):
        write(w, "newmod.py", "def f():\n    return 1\n")
        write(w, "tests/test_newmod.py", "import newmod\n\ndef test_f():\n    assert newmod.f() == 1\n")
    w = world(tmp_path, change)
    rc, d = go(tmp_path, w)
    assert d["revert_check"]["status"] == "fails_without_change"
    assert d["revert_check"]["exit_code"] == 2


def test_code_change_without_tests_is_no_new_tests(tmp_path):
    w = world(tmp_path, lambda w: write(w, "calc.py", CALC_SUB))
    rc, d = go(tmp_path, w)
    assert d["revert_check"]["status"] == "no_new_tests" and d["revert_check"]["tests"] == 0


def test_test_only_change_has_nothing_to_revert(tmp_path):
    w = world(tmp_path, lambda w: write(w, "tests/test_calc.py",
                                        "import calc\n\ndef test_add():\n    assert calc.add(1, 1) == 2\n"))
    rc, d = go(tmp_path, w)
    assert d["revert_check"]["status"] == "nothing_to_revert"


def test_test_file_with_no_tests_is_no_new_tests(tmp_path):
    def change(w):
        write(w, "calc.py", CALC_SUB)
        write(w, "tests/test_calc.py", "import calc\n")
    w = world(tmp_path, change)
    rc, d = go(tmp_path, w)
    assert d["revert_check"]["status"] == "no_new_tests"


def test_new_test_that_fails_even_with_the_change_is_fails_with_change(tmp_path):
    def change(w):
        write(w, "calc.py", CALC_SUB)
        write(w, "tests/test_calc.py", "import calc\n\ndef test_sub():\n    assert calc.sub(3, 1) == 99\n")
    w = world(tmp_path, change)
    rc, d = go(tmp_path, w)
    assert d["revert_check"]["status"] == "fails_with_change"


def test_changed_existing_test_file_is_included(tmp_path):
    def change(w):
        write(w, "calc.py", CALC_SUB)
        write(w, "tests/test_calc.py", "import calc\n\ndef test_add():\n    assert calc.add(1, 2) == 3\n\n"
                                       "def test_sub():\n    assert calc.sub(3, 1) == 2\n")
    w = world(tmp_path, change, main_files={
        "tests/test_calc.py": "import calc\n\ndef test_add():\n    assert calc.add(1, 2) == 3\n"})
    rc, d = go(tmp_path, w)
    assert d["revert_check"]["status"] == "fails_without_change" and d["revert_check"]["tests"] == 1


def test_changes_to_conftest_are_reverted_for_the_check(tmp_path):
    # the branch adds a conftest that skips everything; the revert restores main's state for it
    def change(w):
        write(w, "calc.py", CALC_SUB)
        write(w, "tests/conftest.py", "import pytest\n\ndef pytest_collection_modifyitems(items):\n"
                                      "    for i in items:\n        i.add_marker(pytest.mark.skip)\n")
        write(w, "tests/test_calc.py", "import calc\n\ndef test_sub():\n    assert calc.sub(3, 1) == 2\n")
    w = world(tmp_path, change)
    rc, d = go(tmp_path, w)
    # at HEAD every test is skipped (exit 0, nothing passed): that is not a passing new test, so a
    # skip-everything conftest cannot turn "fails after reverting conftest" into agreement
    assert d["revert_check"]["status"] == "fails_with_change"


def test_revert_uses_a_scratch_worktree_and_leaves_work_untouched(tmp_path):
    w = world(tmp_path, sub_change)
    before = git(w, "status", "--porcelain=v1", "--ignored")
    go(tmp_path, w)
    assert git(w, "status", "--porcelain=v1", "--ignored") == before
    assert (w / "calc.py").read_text() == CALC_SUB
    assert len(git(w, "worktree", "list").strip().splitlines()) == 1


def test_head_mismatch_writes_nothing_and_fails(tmp_path):
    w = world(tmp_path, sub_change)
    rc, d = go(tmp_path, w, sha="0" * 40)
    assert rc != 0 and d is None


def test_pytest_timeout_is_error(tmp_path, monkeypatch):
    def change(w):
        write(w, "calc.py", CALC_SUB)
        write(w, "tests/test_calc.py", "import time\n\ndef test_slow():\n    time.sleep(30)\n")
    w = world(tmp_path, change)
    monkeypatch.setattr(V, "PYTEST_TIMEOUT_S", 2)
    rc, d = go(tmp_path, w)
    assert d["revert_check"]["status"] == "error"


# --- sealed run -------------------------------------------------------------------------------

def test_no_bundle_means_not_provided(tmp_path):
    w = world(tmp_path, sub_change)
    rc, d = go(tmp_path, w)
    assert d["sealed"] == {"status": "not_provided", "total": 0, "failed": 0, "errors": 0, "skipped": 0}


def test_sealed_run_counts_pass_and_fail(tmp_path):
    w = world(tmp_path, sub_change)
    b = sealed_bundle({"test_acc.py": "import calc\n\ndef test_ok():\n    assert calc.sub(3, 1) == 2\n\n"
                                      "def test_bad():\n    assert calc.sub(1, 1) == 5\n\n"
                                      "def test_ok2():\n    assert True\n"})
    rc, d = go(tmp_path, w, b)
    assert d["sealed"] == {"status": "ran", "total": 3, "failed": 1, "errors": 0, "skipped": 0}


def test_sealed_run_all_pass(tmp_path):
    w = world(tmp_path, sub_change)
    b = sealed_bundle({"test_acc.py": "import calc\n\ndef test_ok():\n    assert calc.sub(3, 1) == 2\n"})
    rc, d = go(tmp_path, w, b)
    assert d["sealed"]["status"] == "ran" and d["sealed"]["failed"] == 0 and d["sealed"]["total"] == 1


def test_sealed_collection_error_counts_as_error(tmp_path):
    w = world(tmp_path, sub_change)
    b = sealed_bundle({"test_acc.py": "import does_not_exist\n\ndef test_x():\n    pass\n"})
    rc, d = go(tmp_path, w, b)
    assert d["sealed"]["status"] == "ran" and d["sealed"]["errors"] >= 1


def test_sealed_zero_collected_tests_is_not_success(tmp_path):
    w = world(tmp_path, sub_change)
    b = sealed_bundle({"test_acc.py": "def helper():\n    return 1\n"})
    rc, d = go(tmp_path, w, b)
    assert d["sealed"]["status"] == "no_tests" and d["sealed"]["total"] == 0


def test_sealed_all_skipped_is_not_success(tmp_path):
    w = world(tmp_path, sub_change)
    b = sealed_bundle({"test_acc.py": "import pytest\n\n@pytest.mark.skip\ndef test_x():\n    pass\n"})
    rc, d = go(tmp_path, w, b)
    assert d["sealed"]["status"] == "no_tests" and d["sealed"]["skipped"] == 1


def test_sealed_pytest_crash_is_reported_as_crash(tmp_path):
    w = world(tmp_path, sub_change)
    b = sealed_bundle({"test_acc.py": "import os\nos._exit(7)\n\ndef test_x():\n    pass\n"})
    rc, d = go(tmp_path, w, b)
    assert d["sealed"]["status"] == "crash"


def test_sealed_timeout_is_crash(tmp_path, monkeypatch):
    w = world(tmp_path, sub_change)
    b = sealed_bundle({"test_acc.py": "import time\n\ndef test_x():\n    time.sleep(30)\n"})
    monkeypatch.setattr(V, "PYTEST_TIMEOUT_S", 2)
    rc, d = go(tmp_path, w, b)
    assert d["sealed"]["status"] == "crash"


def test_bundle_touching_a_path_outside_the_sealed_dir_is_invalid(tmp_path):
    w = world(tmp_path, sub_change)
    b = sealed_bundle({"test_acc.py": "def test_x():\n    pass\n"}) + S.new_file_patch("calc.py.evil", b"x\n")
    rc, d = go(tmp_path, w, b)
    assert d["sealed"]["status"] == "invalid"
    assert not (w / "calc.py.evil").exists()


def test_bundle_that_does_not_apply_is_invalid(tmp_path):
    w = world(tmp_path, sub_change)
    b = sealed_bundle({"test_acc.py": "def test_x():\n    pass\n"})
    (w / "tests" / "sealed" / "issue-7").mkdir(parents=True)
    write(w, "tests/sealed/issue-7/test_acc.py", "already here\n")
    git(w, "add", "-A")
    git(w, "commit", "-qm", "planted")
    rc, d = go(tmp_path, w, b)
    assert d["sealed"]["status"] == "invalid"


def test_sealed_run_leaves_work_clean(tmp_path):
    w = world(tmp_path, sub_change)
    b = sealed_bundle({"test_acc.py": "def test_x():\n    assert True\n"})
    go(tmp_path, w, b)
    assert git(w, "status", "--porcelain").strip() == ""
    assert not (w / "tests" / "sealed").exists()
    assert len(git(w, "worktree", "list").strip().splitlines()) == 1


def test_sealed_tests_do_not_run_in_the_revert_check(tmp_path):
    w = world(tmp_path, lambda w: write(w, "calc.py", CALC_SUB))
    b = sealed_bundle({"test_acc.py": "def test_x():\n    assert True\n"})
    rc, d = go(tmp_path, w, b)
    assert d["revert_check"]["status"] == "no_new_tests" and d["sealed"]["status"] == "ran"


def test_canary_file_in_bundle_is_accepted(tmp_path):
    w = world(tmp_path, sub_change)
    b = sealed_bundle({"test_acc.py": "def test_x():\n    assert True\n"})
    b += S.new_file_patch("tests/sealed/issue-7/canary_" + "c" * 32 + ".txt", b"c" * 32 + b"\n")
    rc, d = go(tmp_path, w, b)
    assert d["sealed"]["status"] == "ran" and d["sealed"]["total"] == 1


# --- inputs -----------------------------------------------------------------------------------

@pytest.mark.parametrize("key,value", [
    ("FACTORY_BRANCH", "main"), ("FACTORY_BRANCH", "factory/7-x; rm -rf /"), ("FACTORY_REQUEST_ID", "xyz"),
    ("FACTORY_EXPECTED_SHA", "abc"), ("FACTORY_EXPECTED_SHA", "G" * 40), ("FACTORY_ISSUE", "7; x"),
    ("FACTORY_ISSUE", "-1"), ("FACTORY_ISSUE", ""), ("FACTORY_BRANCH", "factory/8-other"),
    ("FACTORY_SEALED_B64", "not base64!!"), ("FACTORY_SEALED_B64", base64.b64encode(b"plain").decode()),
])
def test_bad_inputs_rejected(tmp_path, key, value):
    w = world(tmp_path, sub_change)
    with pytest.raises(V.VerifyInputError):
        V.validate_inputs(env_for(tmp_path, w, **{key: value}), POLICY)


def test_missing_input_rejected(tmp_path):
    w = world(tmp_path, sub_change)
    e = env_for(tmp_path, w)
    del e["FACTORY_ISSUE"]
    with pytest.raises(V.VerifyInputError):
        V.validate_inputs(e, POLICY)


def test_oversized_decoded_bundle_rejected(tmp_path):
    w = world(tmp_path, sub_change)
    big = base64.b64encode(gzip.compress(b"a" * (POLICY.sealed.max_patch_bytes * 3), mtime=0)).decode()
    with pytest.raises(V.VerifyInputError):
        V.validate_inputs(env_for(tmp_path, w, FACTORY_SEALED_B64=big), POLICY)


def test_main_validate_only_and_bad_args(tmp_path, monkeypatch):
    w = world(tmp_path, sub_change)
    for k, v in env_for(tmp_path, w).items():
        monkeypatch.setenv(k, v)
    assert V.main(["--validate-only"], root=REPO) == 0
    assert V.main(["--bogus"], root=REPO) == 2
    monkeypatch.setenv("FACTORY_BRANCH", "main")
    assert V.main(["--validate-only"], root=REPO) == 2


def test_subprocess_env_has_no_tokens(tmp_path):
    w = world(tmp_path, sub_change)
    seen = []
    real = V.default_run

    def spy(argv, **kw):
        seen.append(kw.get("env"))
        return real(argv, **kw)
    V.run(env_for(tmp_path, w), POLICY, runner=spy)
    assert seen and all(e is not None and "GITHUB_TOKEN" not in e for e in seen)
