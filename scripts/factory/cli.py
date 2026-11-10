"""CLI: `python3 -m scripts.factory run --once [--dry-run]` and `status`."""
from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import timezone
from pathlib import Path
from typing import Callable, Optional

from . import ledger as ledger_mod, runner, stops
from .gates import ScriptGateRunner
from .launcher import ClaudeLauncher
from .ledger import Ledger, LedgerError
from .policy import PolicyError, load as load_policy
from .tracker import GhTracker, TrackerError
from .workspace import GitWorkspace, WorkspaceError

EXIT_OK, EXIT_ERROR, EXIT_HALTED = 0, 2, 3


def resolve_root(arg: Optional[str]) -> Path:
    if arg:
        return Path(arg).resolve()
    try:
        out = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True)
        return Path(out.stdout.strip())
    except (OSError, subprocess.CalledProcessError):
        return Path.cwd()


def build_real_context(root, repo: Optional[str]) -> runner.Context:
    root = Path(root)
    policy = load_policy(root)
    return runner.Context(
        root=root, policy=policy,
        tracker=GhTracker(allowed_authors=policy.allowlisted_authors, repo=repo),
        launcher=ClaudeLauncher(policy), gates=ScriptGateRunner(),
        workspace=GitWorkspace(root),
        ledger=Ledger(root / ".factory" / "ledger.jsonl"))


def _status(ctx: runner.Context) -> int:
    rows = ctx.ledger.rows()
    now = ctx.now().astimezone(timezone.utc)
    s = ledger_mod.summarize(rows)
    ctx.out(f"queued: {len(ctx.tracker.list_queued())}")
    ctx.out(f"awaiting-human: {ctx.tracker.count_state('awaiting-human')} (max {ctx.policy.max_awaiting_human})")
    ctx.out(f"halt label: {'yes' if ctx.tracker.halt_label_present() else 'no'}")
    ctx.out(f"STOP file: {'present' if stops.stop_file(ctx.root).exists() else 'absent'}")
    ctx.out(f"spent today: ${ledger_mod.spent_on(rows, now.date()):.2f} of ${ctx.policy.per_day_usd:.2f}")
    ctx.out(f"ledger rows: {s['total']}  cost: ${s['cost_usd']:.2f}")
    ctx.out(f"by outcome: {s['by_outcome']}  by tier: {s['by_tier']}")
    ctx.out(f"phase {runner.PHASE}: every category forced to T2, nothing auto-merges")
    return EXIT_OK


def main(argv=None, build: Optional[Callable] = None) -> int:
    ap = argparse.ArgumentParser(prog="factory", description="Software factory runner (phase 2).")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="process at most one queued issue")
    r.add_argument("--once", action="store_true", required=True, help="process at most one issue (required)")
    r.add_argument("--dry-run", action="store_true", help="print the plan; no side effects")
    s = sub.add_parser("status", help="print queue and ledger summary")
    for p in (r, s):
        p.add_argument("--root")
        p.add_argument("--repo", help="owner/name passed to gh")
    a = ap.parse_args(argv)
    root = resolve_root(a.root)
    try:
        ctx = build(root, a) if build else build_real_context(root, a.repo)
        if a.cmd == "status":
            return _status(ctx)
        res = runner.run_once(ctx, dry_run=a.dry_run)
    except (PolicyError, LedgerError, TrackerError, WorkspaceError) as e:
        print(f"factory: error: {e}", file=sys.stderr)
        return EXIT_ERROR
    return EXIT_HALTED if res.status == "halted" else EXIT_OK
