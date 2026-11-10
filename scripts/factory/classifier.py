"""Deterministic risk-tier classifier. Pure: no I/O, no model calls."""
from __future__ import annotations

import posixpath
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import List, Optional, Sequence

from .policy import Policy

TIER_ORDER = {"T0": 0, "T1": 1, "T2": 2}
VERDICTS = ("agree", "disagree", "not_run", None)


@dataclass(frozen=True)
class Classification:
    tier: str
    reasons: List[str]


@lru_cache(maxsize=512)
def _compile(pattern: str):
    out, i = [], 0
    while i < len(pattern):
        ch = pattern[i]
        if pattern.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif pattern.startswith("/**", i) and i + 3 == len(pattern):
            out.append("/.+")
            i += 3
        elif pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif ch == "*":
            out.append("[^/]*")
            i += 1
        elif ch == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(ch))
            i += 1
    return re.compile("^" + "".join(out) + "$", re.IGNORECASE | re.DOTALL)


def glob_match(pattern: str, path: str) -> bool:
    """Anchored, case-insensitive glob. `*` and `?` stay inside one path segment;
    `**` crosses segments; a trailing `/**` needs at least one more segment."""
    return _compile(pattern).match(path) is not None


def normalize_path(raw: str) -> Optional[str]:
    """Repo-relative posix path, or None if empty, absolute or escaping the root."""
    if not isinstance(raw, str) or not raw.strip():
        return None
    p = raw.replace("\\", "/")
    if p.startswith("/"):
        return None
    p = posixpath.normpath(p)
    if p in (".", "") or p == ".." or p.startswith("../"):
        return None
    return p


def category(paths: Sequence[str]) -> str:
    """Path category for earned autonomy: shared top-level dir, 'root', or 'mixed'."""
    tops = set()
    for raw in paths:
        n = normalize_path(raw)
        if n is None:
            return "mixed"
        tops.add(n.split("/", 1)[0] if "/" in n else "root")
    return tops.pop() if len(tops) == 1 else "mixed"


def _nonneg_int(v, name):
    if isinstance(v, bool) or not isinstance(v, int) or v < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return v


def classify(policy: Policy, paths: Sequence[str], added: int, deleted: int,
             deleted_files: int, new_dependency: bool, verifier_verdict: Optional[str],
             sealed_failures: int, retries_exhausted: bool, budget_exceeded: bool,
             category_level: str) -> Classification:
    if not paths:
        raise ValueError("nothing to classify: no changed paths")
    _nonneg_int(added, "added")
    _nonneg_int(deleted, "deleted")
    _nonneg_int(deleted_files, "deleted_files")
    _nonneg_int(sealed_failures, "sealed_failures")
    if verifier_verdict not in VERDICTS:
        raise ValueError(f"unknown verifier verdict {verifier_verdict!r}")
    if category_level not in ("T1", "T2"):
        raise ValueError(f"unknown category level {category_level!r}")

    reasons: List[str] = []
    norm: List[str] = []
    for raw in paths:
        n = normalize_path(raw)
        if n is None:
            reasons.append(f"unsafe path treated as protected: {raw!r}")
        else:
            norm.append(n)
            for pat in policy.protected_paths:
                if glob_match(pat, n):
                    reasons.append(f"protected path: {n}")
                    break
    dep_paths = [n for n in norm if any(glob_match(p, n) for p in policy.dependency_files)]
    if new_dependency or dep_paths:
        reasons.append("new dependency")
    if added + deleted > policy.max_diff_lines:
        reasons.append(f"diff over size cap ({added + deleted} > {policy.max_diff_lines} lines)")
    if deleted_files > policy.max_deleted_files:
        reasons.append(f"deleted files over cap ({deleted_files} > {policy.max_deleted_files})")
    if verifier_verdict == "disagree":
        reasons.append("verifier disagreement")
    if sealed_failures > 0:
        reasons.append(f"sealed-test failures: {sealed_failures}")
    if retries_exhausted:
        reasons.append("retries exhausted")
    if budget_exceeded:
        reasons.append("budget exceeded")
    if category_level == "T2":
        reasons.append("category earned level is T2")

    if reasons:
        return Classification("T2", reasons)
    all_t0 = len(norm) == len(paths) and all(
        any(glob_match(p, n) for p in policy.t0_paths) for n in norm)
    if all_t0:
        return Classification("T0", [])
    if verifier_verdict != "agree":
        return Classification("T2", ["verifier has not agreed"])
    return Classification("T1", [])
