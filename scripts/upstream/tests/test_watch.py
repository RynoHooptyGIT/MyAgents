import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from watch import Watcher, report  # noqa: E402

PATH_MAP = [["skills/bmad-", "team/core-skills/bmad-"], ["src/scripts/", "_bmad/scripts/"]]


def sh(cwd, *args):
    return subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def commit(repo, files: dict, msg: str):
    for name, text in files.items():
        p = repo / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    sh(repo, "git", "add", "-A")
    sh(repo, "git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", msg)
    return sh(repo, "git", "rev-parse", "HEAD")


@pytest.fixture
def world(tmp_path):
    up, local = tmp_path / "up", tmp_path / "local"
    for r in (up, local):
        r.mkdir()
        sh(r, "git", "init", "-q", "-b", "main")
    base = commit(up, {"skills/bmad-review/a.py": "x = 1\n", "docs/readme.md": "hi\n"}, "base")
    commit(local, {"team/core-skills/bmad-review/a.py": "x = 1\n", ".baseline": base + "\n"}, "base")
    manifest = {
        "ledger": ".ledger.json",
        "test_cmd": ["true"],
        "max_apply": 10,
        "upstreams": [{
            "name": "u", "remote": "u", "url": str(up), "branch": "main",
            "baseline_file": ".baseline", "path_map": PATH_MAP,
            "structural_pattern": "ticket|sofia",
            "auto_port_pattern": r"^(fix|perf)(\([^)]*\))?:",
        }],
    }
    return up, local, Watcher(local, manifest)


def statuses(rows):
    return {r[3]: r[4] for r in rows}


def test_map_path_first_match_wins():
    assert Watcher.map_path("skills/bmad-x/s.py", PATH_MAP) == "team/core-skills/bmad-x/s.py"
    assert Watcher.map_path("docs/readme.md", PATH_MAP) is None


def test_rewrite_patch_only_touches_headers():
    patch = "diff --git a/s/f b/s/f\n--- a/s/f\n+++ b/s/f\n@@ -1 +1 @@\n-a/s/f\n+b/s/f\n"
    out = Watcher.rewrite_patch(patch, {"s/f": "t/f"})
    assert "diff --git a/t/f b/t/f" in out and "--- a/t/f" in out
    assert "-a/s/f" in out and "+b/s/f" in out


def test_scan_classifies_and_changes_nothing(world):
    up, local, w = world
    commit(up, {"skills/bmad-review/a.py": "x = 2\n"}, "fix: bump")
    commit(up, {"docs/readme.md": "bye\n"}, "docs: readme")
    commit(up, {"skills/bmad-review/t.py": "t = 1\n"}, "feat: ticket store")
    rows = w.run(apply=False, max_apply=10)
    assert statuses(rows) == {
        "fix: bump": "clean", "docs: readme": "not-applicable", "feat: ticket store": "structural",
    }
    assert (local / "team/core-skills/bmad-review/a.py").read_text() == "x = 1\n"
    assert not w.ledger_path.exists()


def test_apply_ports_one_commit_each_and_records_ledger(world):
    up, local, w = world
    commit(up, {"skills/bmad-review/a.py": "x = 2\n"}, "fix: bump")
    w.run(apply=True, max_apply=10)
    assert (local / "team/core-skills/bmad-review/a.py").read_text() == "x = 2\n"
    assert "fix(upstream): port u" in sh(local, "git", "log", "-1", "--format=%s")
    assert w.load_ledger()["u"][sh(up, "git", "rev-parse", "HEAD")]["status"] == "ported"
    # settled commits are not revisited
    assert w.run(apply=True, max_apply=10) == []


def test_already_present_and_conflict(world):
    up, local, w = world
    commit(up, {"skills/bmad-review/p.py": "p = 2\n"}, "fix: already local")
    commit(local, {"team/core-skills/bmad-review/p.py": "p = 2\n"}, "local got it first")
    commit(up, {"skills/bmad-review/a.py": "x = 3\n"}, "fix: diverged")
    commit(local, {"team/core-skills/bmad-review/a.py": "x = 9\n"}, "local differs")
    rows = statuses(w.run(apply=False, max_apply=10))
    assert rows["fix: already local"] == "already-present"
    assert rows["fix: diverged"] == "conflict"


def test_only_fixes_are_auto_ported(world):
    up, local, w = world
    commit(up, {"skills/bmad-review/a.py": "x = 2\n"}, "feat: new layer")
    commit(up, {"skills/bmad-review/b.py": "b = 1\n"}, "fix(review): typo")
    rows = {r[3]: (r[4], r[5]) for r in w.run(apply=True, max_apply=10)}
    assert rows["fix(review): typo"][0] == "ported"
    assert rows["feat: new layer"] == ("clean", "not a fix: review before porting")


def test_max_apply_caps_ports(world):
    up, local, w = world
    commit(up, {"skills/bmad-review/a.py": "x = 2\n"}, "fix: one")
    commit(up, {"skills/bmad-review/b.py": "b = 1\n"}, "fix: two")
    rows = statuses(w.run(apply=True, max_apply=1))
    assert rows == {"fix: one": "ported", "fix: two": "clean"}


def test_failing_tests_roll_the_port_back(world):
    up, local, w = world
    w.m["test_cmd"] = ["false"]
    commit(up, {"skills/bmad-review/a.py": "x = 2\n"}, "fix: bump")
    head = sh(local, "git", "rev-parse", "HEAD")
    rows = statuses(w.run(apply=True, max_apply=10))
    assert rows == {"fix: bump": "test-failed"}
    assert sh(local, "git", "rev-parse", "HEAD") == head
    assert (local / "team/core-skills/bmad-review/a.py").read_text() == "x = 1\n"


def test_report_lists_each_bucket(world):
    up, local, w = world
    commit(up, {"skills/bmad-review/a.py": "x = 2\n"}, "fix: bump")
    commit(up, {"skills/bmad-review/t.py": "t = 1\n"}, "feat: sofia")
    text = report(w.run(apply=True, max_apply=10), True)
    assert "ported in this run | 1" in text and "## Structural" in text and "feat: sofia" in text
