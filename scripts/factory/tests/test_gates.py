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

    def fake(argv, cwd=None, input_text=None, timeout=None):
        seen["argv"] = argv
        from ..proc import ProcResult
        return ProcResult(1, "oops\nFACTORY-GATES: FAIL\n", "")

    res = G.ScriptGateRunner(fake).run(tmp_path)
    assert res.verdict == "FAIL" and "oops" in res.output
    assert seen["argv"][0] == "bash" and seen["argv"][-1] == str(tmp_path)


def test_script_runner_no_verdict_is_misconfigured(tmp_path):
    from ..proc import ProcResult
    res = G.ScriptGateRunner(lambda *a, **k: ProcResult(0, "hello", "")).run(tmp_path)
    assert res.verdict == "MISCONFIGURED"


def test_fake_gate_runner_scripts_results(tmp_path):
    f = G.FakeGateRunner([("FAIL", "x"), ("PASS", "")])
    assert f.run(tmp_path).verdict == "FAIL"
    assert f.run(tmp_path).verdict == "PASS"
