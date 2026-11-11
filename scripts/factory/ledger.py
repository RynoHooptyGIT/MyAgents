"""Append-only ledger (.factory/ledger.jsonl) and the earned-autonomy reader.

The ledger is runtime state and is gitignored (see .factory/.gitignore): it is
appended on whichever machine runs the factory, so committing it would cause
merge conflicts and put cost data in a public repo.
One row per issue run (not per worker attempt); `retries` counts the attempts.
"""
from __future__ import annotations

import json
import os
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List

from .policy import SANDBOX_MODES, Policy

OUTCOMES = ("merged", "awaiting-human", "failed", "reverted", "refused")
TIERS = ("T0", "T1", "T2")
REQUIRED = ("ts", "issue", "tier", "reasons", "category", "protected", "models", "tokens",
            "cost_usd", "retries", "outcome", "started_at", "finished_at")


class LedgerError(ValueError):
    pass


def _ts(v, name):
    try:
        d = datetime.fromisoformat(str(v))
    except ValueError:
        raise LedgerError(f"{name} is not an ISO timestamp: {v!r}") from None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def _int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def validate(r) -> None:
    if not isinstance(r, dict):
        raise LedgerError("row must be an object")
    for k in REQUIRED:
        if k not in r:
            raise LedgerError(f"row missing {k!r}")
    if not _int(r["issue"]) or r["issue"] < 0:
        raise LedgerError("issue must be a non-negative int")
    if r["tier"] not in TIERS:
        raise LedgerError(f"bad tier {r['tier']!r}")
    if r["outcome"] not in OUTCOMES:
        raise LedgerError(f"bad outcome {r['outcome']!r}")
    if not isinstance(r["reasons"], list) or not all(isinstance(x, str) for x in r["reasons"]):
        raise LedgerError("reasons must be a list of strings")
    if not isinstance(r["category"], str) or not r["category"]:
        raise LedgerError("category must be a non-empty string")
    if not isinstance(r["protected"], bool):
        raise LedgerError("protected must be a bool")
    if not isinstance(r["models"], dict):
        raise LedgerError("models must be an object")
    t = r["tokens"]
    if not isinstance(t, dict) or not _int(t.get("input")) or not _int(t.get("output")):
        raise LedgerError("tokens must have int input and output")
    if isinstance(r["cost_usd"], bool) or not isinstance(r["cost_usd"], (int, float)) or r["cost_usd"] < 0:
        raise LedgerError("cost_usd must be a non-negative number")
    if not _int(r["retries"]) or r["retries"] < 0:
        raise LedgerError("retries must be a non-negative int")
    if "cost_known" in r and not isinstance(r["cost_known"], bool):
        raise LedgerError("cost_known must be a bool")
    if "sandbox" in r and (not isinstance(r["sandbox"], str) or r["sandbox"] not in SANDBOX_MODES):
        raise LedgerError(f"bad sandbox {r['sandbox']!r}")
    if "notes" in r and (not isinstance(r["notes"], list) or not all(isinstance(x, str) for x in r["notes"])):
        raise LedgerError("notes must be a list of strings")
    for k in ("ts", "started_at", "finished_at"):
        _ts(r[k], k)


class Ledger:
    def __init__(self, path):
        self.path = Path(path)

    def append(self, row: dict) -> None:
        validate(row)
        line = json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(str(self.path), os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
        try:
            os.write(fd, line.encode("utf-8"))
            os.fsync(fd)
        finally:
            os.close(fd)

    def rows(self) -> List[dict]:
        if not self.path.is_file():
            return []
        out = []
        for n, line in enumerate(self.path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                r = json.loads(line)
                validate(r)
            except (ValueError, LedgerError) as e:
                raise LedgerError(f"{self.path} line {n}: {e}") from e
            out.append(r)
        return out


def spent_on(rows: List[dict], day: date) -> float:
    return round(sum(r["cost_usd"] for r in rows if _ts(r["ts"], "ts").astimezone(timezone.utc).date() == day), 6)


def summarize(rows: List[dict]) -> dict:
    return {"total": len(rows),
            "by_outcome": dict(Counter(r["outcome"] for r in rows)),
            "by_tier": dict(Counter(r["tier"] for r in rows)),
            "cost_usd": round(sum(r["cost_usd"] for r in rows), 6)}


def earned_level(rows: List[dict], category: str, policy: Policy, now: datetime) -> str:
    """T2 until `promotion_count` consecutive clean merges in the category, then T1.
    A merge counts only once it is older than `revert_window_days` with no revert.
    T0 (docs/test-only) and protected merges never count toward promoting a category.
    A revert demotes one tier (T1 -> T2), drops pending merges and resets the count."""
    window = timedelta(days=policy.revert_window_days)
    level, streak, pending = "T2", 0, []

    def settle(upto):
        nonlocal level, streak, pending
        keep = []
        for ts in pending:
            if ts + window <= upto:
                streak += 1
                if streak >= policy.promotion_count:
                    level = "T1"
            else:
                keep.append(ts)
        pending = keep

    for r in sorted((r for r in rows if r["category"] == category), key=lambda r: _ts(r["ts"], "ts")):
        ts = _ts(r["ts"], "ts")
        settle(ts)
        if r["outcome"] == "merged" and not r["protected"] and r["tier"] != "T0":
            pending.append(ts)
        elif r["outcome"] == "reverted":
            level, streak, pending = "T2", 0, []
    settle(now if now.tzinfo else now.replace(tzinfo=timezone.utc))
    return level
