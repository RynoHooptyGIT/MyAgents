import os
import subprocess
from pathlib import Path

import pytest

from .. import classifier as c
from .. import policy as pol
from .. import workspace as W

REPO = Path(__file__).resolve().parents[3]


def git(cwd, *args):
    env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t",
               GIT_COMMITTER_EMAIL="t@t")
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True, env=env).stdout


@pytest.fixture
def repo(tmp_path):
    r = tmp_path / "repo"
    r.mkdir()
    git(r, "init", "-q", "-b", "main")
    (r / "a.txt").write_text("a\n")
    git(r, "add", "-A")
    git(r, "commit", "-qm", "init")
    return r


def test_real_numstat_with_binary_file_is_reported_and_t2(repo):
    ws = W.GitWorkspace(repo, base="main")
    wt = ws.prepare(1, "bin", attempt=1)
    (wt / "img.bin").write_bytes(bytes(range(256)) * 4)
    (wt / "ok.py").write_text("x = 1\n")
    ws.snapshot(wt)
    st = ws.diff(wt)
    assert st.binary_files == 1 and "img.bin" in st.paths
    policy = pol.load(REPO)
    r = c.classify(policy, st.paths, st.added, st.deleted, st.deleted_files, False, "agree", 0,
                   False, False, "T1", deleted_paths=st.deleted_paths, binary_files=st.binary_files)
    assert r.tier == "T2" and any("binary" in x for x in r.reasons)


def test_real_diff_reports_deleted_paths(repo):
    ws = W.GitWorkspace(repo, base="main")
    wt = ws.prepare(2, "del", attempt=1)
    (wt / "a.txt").unlink()
    ws.snapshot(wt)
    st = ws.diff(wt)
    assert st.deleted_paths == ["a.txt"] and st.deleted_files == 1


def branches(repo):
    return git(repo, "branch", "--format=%(refname:short)").split()


def test_requeued_issue_gets_fresh_branch_and_old_worktree_removed(repo):
    ws = W.GitWorkspace(repo, base="main")
    wt1 = ws.prepare(5, "thing", attempt=1)
    (wt1 / "new.txt").write_text("work\n")
    ws.snapshot(wt1)
    wt2 = ws.prepare(5, "thing", attempt=2)
    assert wt2.exists() and not (wt2 / "new.txt").exists()
    assert "factory/5-thing" in branches(repo) and "factory/5-thing-a2" in branches(repo)
    assert git(repo, "log", "--oneline", "factory/5-thing").count("\n") == 2   # old commits kept
    assert ws.take_notes() == []      # nothing was force-deleted


def test_dirty_old_worktree_is_force_removed_and_noted(repo):
    ws = W.GitWorkspace(repo, base="main")
    wt1 = ws.prepare(6, "t", attempt=1)
    (wt1 / "uncommitted.txt").write_text("x\n")
    ws.prepare(6, "t", attempt=2)
    notes = ws.take_notes()
    assert len(notes) == 1 and "dirty" in notes[0]
    assert "factory/6-t" in branches(repo)


def test_prepare_never_deletes_branches(repo):
    src = Path(W.__file__).read_text()
    assert "branch\", \"-D" not in src and "-D\"" not in src and "--delete" not in src


def test_attempt_one_uses_plain_branch_name(repo):
    ws = W.GitWorkspace(repo, base="main")
    ws.prepare(7, "x", attempt=1)
    assert "factory/7-x" in branches(repo)


def test_head_sha_and_diff_text_include_diff_and_commit_messages(repo):
    ws = W.GitWorkspace(repo, base="main")
    wt = ws.prepare(9, "txt", attempt=1)
    (wt / "n.py").write_text("SECRET_TOKEN_VALUE = 1\n")
    ws.snapshot(wt)
    sha = ws.head_sha(wt)
    assert len(sha) == 40 and sha == git(wt, "rev-parse", "HEAD").strip()
    text = ws.diff_text(wt)
    assert "SECRET_TOKEN_VALUE" in text and "n.py" in text and "factory: snapshot of worker output" in text


def test_diff_text_includes_binary_content_as_text_and_is_capped(repo):
    ws = W.GitWorkspace(repo, base="main")
    wt = ws.prepare(10, "bin", attempt=1)
    (wt / "b.bin").write_bytes(b"\x00\x01CANARYTOKEN\x00")
    ws.snapshot(wt)
    assert "CANARYTOKEN" in ws.diff_text(wt)
    assert len(ws.diff_text(wt, cap=50)) <= 50


def test_fake_workspace_head_sha_and_diff_text(tmp_path):
    fw = W.FakeWorkspace(tmp_path, W.DiffStats(["a"], 1, 0, 0))
    assert len(fw.head_sha(tmp_path)) == 40 and fw.diff_text(tmp_path) == ""
    fw.diff_text_value = "abc"
    assert fw.diff_text(tmp_path) == "abc"
