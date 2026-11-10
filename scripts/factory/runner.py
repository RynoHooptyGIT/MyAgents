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
    state_dir: Path
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


REASON_CODES = [
    ("protected path", "protected-path"), ("unsafe path", "unsafe-path"), ("new dependency", "new-dependency"),
    ("diff over size", "size-cap"), ("deleted files over", "deleted-files-cap"),
    ("deleted test file", "deleted-test-file"), ("binary file", "binary-file"),
    ("verifier disagreement", "verifier-disagreement"), ("sealed-test", "sealed-failure"),
    ("retries exhausted", "retries-exhausted"), ("retry identical", "identical-retry"),
    ("budget exceeded", "budget-exceeded"), ("daily budget", "budget-exceeded"),
    ("per-issue budget", "budget-exceeded"), ("category earned", "category-level"),
    ("verifier not implemented", "verifier-stub"), ("sealed tests not implemented", "sealed-stub"),
    ("verifier has not agreed", "verifier-not-agreed"), ("phase", "phase-2-forced"),
    ("no changes", "no-changes"), ("spec worker failed", "spec-failed"),
    ("unexpected error", "crash"),
]


def reason_code(reason: str) -> str:
    for prefix, code in REASON_CODES:
        if reason.startswith(prefix):
            return code
    return "other"


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
    def __init__(self, ctx: Context, issue: Issue, spent_before: float, attempt: int):
        self.ctx, self.issue, self.spent_before, self.attempt = ctx, issue, spent_before, attempt
        self.state = "queued"
        self.cost = 0.0
        self.cost_known = True
        self.cost_recorded = 0.0
        self.tokens_in = 0
        self.tokens_out = 0
        self.models: Dict[str, List[str]] = {}
        self.retries = 0
        self.started = ctx.now()
        self.worktree: Optional[Path] = None

    def log(self, text: str) -> None:
        """Detail (worker output, gate output) stays in a local file, never on the issue."""
        try:
            d = self.ctx.state_dir / "logs"
            d.mkdir(parents=True, exist_ok=True)
            with open(d / f"issue-{self.issue.number}.log", "a", encoding="utf-8") as f:
                f.write(f"--- {self.ctx.now().isoformat()} attempt {self.attempt}\n{text}\n")
        except OSError as e:
            self.ctx.out(f"could not write log: {e}")

    def move(self, new: str) -> None:
        self.ctx.tracker.transition(self.issue.number, self.state, new)
        self.state = new

    def remaining_budget(self) -> float:
        p = self.ctx.policy
        return max(min(p.per_issue_usd - self.cost, p.per_day_usd - self.spent_before - self.cost), 0.0)

    def worker(self, role: str, prompt: str, model: Optional[str] = None) -> WorkerResult:
        res = self.ctx.launcher.run(role, prompt, self.worktree, model=model,
                                    max_budget_usd=self.remaining_budget())
        cost = res.cost_usd
        if not res.cost_known:
            # Unknown spend (timeout, unparseable output): charge what is left of the issue budget.
            cost = max(cost, self.ctx.policy.per_issue_usd - self.cost)
            self.cost_known = False
        self.cost += cost
        self.tokens_in += res.input_tokens
        self.tokens_out += res.output_tokens
        self.models.setdefault(role, []).append(res.model)
        return res

    def budget_block(self) -> Optional[str]:
        return (stops.issue_budget_block(self.cost, self.ctx.policy)
                or stops.day_budget_block(self.spent_before, self.cost, self.ctx.policy))

    def record(self, outcome: str, tier: str, reasons: List[str], category: str, protected: bool) -> None:
        finished = self.ctx.now()
        row = {
            "ts": finished.isoformat(), "issue": self.issue.number, "tier": tier, "reasons": reasons,
            "category": category, "protected": protected, "models": self.models,
            "tokens": {"input": self.tokens_in, "output": self.tokens_out},
            # spend already written by an earlier row is not counted twice
            "cost_usd": round(self.cost - self.cost_recorded, 6), "cost_known": self.cost_known,
            "retries": self.retries, "outcome": outcome,
            "started_at": self.started.isoformat(), "finished_at": finished.isoformat()}
        notes = self.ctx.workspace.take_notes()
        if notes:
            row["notes"] = notes
        self.ctx.ledger.append(row)
        self.cost_recorded = self.cost
        self.tokens_in = self.tokens_out = 0


def _summary(tier: str, state: str, reasons: List[str]) -> str:
    codes = []
    for r in reasons:
        c = reason_code(r)
        if c not in codes:
            codes.append(c)
    return (f"factory: parked at {tier} ({state}). Reason codes: {', '.join(codes) or 'none'}. "
            "Details are in the operator's local factory log.")


def _finish(run: _Run, outcome_state: str, gate: str, stats: Optional[DiffStats],
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
            FORCED_LEVEL, deleted_paths=stats.deleted_paths, binary_files=stats.binary_files)
        reasons = c.reasons + [r for r in extra_reasons if r not in c.reasons]
        protected = any(r.startswith("protected path") for r in c.reasons)
    else:
        reasons.append("no changes produced")
    reasons.append(f"phase {PHASE}: all categories forced to T2 at integration")
    run.log(f"gate verdict {gate}; reasons: {reasons}")
    run.record(outcome_state, "T2", reasons, category, protected)   # ledger first
    run.move(outcome_state)
    ctx.tracker.comment(run.issue.number, _summary("T2", outcome_state, reasons))
    return RunResult("processed", run.issue.number, outcome_state, "T2", reasons)


def _fail(run: _Run, why: str, detail: str) -> RunResult:
    run.log(f"{why}: {detail}")
    run.record("failed", "T2", [why], "none", False)
    run.move("failed")
    run.ctx.tracker.comment(run.issue.number, _summary("T2", "failed", [why]))
    return RunResult("processed", run.issue.number, "failed", "T2", [why], why)


def _process(run: _Run) -> RunResult:
    ctx, issue = run.ctx, run.issue
    run.move("claimed")
    run.worktree = ctx.workspace.prepare(issue.number, slug(issue.title), run.attempt)

    block = run.budget_block()
    if block:
        return _finish(run, "awaiting-human", "not run", None, ["budget exceeded", block])
    spec = run.worker("spec", build_prompt("spec", issue.number, issue.title, issue.body))
    if not spec.ok:
        return _fail(run, "spec worker failed", spec.text)
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
        run.log(f"build round {plan.round} gate {gate.verdict}\n{gate.output}")
        if gate.verdict == "PASS":
            break
        try:
            nxt = ladder.next_attempt(history, gate.output)
        except retry.IdenticalRetry as e:
            extra += ["retries exhausted", f"retry identical: {e}"]
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
        return _finish(run, "awaiting-human", gate.verdict, stats, extra)

    ctx.out(f"verify: {NOT_IMPLEMENTED}; forcing T2")
    ctx.out(f"sealed tests: {NOT_IMPLEMENTED}; forcing T2")
    run.move("verifying")
    return _finish(run, "awaiting-human", "PASS", stats,
                   [f"verifier {NOT_IMPLEMENTED}", f"sealed tests {NOT_IMPLEMENTED}"])


def run_once(ctx: Context, dry_run: bool = False) -> RunResult:
    rows = ctx.ledger.rows()
    now = ctx.now()
    block = stops.new_claim_block(ctx.root, ctx.tracker, rows, ctx.policy, now)
    if block:
        ctx.out(f"halted: {block}")
        return RunResult("halted", message=block)
    issue, skipped = select_claimable(ctx.tracker)
    for n in ctx.tracker.ambiguous:
        ctx.out(f"skipped #{n}: carries multiple factory state labels")
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

    attempt = 1 + sum(1 for r in rows if r["issue"] == issue.number and r["outcome"] != "refused")
    run = _Run(ctx, issue, ledger_mod.spent_on(rows, now.astimezone(timezone.utc).date()), attempt)
    try:
        result = _process(run)
    except (StateMismatch, NotAllowlisted) as e:
        if run.state == "queued":   # lost the claim: nothing started, nothing spent
            ctx.out(f"skipped #{issue.number}: {e}")
            return RunResult("skipped", issue.number, message=str(e))
        _crash(run, e)
        raise
    except BaseException as e:
        _crash(run, e)
        raise
    ctx.out(f"#{issue.number}: {result.outcome} at {result.tier}")
    return result


def _crash(run: _Run, exc: BaseException) -> None:
    """Spend must never go unrecorded: ledger row first, in its own try; then park, in another."""
    why = f"unexpected error: {type(exc).__name__}"
    run.log(f"{why}: {exc}")
    try:
        run.record("failed", "T2", [why], "none", False)
    except Exception as e:  # already unwinding another error; report and carry on to the park attempt
        run.ctx.out(f"LEDGER WRITE FAILED for #{run.issue.number}: {e}")
    try:
        if run.state not in ("failed", "awaiting-human", "done"):
            run.move("failed")
    except Exception as e:  # same: never mask the original error
        run.ctx.out(f"could not park #{run.issue.number} as failed (state {run.state}): {e}")
