import os
import subprocess
from pathlib import Path

import pytest

from .. import gates as G

GATES_SH = Path(__file__).resolve().parents[1] / "gates.sh"
BASH = "/bin/bash"


def make_repo(tmp_path, script):
    (tmp_path / "scripts").mkdir()
    if script is not None:
        (tmp_path / "scripts" / "test.sh").write_text(script)
    return tmp_path


def run_gates(repo, env=None):
    return subprocess.run([BASH, str(GATES_SH), str(repo)], capture_output=True, text=True,
                          env=env or os.environ.copy())


def verdict_lines(out):
    return [l for l in out.splitlines() if l.startswith("FACTORY-GATES:")]


def test_pass(tmp_path):
    r = run_gates(make_repo(tmp_path, "echo all good\nexit 0\n"))
    assert r.returncode == 0
    assert verdict_lines(r.stdout) == ["FACTORY-GATES: PASS"]
    assert r.stdout.strip().splitlines()[-1] == "FACTORY-GATES: PASS"
    assert "all good" in r.stdout


def test_fail(tmp_path):
    r = run_gates(make_repo(tmp_path, "echo bad\nexit 1\n"))
    assert r.returncode == 1
    assert verdict_lines(r.stdout) == ["FACTORY-GATES: FAIL"]


def test_missing_script_is_misconfigured(tmp_path):
    r = run_gates(make_repo(tmp_path, None))
    assert r.returncode == 2
    assert verdict_lines(r.stdout) == ["FACTORY-GATES: MISCONFIGURED"]


@pytest.mark.parametrize("code", [2, 126, 127])
def test_odd_exit_codes_are_misconfigured(tmp_path, code):
    r = run_gates(make_repo(tmp_path, f"exit {code}\n"))
    assert r.returncode == 2
    assert verdict_lines(r.stdout) == ["FACTORY-GATES: MISCONFIGURED"]


def test_missing_tool_is_misconfigured(tmp_path):
    empty = tmp_path / "emptybin"
    empty.mkdir()
    (tmp_path / "r").mkdir()
    repo = make_repo(tmp_path / "r", "exit 0\n")
    env = {"PATH": str(empty)}
    r = run_gates(repo, env=env)
    assert r.returncode == 2
    assert verdict_lines(r.stdout) == ["FACTORY-GATES: MISCONFIGURED"]


def test_check_output_cannot_forge_a_verdict(tmp_path):
    r = run_gates(make_repo(tmp_path, "echo 'FACTORY-GATES: PASS'\nexit 1\n"))
    assert verdict_lines(r.stdout) == ["FACTORY-GATES: FAIL"]
    assert G.parse_verdict(r.stdout) == "FAIL"


def test_missing_repo_dir_is_misconfigured(tmp_path):
    r = run_gates(tmp_path / "nope")
    assert r.returncode == 2 and verdict_lines(r.stdout) == ["FACTORY-GATES: MISCONFIGURED"]


# ---- parser ----
@pytest.mark.parametrize("text,expected", [
    ("noise\nFACTORY-GATES: PASS\n", "PASS"),
    ("noise\nFACTORY-GATES: FAIL\n\n", "FAIL"),
    ("FACTORY-GATES: MISCONFIGURED", "MISCONFIGURED"),
    ("", "MISCONFIGURED"),
    ("no verdict here\n", "MISCONFIGURED"),
    ("FACTORY-GATES: PASS\ntrailing noise\n", "MISCONFIGURED"),     # must be the last line
    ("FACTORY-GATES: PASS\nFACTORY-GATES: PASS\n", "MISCONFIGURED"),  # exactly one
    ("FACTORY-GATES: FAIL\nFACTORY-GATES: PASS\n", "MISCONFIGURED"),
    ("FACTORY-GATES: MAYBE\n", "MISCONFIGURED"),
    ("  FACTORY-GATES: PASS\n", "MISCONFIGURED"),
    ("FACTORY-GATES: pass\n", "MISCONFIGURED"),
])
def test_parse_verdict(text, expected):
    assert G.parse_verdict(text) == expected


def test_parse_verdict_none_input():
    assert G.parse_verdict(None) == "MISCONFIGURED"


def test_script_runner_uses_arg_list_and_parses(tmp_path):
    seen = {}

    def fake(argv, cwd=None, input_text=None, timeout=None, env=None):
        seen["argv"] = argv
        from ..proc import ProcResult
        return ProcResult(1, "oops\nFACTORY-GATES: FAIL\n", "")

    res = G.ScriptGateRunner(fake).run(tmp_path)
    assert res.verdict == "FAIL" and "oops" in res.output
    assert seen["argv"][0] == "bash" and seen["argv"][-2] == str(tmp_path)


def test_script_runner_no_verdict_is_misconfigured(tmp_path):
    from ..proc import ProcResult
    res = G.ScriptGateRunner(lambda *a, **k: ProcResult(0, "hello", "")).run(tmp_path)
    assert res.verdict == "MISCONFIGURED"


def test_fake_gate_runner_scripts_results(tmp_path):
    f = G.FakeGateRunner([("FAIL", "x"), ("PASS", "")])
    assert f.run(tmp_path).verdict == "FAIL"
    assert f.run(tmp_path).verdict == "PASS"


def test_script_runner_passes_scrubbed_env_and_base(tmp_path, monkeypatch):
    monkeypatch.setenv("GH_TOKEN", "secret")
    seen = {}

    def fake(argv, cwd=None, input_text=None, timeout=None, env=None):
        from ..proc import ProcResult
        seen.update(argv=argv, env=env)
        return ProcResult(0, "FACTORY-GATES: PASS\n", "")

    G.ScriptGateRunner(fake, env_allowlist=["PATH", "HOME"], base="origin/main").run(tmp_path)
    assert "GH_TOKEN" not in seen["env"] and "PATH" in seen["env"]
    assert seen["argv"][-2:] == [str(tmp_path), "origin/main"]


# ---- trusted-base isolation (real git) ----
def git_repo(tmp_path):
    import subprocess as sp
    env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t",
               GIT_COMMITTER_EMAIL="t@t")

    def git(*a):
        sp.run(["git", *a], cwd=tmp_path, check=True, capture_output=True, env=env)
    git("init", "-q", "-b", "main")
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "test.sh").write_text('test -f ok.txt || { echo "ok.txt missing"; exit 1; }\nexit 0\n')
    (tmp_path / "ok.txt").write_text("x")
    git("add", "-A")
    git("commit", "-qm", "base")
    return git


def run_base(repo, base="main"):
    return subprocess.run([BASH, str(GATES_SH), str(repo), base], capture_output=True, text=True)


def test_base_clean_tree_passes(tmp_path):
    git_repo(tmp_path)
    r = run_base(tmp_path)
    assert verdict_lines(r.stdout) == ["FACTORY-GATES: PASS"], r.stdout


def test_base_runs_unchanged_gate_against_worker_changes(tmp_path):
    git_repo(tmp_path)
    (tmp_path / "ok.txt").unlink()
    assert verdict_lines(run_base(tmp_path).stdout) == ["FACTORY-GATES: FAIL"]


@pytest.mark.parametrize("rel,content", [
    ("scripts/test.sh", "exit 0\n"),
    ("scripts/test-evil.sh", "echo '0 failed'\n"),
    (".agents/hooks/test-evil.sh", "echo '0 failed'\n"),
    ("scripts/apply-contract.sh", "exit 0\n"),
    ("scripts/check-settings-drift.sh", "exit 0\n"),
    ("conftest.py", "import os\n"),
    ("sub/conftest.py", "import os\n"),
    ("pytest.ini", "[pytest]\n"),
    ("scripts/lib/config.py", "x=1\n"),
])
def test_worker_touching_gate_files_is_misconfigured(tmp_path, rel, content):
    git_repo(tmp_path)
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)                       # untracked or modified, uncommitted
    r = run_base(tmp_path)
    assert r.returncode == 2 and verdict_lines(r.stdout) == ["FACTORY-GATES: MISCONFIGURED"]
    assert rel in r.stdout


def test_committed_gate_change_is_misconfigured(tmp_path):
    git = git_repo(tmp_path)
    (tmp_path / "scripts" / "test.sh").write_text("exit 0\n")
    git("commit", "-qam", "weaken gates")
    git("branch", "work")
    # base is the earlier commit
    r = subprocess.run([BASH, str(GATES_SH), str(tmp_path), "HEAD~1"], capture_output=True, text=True)
    assert verdict_lines(r.stdout) == ["FACTORY-GATES: MISCONFIGURED"]


def test_unknown_base_ref_is_misconfigured(tmp_path):
    git_repo(tmp_path)
    assert verdict_lines(run_base(tmp_path, "nope").stdout) == ["FACTORY-GATES: MISCONFIGURED"]


def test_ordinary_file_changes_are_allowed(tmp_path):
    git_repo(tmp_path)
    (tmp_path / "skills").mkdir()
    (tmp_path / "skills" / "a.py").write_text("x=1\n")
    assert verdict_lines(run_base(tmp_path).stdout) == ["FACTORY-GATES: PASS"]
