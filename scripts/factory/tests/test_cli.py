import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from .. import cli
from .. import gates as G
from .. import launcher as Lc
from .. import ledger as Ld
from .. import policy as pol
from .. import runner as R
from .. import tracker as T
from .. import workspace as W

REPO = Path(__file__).resolve().parents[3]


def setup(tmp_path, with_policy=True):
    (tmp_path / ".factory").mkdir()
    if with_policy:
        shutil.copy(REPO / ".factory" / "policy.yaml", tmp_path / ".factory" / "policy.yaml")
    policy = pol.load(tmp_path) if with_policy else None
    tr = T.FakeTracker(["RynoHooptyGIT"])
    tr.add_issue(1, "t", "b", "RynoHooptyGIT", ["factory:queued"], "2026-11-01")
    out = []

    def build(root, args):
        return R.Context(root=Path(root), policy=pol.load(root), tracker=tr, launcher=Lc.FakeLauncher(),
                         gates=G.FakeGateRunner([("PASS", "")]),
                         workspace=W.FakeWorkspace(tmp_path, W.DiffStats(["docs/a.md"], 1, 0, 0)),
                         ledger=Ld.Ledger(Path(root) / "state" / "ledger.jsonl"), state_dir=Path(root) / "state",
                         out=out.append)
    return tr, build, out


def test_run_once_dry_run(tmp_path, capsys):
    tr, build, out = setup(tmp_path)
    code = cli.main(["run", "--once", "--dry-run", "--root", str(tmp_path)], build=build)
    assert code == 0 and tr.transitions == []
    assert any("dry-run" in l for l in out)


def test_run_once_processes(tmp_path):
    tr, build, out = setup(tmp_path)
    assert cli.main(["run", "--once", "--root", str(tmp_path)], build=build) == 0
    assert tr.labels(1) == {"factory:awaiting-human"}


def test_halt_exit_code_is_3(tmp_path):
    tr, build, out = setup(tmp_path)
    (tmp_path / ".factory" / "STOP").write_text("")
    assert cli.main(["run", "--once", "--root", str(tmp_path)], build=build) == 3


def test_missing_policy_exits_2_with_message(tmp_path, capsys):
    (tmp_path / ".factory").mkdir()
    code = cli.main(["run", "--once", "--root", str(tmp_path)])
    assert code == 2
    assert "policy" in capsys.readouterr().err


def test_run_requires_once(tmp_path):
    with pytest.raises(SystemExit) as e:
        cli.main(["run", "--root", str(tmp_path)])
    assert e.value.code == 2


def test_status_prints_queue_and_ledger(tmp_path):
    tr, build, out = setup(tmp_path)
    cli.main(["run", "--once", "--root", str(tmp_path)], build=build)
    out.clear()
    assert cli.main(["status", "--root", str(tmp_path)], build=build) == 0
    text = "\n".join(out)
    assert "queued: 0" in text and "awaiting-human: 1" in text
    assert "ledger rows: 1" in text and "STOP" in text


def test_module_entry_point_runs(tmp_path):
    r = subprocess.run([sys.executable, "-m", "scripts.factory", "run", "--root", str(tmp_path)],
                       capture_output=True, text=True, cwd=REPO)
    assert r.returncode == 2 and "--once" in r.stderr


def test_real_wiring_builds_gh_and_claude_without_executing(tmp_path):
    (tmp_path / ".factory").mkdir()
    shutil.copy(REPO / ".factory" / "policy.yaml", tmp_path / ".factory" / "policy.yaml")
    ctx = cli.build_real_context(tmp_path, repo=None)
    assert isinstance(ctx.tracker, T.GhTracker) and isinstance(ctx.launcher, Lc.ClaudeLauncher)


def test_status_reports_ambiguous_issues(tmp_path):
    tr, build, out = setup(tmp_path)
    tr.add_issue(2, "t", "b", "RynoHooptyGIT", ["factory:queued", "factory:done"], "2026-11-02")
    cli.main(["status", "--root", str(tmp_path)], build=build)
    assert any("ambiguous" in l and "2" in l for l in out)


def test_state_dir_inside_repo_is_rejected(tmp_path, capsys):
    (tmp_path / ".factory").mkdir()
    text = (REPO / ".factory" / "policy.yaml").read_text().replace(
        'state_dir: "~/.local/state/myagents-factory"', 'state_dir: ".factory/state"')
    (tmp_path / ".factory" / "policy.yaml").write_text(text)
    assert cli.main(["status", "--root", str(tmp_path)]) == 2
    assert "state_dir" in capsys.readouterr().err


def test_real_wiring_puts_ledger_outside_repo(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    (tmp_path / "repo" / ".factory").mkdir(parents=True)
    shutil.copy(REPO / ".factory" / "policy.yaml", tmp_path / "repo" / ".factory" / "policy.yaml")
    ctx = cli.build_real_context(tmp_path / "repo", repo=None)
    assert str(ctx.ledger.path).startswith(str(tmp_path / "home"))
    assert not str(ctx.state_dir).startswith(str(tmp_path / "repo"))
