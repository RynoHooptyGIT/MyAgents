"""Deterministic runner: intake -> claim -> spec -> build -> gates -> classify -> record.

Phase 2 ("Core"): every category is forced to T2 at integration time, the verify and
sealed-test steps are explicit stubs that force T2, and there is no merge step.
Nothing here pushes, opens a PR, or merges.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional

from . import classifier, ledger as ledger_mod, retry, stops
from .gates import GateResult, GateRunner
from .launcher import Launcher, WorkerResult, build_prompt
from .ledger import Ledger
from .policy import Policy
from .tracker import Issue, NotAllowlisted, StateMismatch, Tracker, select_claimable
from .workspace import DiffStats, Workspace, slug

PHASE = 2
FORCED_LEVEL = "T2"   # phase 2: every category is T2 at integration. Changing it is a code change
                      # under scripts/factory/**, which is itself a protected (always T2) path.
NOT_IMPLEMENTED = "not implemented in phase 2"


@dataclass
class Context:
    root: Path
    policy: Policy
    tracker: Tracker
    launcher: Launcher
    gates: GateRunner
    workspace: Workspace
    ledger: Ledger
    now: Callable[[], datetime] = lambda: datetime.now(timezone.utc)
    out: Callable[[str], None] = print


@dataclass
class RunResult:
    status: str                      # processed | idle | halted | dry-run | skipped
    issue: Optional[int] = None
    outcome: Optional[str] = None
    tier: Optional[str] = None
    reasons: List[str] = field(default_factory=list)
    message: str = ""


PLAN = [
    "claim: queued -> claimed (label)",
    "spec: worker writes specs/<issue>.md (ambiguity check: " + NOT_IMPLEMENTED + ")",
    "build: worker on the routed model, in a dedicated worktree",
    "gates: scripts/factory/gates.sh; on failure retry ladder (same model, then a different model)",
    "verify and sealed tests: stubs, " + NOT_IMPLEMENTED + "; force T2",
    "classify: deterministic tier from the final diff; every category is forced to T2 in phase 2",
    "integrate: label awaiting-human with a summary (no PR, no push, no merge in phase 2)",
    "record: one ledger row",
]


class _Run:
    def __init__(self, ctx: Context, issue: Issue, spent_before: float):
        self.ctx, self.issue, self.spent_before = ctx, issue, spent_before
        self.state = "queued"
        self.cost = 0.0
        self.tokens_in = 0
        self.tokens_out = 0
        self.models: Dict[str, List[str]] = {}
        self.retries = 0
        self.started = ctx.now()
        self.worktree: Optional[Path] = None

    def move(self, new: str) -> None:
        self.ctx.tracker.transition(self.issue.number, self.state, new)
        self.state = new

    def worker(self, role: str, prompt: str, model: Optional[str] = None) -> WorkerResult:
        res = self.ctx.launcher.run(role, prompt, self.worktree, model=model)
        self.cost += res.cost_usd
        self.tokens_in += res.input_tokens
        self.tokens_out += res.output_tokens
        self.models.setdefault(role, []).append(res.model)
        return res

    def budget_block(self) -> Optional[str]:
        return (stops.issue_budget_block(self.cost, self.ctx.policy)
                or stops.day_budget_block(self.spent_before, self.cost, self.ctx.policy))

    def record(self, outcome: str, tier: str, reasons: List[str], category: str, protected: bool) -> None:
        finished = self.ctx.now()
        self.ctx.ledger.append({
            "ts": finished.isoformat(), "issue": self.issue.number, "tier": tier, "reasons": reasons,
            "category": category, "protected": protected, "models": self.models,
            "tokens": {"input": self.tokens_in, "output": self.tokens_out},
            "cost_usd": round(self.cost, 6), "retries": self.retries, "outcome": outcome,
            "started_at": self.started.isoformat(), "finished_at": finished.isoformat()})


def _summary(run: _Run, tier: str, reasons: List[str], gate: str) -> str:
    lines = [f"factory: parked at {tier}, awaiting a person.", f"gates: {gate}",
             f"retries: {run.retries}", f"cost: ${run.cost:.2f}"]
    lines += [f"reason: {r}" for r in reasons]
    return "\n".join(lines)


def _finish(run: _Run, outcome_state: str, reasons: List[str], gate: str, stats: Optional[DiffStats],
            extra_reasons: List[str]) -> RunResult:
    ctx = run.ctx
    reasons = list(extra_reasons)
    protected = False
    category = "none"
    if stats and stats.paths:
        category = classifier.category(stats.paths)
        c = classifier.classify(
            ctx.policy, stats.paths, stats.added, stats.deleted, stats.deleted_files, False,
            "not_run", 0, "retries exhausted" in extra_reasons, "budget exceeded" in extra_reasons,
            FORCED_LEVEL)
        reasons = c.reasons + [r for r in extra_reasons if r not in c.reasons]
        protected = any(r.startswith("protected path") for r in c.reasons)
    else:
        reasons.append("no changes produced")
    reasons.append(f"phase {PHASE}: all categories forced to T2 at integration")
    tier = "T2"
    run.move(outcome_state)
    ctx.tracker.comment(run.issue.number, _summary(run, tier, reasons, gate))
    run.record(outcome_state, tier, reasons, category, protected)
    return RunResult("processed", run.issue.number, outcome_state, tier, reasons)


def _fail(run: _Run, why: str) -> RunResult:
    run.move("failed")
    run.ctx.tracker.comment(run.issue.number, f"factory: failed. {why}")
    run.record("failed", "T2", [why], "none", False)
    return RunResult("processed", run.issue.number, "failed", "T2", [why], why)


def _process(run: _Run) -> RunResult:
    ctx, issue = run.ctx, run.issue
    run.move("claimed")
    run.worktree = ctx.workspace.prepare(issue.number, slug(issue.title))

    block = run.budget_block()
    if block:
        return _finish(run, "awaiting-human", [], "not run", None, ["budget exceeded", block])
    spec = run.worker("spec", build_prompt("spec", issue.number, issue.title, issue.body))
    if not spec.ok:
        return _fail(run, f"spec worker failed: {spec.text[-300:]}")
    ctx.out(f"ambiguity check: {NOT_IMPLEMENTED}")
    run.move("building")

    build_model = ctx.policy.routing["build"]
    history = [retry.attempt_record(0, build_model, "")]
    ladder = retry.Ladder(ctx.policy)
    plan = retry.Plan(0, build_model, "")
    gate = GateResult("MISCONFIGURED", "")
    extra: List[str] = []
    while True:
        block = run.budget_block()
        if block:
            extra += ["budget exceeded", block]
            break
        res = run.worker("build", build_prompt("build", issue.number, issue.title, issue.body, plan.context),
                         model=plan.model)
        gate = (ctx.gates.run(run.worktree) if res.ok
                else GateResult("FAIL", f"build worker exited {res.returncode}\n{res.text}"))
        if gate.verdict == "PASS":
            break
        try:
            nxt = ladder.next_attempt(history, gate.output)
        except retry.IdenticalRetry as e:
            extra += ["retries exhausted", str(e)]
            break
        if nxt is None:
            extra.append("retries exhausted")
            break
        history.append(retry.attempt_record(nxt.round, nxt.model, nxt.context))
        run.retries = nxt.round
        plan = nxt

    ctx.workspace.snapshot(run.worktree)
    stats = ctx.workspace.diff(run.worktree)
    if gate.verdict != "PASS" or extra:
        return _finish(run, "awaiting-human", [], gate.verdict, stats, extra)

    run.move("verifying")
    ctx.out(f"verify: {NOT_IMPLEMENTED}; forcing T2")
    ctx.out(f"sealed tests: {NOT_IMPLEMENTED}; forcing T2")
    return _finish(run, "awaiting-human", [], "PASS", stats,
                   [f"verifier {NOT_IMPLEMENTED}", f"sealed tests {NOT_IMPLEMENTED}"])


def run_once(ctx: Context, dry_run: bool = False) -> RunResult:
    rows = ctx.ledger.rows()
    now = ctx.now()
    block = stops.new_claim_block(ctx.root, ctx.tracker, rows, ctx.policy, now)
    if block:
        ctx.out(f"halted: {block}")
        return RunResult("halted", message=block)
    issue, skipped = select_claimable(ctx.tracker)
    for s in skipped:
        ctx.out(f"skipped #{s.number}: author {s.author!r} is not allowlisted")
    if issue is None:
        ctx.out("idle: no claimable queued issue")
        return RunResult("idle", message="no claimable queued issue")
    if dry_run:
        ctx.out(f"dry-run: would process #{issue.number} (no side effects):")
        for step in PLAN:
            ctx.out(f"  - {step}")
        return RunResult("dry-run", issue.number, message="dry-run")

    run = _Run(ctx, issue, ledger_mod.spent_on(rows, now.astimezone(timezone.utc).date()))
    try:
        result = _process(run)
    except (StateMismatch, NotAllowlisted) as e:
        if run.state == "queued":
            ctx.out(f"skipped #{issue.number}: {e}")
            return RunResult("skipped", issue.number, message=str(e))
        raise
    except BaseException as e:
        _park_failed(run, f"unexpected error: {type(e).__name__}")
        raise
    ctx.out(f"#{issue.number}: {result.outcome} at {result.tier}")
    return result


def _park_failed(run: _Run, why: str) -> None:
    try:
        if run.state not in ("failed", "awaiting-human", "done"):
            run.move("failed")
        run.record("failed", "T2", [why], "none", False)
    except Exception as e:  # best effort while already unwinding another error
        run.ctx.out(f"could not record failure for #{run.issue.number}: {e}")
