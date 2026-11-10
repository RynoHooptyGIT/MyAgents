"""Scrubbed environment for workers and gates: explicit allowlist, exact names only."""
from __future__ import annotations

import os
from typing import Dict, Iterable, Mapping, Optional


def scrub_env(environ: Optional[Mapping[str, str]], allowlist: Iterable[str]) -> Dict[str, str]:
    environ = os.environ if environ is None else environ
    allowed = set(allowlist)
    return {k: v for k, v in environ.items() if k in allowed}
