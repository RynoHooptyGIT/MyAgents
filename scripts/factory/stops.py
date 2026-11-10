"""Hard stops: kill switch, halt label, budgets, awaiting-human cap."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from . import ledger as _ledger
from .policy import Policy
from .tracker import Tracker


def stop_file(root) -> Path:
    return Path(root) / ".factory" / "STOP"


def issue_budget_block(issue_spend: float, policy: Policy) -> Optional[str]:
    if issue_spend >= policy.per_issue_usd:
        return f"per-issue budget reached (${issue_spend:.2f} >= ${policy.per_issue_usd:.2f})"
    return None


def day_budget_block(spent_before_run: float, run_spend: float, policy: Policy) -> Optional[str]:
    total = spent_before_run + run_spend
    if total >= policy.per_day_usd:
        return f"daily budget reached (${total:.2f} >= ${policy.per_day_usd:.2f})"
    return None


def new_claim_block(root, tracker: Tracker, ledger_rows: List[dict], policy: Policy,
                    now: datetime) -> Optional[str]:
    """Reason new work must not be claimed, or None. Any existing STOP path blocks."""
    if stop_file(root).exists() or stop_file(root).is_symlink():
        return "kill switch: .factory/STOP is present"
    if tracker.halt_label_present():
        return "kill switch: an open issue carries the factory:halt label"
    spent = _ledger.spent_on(ledger_rows, now.astimezone(timezone.utc).date())
    reason = day_budget_block(spent, 0.0, policy)
    if reason:
        return reason
    waiting = tracker.count_state("awaiting-human")
    if waiting >= policy.max_awaiting_human:
        return f"queue cap: {waiting} issues awaiting-human (max {policy.max_awaiting_human})"
    return None
