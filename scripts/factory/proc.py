"""Subprocess seam. Always argument lists, never a shell string."""
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import Optional, Sequence


@dataclass(frozen=True)
class ProcResult:
    returncode: int
    stdout: str
    stderr: str


def run(argv: Sequence[str], cwd=None, input_text: Optional[str] = None,
        timeout: Optional[float] = None, env: Optional[dict] = None) -> ProcResult:
    if isinstance(argv, (str, bytes)) or not all(isinstance(a, str) for a in argv):
        raise TypeError("argv must be a list of strings")
    try:
        p = subprocess.run(list(argv), cwd=cwd, input=input_text, capture_output=True,
                           text=True, timeout=timeout, shell=False, env=env)
    except FileNotFoundError as e:
        return ProcResult(127, "", f"command not found: {argv[0]}: {e}")
    except subprocess.TimeoutExpired as e:
        return ProcResult(124, "", f"timed out after {timeout}s: {argv[0]}")
    return ProcResult(p.returncode, p.stdout or "", p.stderr or "")
