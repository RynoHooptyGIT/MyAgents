from pathlib import Path

import pytest

from .. import workspace as W
from ..proc import ProcResult


class Rec:
    def __init__(self, responses=()):
        self.calls = []
        self.responses = list(responses)

    def __call__(self, argv, cwd=None, input_text=None, timeout=None):
        self.calls.append(dict(argv=list(argv), cwd=cwd))
        return self.responses.pop(0) if self.responses else ProcResult(0, "", "")


@pytest.mark.parametrize("title,expected", [
    ("Fix the Thing!", "fix-the-thing"),
    ('x"; rm -rf ~ #$(id)', "x-rm-rf-id"),
    ("---", "issue"),
    ("", "issue"),
    ("a" * 200, "a" * 40),
    ("ÜñÏçödé", "d"),
])
def test_slug(title, expected):
    assert W.slug(title) == expected


def test_prepare_uses_arg_list_and_branch_name(tmp_path):
    r = Rec()
    ws = W.GitWorkspace(tmp_path, runner=r)
    path = ws.prepare(7, "$(evil) title")
    assert path == tmp_path / ".worktrees" / "factory-7"
    argv = r.calls[0]["argv"]
    assert argv[:2] == ["git", "worktree"] and "factory/7-evil-title" in argv and "origin/main" in argv
    assert not any("$(" in a for a in argv)


def test_prepare_failure_raises(tmp_path):
    ws = W.GitWorkspace(tmp_path, runner=Rec([ProcResult(128, "", "fatal")]))
    with pytest.raises(W.WorkspaceError, match="fatal"):
        ws.prepare(1, "t")


def test_diff_stats_parses_numstat_and_deleted(tmp_path):
    numstat = "10\t2\tskills/a.py\0-\t-\timg.png\0"
    deleted = "old.py\0gone.py\0"
    r = Rec([ProcResult(0, numstat, ""), ProcResult(0, deleted, "")])
    st = W.GitWorkspace(tmp_path, runner=r, binary_lines=300).diff(tmp_path / "wt")
    assert st.paths == ["skills/a.py", "img.png"]
    assert st.added == 310 and st.deleted == 2     # binary counted at the cap
    assert st.deleted_files == 2
    assert "--no-renames" in r.calls[0]["argv"] and "-z" in r.calls[0]["argv"]
    assert r.calls[0]["cwd"] == tmp_path / "wt"


def test_diff_with_weird_filename_is_data(tmp_path):
    numstat = "1\t0\ta b\"; rm -rf ~.py\0"
    st = W.GitWorkspace(tmp_path, runner=Rec([ProcResult(0, numstat, ""), ProcResult(0, "", "")])).diff(tmp_path)
    assert st.paths == ['a b"; rm -rf ~.py']


def test_snapshot_commits_only_when_dirty(tmp_path):
    r = Rec([ProcResult(0, " M x\n", ""), ProcResult(0, "", ""), ProcResult(0, "", "")])
    W.GitWorkspace(tmp_path, runner=r).snapshot(tmp_path / "wt")
    verbs = [c["argv"][1] for c in r.calls]
    assert verbs == ["status", "add", "commit"]
    r2 = Rec([ProcResult(0, "", "")])
    W.GitWorkspace(tmp_path, runner=r2).snapshot(tmp_path / "wt")
    assert [c["argv"][1] for c in r2.calls] == ["status"]


def test_diff_failure_raises(tmp_path):
    with pytest.raises(W.WorkspaceError):
        W.GitWorkspace(tmp_path, runner=Rec([ProcResult(1, "", "bad")])).diff(tmp_path)


def test_fake_workspace(tmp_path):
    f = W.FakeWorkspace(tmp_path, W.DiffStats(["a"], 1, 0, 0))
    assert f.prepare(1, "t").exists() and f.diff(tmp_path).paths == ["a"]
