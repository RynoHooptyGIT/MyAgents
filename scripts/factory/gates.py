"""Gate verdict parsing and the gate-runner seam."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional, Tuple

from .proc import ProcResult, run as default_run

GATES_SH = Path(__file__).resolve().parent / "gates.sh"
_LINE = re.compile(r"^FACTORY-GATES: (PASS|FAIL|MISCONFIGURED)$")


def parse_verdict(text: Optional[str]) -> str:
    """The verdict must be the single final non-empty line; anything else is MISCONFIGURED."""
    if not text:
        return "MISCONFIGURED"
    lines = [l.rstrip("\r") for l in text.splitlines() if l.strip()]
    if not lines:
        return "MISCONFIGURED"
    verdicts = [l for l in lines if l.startswith("FACTORY-GATES:")]
    m = _LINE.match(lines[-1])
    if len(verdicts) != 1 or not m:
        return "MISCONFIGURED"
    return m.group(1)


@dataclass(frozen=True)
class GateResult:
    verdict: str
    output: str


class GateRunner:
    def run(self, worktree: Path) -> GateResult:
        raise NotImplementedError


class ScriptGateRunner(GateRunner):
    """Runs the factory's own gates.sh (from the trusted checkout) against a worktree."""

    def __init__(self, runner: Callable[..., ProcResult] = default_run, script: Path = GATES_SH):
        self._run = runner
        self._script = script

    def run(self, worktree):
        r = self._run(["bash", str(self._script), str(worktree)], timeout=3600)
        out = r.stdout + (("\n" + r.stderr) if r.stderr else "")
        return GateResult(parse_verdict(r.stdout), out)


class FakeGateRunner(GateRunner):
    def __init__(self, results: List[Tuple[str, str]]):
        self.results = list(results)
        self.calls = 0

    def run(self, worktree):
        self.calls += 1
        v, o = self.results.pop(0) if self.results else ("PASS", "")
        return GateResult(v, o)
