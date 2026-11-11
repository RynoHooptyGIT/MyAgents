import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from .. import sealed as S

GOOD = S.new_file_patch("tests/sealed/issue-7/test_acc.py", b"def test_x():\n    assert True\n")
INIT = S.new_file_patch("tests/sealed/issue-7/__init__.py", b"")


def check(patch, issue=7, max_bytes=100_000, **kw):
    return S.validate_sealed_patch(patch, issue, max_bytes, **kw)


def test_good_patch_is_accepted_and_git_agrees(tmp_path):
    assert check(GOOD) == ["tests/sealed/issue-7/test_acc.py"]
    repo = tmp_path / "r"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    (tmp_path / "p.patch").write_bytes(GOOD)
    subprocess.run(["git", "apply", str(tmp_path / "p.patch")], cwd=repo, check=True)
    assert (repo / "tests/sealed/issue-7/test_acc.py").read_text().startswith("def test_x")


def test_init_plus_test_accepted():
    assert sorted(check(GOOD + INIT)) == ["tests/sealed/issue-7/__init__.py", "tests/sealed/issue-7/test_acc.py"]


def test_empty_patch_rejected():
    with pytest.raises(S.SealedInvalid):
        check(b"")


def test_at_least_one_test_file_required():
    with pytest.raises(S.SealedInvalid, match="test_"):
        check(INIT)


@pytest.mark.parametrize("path", [
    "tests/sealed/issue-8/test_a.py",          # other issue
    "tests/sealed/test_a.py",                  # not in the issue directory
    "tests/test_a.py",
    "src/mod.py",
    "tests/sealed/issue-7/../../../x/test_a.py",
    "tests/sealed/issue-7/conftest.py",
    "tests/sealed/issue-7/helper.py",
    "tests/sealed/issue-7/test_a.txt",
    "tests/sealed/issue-7/test_a.pyc",
    "TESTS/SEALED/issue-7/test_a.py",
    ".github/workflows/x.yml",
])
def test_paths_outside_the_issue_directory_or_names_rejected(path):
    patch = GOOD + S.new_file_patch(path, b"x\n")
    with pytest.raises(S.SealedInvalid):
        check(patch)


def test_canary_name_only_allowed_for_bundles():
    canary = S.new_file_patch("tests/sealed/issue-7/canary_" + "a" * 32 + ".txt", b"a" * 32 + b"\n")
    with pytest.raises(S.SealedInvalid):
        check(GOOD + canary)
    assert len(check(GOOD + canary, allow_canary=True)) == 2


def test_two_canaries_rejected_even_for_bundles():
    c1 = S.new_file_patch("tests/sealed/issue-7/canary_" + "a" * 32 + ".txt", b"x\n")
    c2 = S.new_file_patch("tests/sealed/issue-7/canary_" + "b" * 32 + ".txt", b"x\n")
    with pytest.raises(S.SealedInvalid):
        check(GOOD + c1 + c2, allow_canary=True)


def test_modification_of_existing_file_rejected():
    mod = (b"diff --git a/tests/sealed/issue-7/test_acc.py b/tests/sealed/issue-7/test_acc.py\n"
           b"index 1111111..2222222 100644\n--- a/tests/sealed/issue-7/test_acc.py\n"
           b"+++ b/tests/sealed/issue-7/test_acc.py\n@@ -1 +1 @@\n-a\n+b\n")
    with pytest.raises(S.SealedInvalid):
        check(GOOD + mod)


def test_deletion_rejected():
    dele = (b"diff --git a/tests/sealed/issue-7/test_old.py b/tests/sealed/issue-7/test_old.py\n"
            b"deleted file mode 100644\nindex 1111111..0000000\n--- a/tests/sealed/issue-7/test_old.py\n"
            b"+++ /dev/null\n@@ -1 +0,0 @@\n-a\n")
    with pytest.raises(S.SealedInvalid):
        check(GOOD + dele)


def test_rename_rejected():
    ren = (b"diff --git a/tests/sealed/issue-7/test_old.py b/tests/sealed/issue-7/test_new.py\n"
           b"similarity index 100%\nrename from tests/sealed/issue-7/test_old.py\n"
           b"rename to tests/sealed/issue-7/test_new.py\n")
    with pytest.raises(S.SealedInvalid):
        check(GOOD + ren)


def test_rename_out_of_the_sealed_dir_rejected():
    ren = (b"diff --git a/tests/sealed/issue-7/test_old.py b/scripts/x.py\n"
           b"similarity index 100%\nrename from tests/sealed/issue-7/test_old.py\nrename to scripts/x.py\n")
    with pytest.raises(S.SealedInvalid):
        check(GOOD + ren)


@pytest.mark.parametrize("mode", ["100755", "120000", "160000"])
def test_mode_tricks_rejected(mode):
    patch = GOOD.replace(b"new file mode 100644", b"new file mode " + mode.encode())
    with pytest.raises(S.SealedInvalid):
        check(patch)


def test_mode_change_rejected():
    mc = (b"diff --git a/tests/sealed/issue-7/test_acc.py b/tests/sealed/issue-7/test_acc.py\n"
          b"old mode 100644\nnew mode 100755\n")
    with pytest.raises(S.SealedInvalid):
        check(GOOD + mc)


def test_binary_patch_rejected():
    b = (b"diff --git a/tests/sealed/issue-7/test_b.py b/tests/sealed/issue-7/test_b.py\n"
         b"new file mode 100644\nindex 0000000..1111111\nGIT binary patch\nliteral 1\nIcmZPo000310RR91\n\n")
    with pytest.raises(S.SealedInvalid):
        check(GOOD + b)


def test_oversize_rejected():
    big = S.new_file_patch("tests/sealed/issue-7/test_big.py", b"#" + b"x" * 5000 + b"\n")
    with pytest.raises(S.SealedInvalid, match="large"):
        check(GOOD + big, max_bytes=2000)


def test_garbage_rejected():
    with pytest.raises(S.SealedInvalid):
        check(b"this is not a patch at all\n")


def test_unparseable_by_git_rejected():
    bad = GOOD.replace(b"@@ -0,0 +1,2 @@", b"@@ -0,0 +1,5 @@")
    with pytest.raises(S.SealedInvalid):
        check(bad)


def test_header_path_with_traversal_or_git_dir_rejected():
    for p in ("tests/sealed/issue-7/.git/test_a.py", "tests/sealed/issue-7/./test_a.py"):
        with pytest.raises(S.SealedInvalid):
            check(GOOD + S.new_file_patch(p, b"x\n"))


# --- store ----------------------------------------------------------------------------------

def store(tmp_path, token="f" * 32):
    return S.SealedStore(tmp_path / "state", token=lambda: token)


def test_save_writes_patch_and_manifest_outside_repo(tmp_path):
    s = store(tmp_path)
    got = s.save(7, 2, GOOD, "a" * 40)
    d = tmp_path / "state" / "sealed" / "issue-7-a2"
    assert (d / "sealed.patch").read_bytes() == GOOD
    m = json.loads((d / "manifest.json").read_text())
    assert m["patch_sha256"] == hashlib.sha256(GOOD).hexdigest()
    assert m["spec_sha"] == "a" * 40 and m["canary"] == "f" * 32 and m["issue"] == 7 and m["attempt"] == 2
    assert "created_at" in m
    assert got.canary == "f" * 32 and got.patch == GOOD


def test_canary_is_generated_by_the_operator_side_and_differs_per_save(tmp_path):
    s = S.SealedStore(tmp_path / "state")
    a = s.save(7, 1, GOOD, "a" * 40)
    b = s.save(7, 2, GOOD, "a" * 40)
    assert a.canary != b.canary and len(a.canary) == 32 and int(a.canary, 16) >= 0


def test_load_round_trip(tmp_path):
    s = store(tmp_path)
    s.save(7, 1, GOOD, "b" * 40)
    got = s.load(7, 1)
    assert got.patch == GOOD and got.spec_sha == "b" * 40 and got.canary == "f" * 32


def test_load_refuses_on_hash_mismatch(tmp_path):
    s = store(tmp_path)
    s.save(7, 1, GOOD, "b" * 40)
    p = tmp_path / "state" / "sealed" / "issue-7-a1" / "sealed.patch"
    p.write_bytes(GOOD + b"\n")
    with pytest.raises(S.SealedHashMismatch):
        s.load(7, 1)


def test_load_refuses_missing_or_malformed_manifest(tmp_path):
    s = store(tmp_path)
    with pytest.raises(S.SealedError):
        s.load(7, 1)
    s.save(7, 1, GOOD, "b" * 40)
    m = tmp_path / "state" / "sealed" / "issue-7-a1" / "manifest.json"
    m.write_text("{not json")
    with pytest.raises(S.SealedError):
        s.load(7, 1)
    m.write_text(json.dumps({"patch_sha256": 5}))
    with pytest.raises(S.SealedError):
        s.load(7, 1)


def test_save_never_overwrites(tmp_path):
    s = store(tmp_path)
    s.save(7, 1, GOOD, "b" * 40)
    with pytest.raises(S.SealedError):
        s.save(7, 1, GOOD + INIT, "b" * 40)


def test_bundle_is_patch_plus_valid_canary_file(tmp_path):
    s = store(tmp_path)
    sealed = s.save(7, 1, GOOD, "b" * 40)
    b = S.bundle(sealed)
    assert b.startswith(GOOD)
    paths = check(b, allow_canary=True)
    assert "tests/sealed/issue-7/canary_" + "f" * 32 + ".txt" in paths


def test_sealed_prompt_names_the_directory_and_keeps_issue_in_fences():
    p = S.build_sealed_prompt(7, "Title", "Body ``` with fence")
    assert "specs/7.md" in p and "tests/sealed/issue-7/" in p
    assert "UNTRUSTED" in p and "Body" in p
    assert "no implementation" in p.lower()
