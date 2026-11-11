"""Deterministic runner: intake -> claim -> spec -> sealed tests -> build -> gates -> verify -> classify -> record.

Phase 3: workers, gates and verification run on ephemeral Actions runners (sandbox mode "actions").
Sealed acceptance tests are written before the build and never reach the builder; after the gates
pass, a deterministic verify job (revert check, sealed run) and a cold-read model verifier run.
Every category is still forced to T2 at integration time and there is no merge step: nothing here
opens a PR or merges. The spec ambiguity check is still a stub. In sandbox mode "actions" the
launcher, gate runner and verifier push the worker's `factory/` branch (never forced).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from . import classifier, ledger as ledger_mod, retry, stops
from .gates import GateResult, GateRunner
from .launcher import SANDBOX_REJECTED_PREFIX, Launcher, WorkerResult, build_prompt
from .ledger import Ledger
from .policy import Policy
from .sealed import (SealedError, SealedHashMismatch, SealedInvalid, SealedSet, SealedStore, build_sealed_prompt,
                     bundle as sealed_bundle, validate_sealed_patch)
from .verifier import VerifyResult, Verifier, build_verifier_prompt, parse_agreement
from .tracker import Issue, NotAllowlisted, StateMismatch, Tracker, select_claimable
from .workspace import DiffStats, Workspace, slug

PHASE = 3
FORCED_LEVEL = "T2"   # every category is T2 at integration until phase 4. Changing it is a code change
                      # under scripts/factory/**, which is itself a protected (always T2) path.
AMBIGUITY_CHECK = "not implemented (stub)"


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
    sandbox: str = "local"   # where workers and gates ran; recorded on every ledger row
    out: Callable[[str], None] = print
    verifier: Optional[Verifier] = None          # None: verification is unavailable (a T2 reason)
    sealed_store: Optional[SealedStore] = None   # default: SealedStore(state_dir)


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
    ("verifier has not agreed", "verifier-not-agreed"), ("phase", "phase-forced"),
    ("verification unavailable", "verify-unavailable"), ("verification skipped", "verify-skipped"),
    ("verifier model equals", "verifier-model-equals-builder"), ("verifier unavailable", "verifier-unavailable"),
    ("verifier returned a patch", "verifier-patch"),
    ("revert check: tests pass", "revert-passes"), ("revert check: new tests do not pass", "revert-fails-with-change"),
    ("revert check: no new tests", "revert-no-new-tests"), ("revert check error", "revert-error"),
    ("sealed tests unavailable", "sealed-unavailable"), ("sealed run collected no tests", "sealed-no-tests"),
    ("sealed canary", "sealed-canary"), ("sealed bundle hash", "sealed-hash-mismatch"),
    ("sealed path", "sealed-path-touched"),
    ("no changes", "no-changes"), ("spec worker failed", "spec-failed"),
    ("sandbox rejected path", "sandbox-rejected-path"),
    ("unexpected error", "crash"),
]


def reason_code(reason: str) -> str:
    for prefix, code in REASON_CODES:
        if reason.startswith(prefix):
            return code
    return "other"


PLAN = [
    "claim: queued -> claimed (label)",
    "spec: worker writes specs/<issue>.md (ambiguity check: " + AMBIGUITY_CHECK + ")",
    "sealed tests: author worker writes acceptance tests, collected as a patch and kept outside the repo (never pushed)",
    "build: worker on the routed model, in a dedicated worktree",
    "gates: scripts/factory/gates.sh; on failure retry ladder (same model, then a different model)",
    "verify: revert check and sealed run on an ephemeral runner, then a cold-read verifier on a different model",
    "classify: deterministic tier from the final diff; every category is forced to T2 in phase 3",
    "integrate: label awaiting-human with a summary (no PR, no merge; sandbox mode actions pushes the factory/ branch)",
    "record: one ledger row",
]


def decide_verdict(policy: Policy, paths: List[str], model_verdict: str, revert_status: str,
                   available: bool) -> Tuple[str, List[str]]:
    """The classifier's verifier verdict and the T2 reasons behind it.

    `agree` needs the model verifier to agree AND the revert check to show the new tests fail without
    the change. `no_new_tests` and `nothing_to_revert` only pass for a change whose paths are all
    docs or tests (policy t0_paths): a code change with no new tests cannot be agreed. Unavailable
    verification is never agreement (`not_run`)."""
    if not available or revert_status == "unavailable":
        return "not_run", ["verification unavailable"]
    reasons: List[str] = []
    if revert_status == "passes_without_change":
        reasons.append("revert check: tests pass without the change")
    elif revert_status == "fails_with_change":
        reasons.append("revert check: new tests do not pass with the change")
    elif revert_status in ("no_new_tests", "nothing_to_revert"):
        if not all(any(classifier.glob_match(p, path) for p in policy.t0_paths) for path in paths):
            reasons.append("revert check: no new tests for a code change")
    elif revert_status != "fails_without_change":
        reasons.append("revert check error")
    if model_verdict == "unavailable":
        return "not_run", reasons + ["verifier unavailable"]
    if model_verdict == "not_run":
        return "not_run", reasons
    if model_verdict == "disagree" or reasons:
        return "disagree", reasons
    return "agree", reasons


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
        self.sealed: Optional[SealedSet] = None
        self.pre_reasons: List[str] = []      # reasons found before the build (sealed tests unavailable)
        self.build_texts: List[str] = []      # builder result text, searched for the sealed canary
        self.verify_info: Optional[dict] = None

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
        return self._account(role, res)

    def collect_worker(self, role: str, prompt: str) -> Tuple[WorkerResult, bytes]:
        """A worker whose patch comes back unapplied. Its spend counts like any other worker's."""
        res, patch = self.ctx.launcher.collect(role, prompt, self.worktree, model=None,
                                               max_budget_usd=self.remaining_budget())
        return self._account(role, res), patch

    def _account(self, role: str, res: WorkerResult) -> WorkerResult:
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
            "sandbox": self.ctx.sandbox,
            "started_at": self.started.isoformat(), "finished_at": finished.isoformat()}
        if self.verify_info is not None:
            row["verify"] = self.verify_info
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


def _touches_sealed(paths: List[str]) -> bool:
    for raw in paths:
        n = classifier.normalize_path(raw)
        if n is None or n.casefold().split("/")[:2] == ["tests", "sealed"]:
            return True
    return False


def _finish(run: _Run, outcome_state: str, gate: str, stats: Optional[DiffStats],
            extra_reasons: List[str], verdict: str = "not_run", sealed_failures: int = 0) -> RunResult:
    ctx = run.ctx
    extra_reasons = list(extra_reasons) + [r for r in run.pre_reasons if r not in extra_reasons]
    if stats and _touches_sealed(stats.paths):
        extra_reasons.append("sealed path in build diff")
    reasons = list(extra_reasons)
    protected = False
    category = "none"
    if stats and stats.paths:
        category = classifier.category(stats.paths)
        c = classifier.classify(
            ctx.policy, stats.paths, stats.added, stats.deleted, stats.deleted_files, False,
            verdict, sealed_failures, "retries exhausted" in extra_reasons, "budget exceeded" in extra_reasons,
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
        if spec.text.startswith(SANDBOX_REJECTED_PREFIX):
            return _fail(run, "sandbox rejected path", spec.text)
        return _fail(run, "spec worker failed", spec.text)
    ctx.out(f"ambiguity check: {AMBIGUITY_CHECK}")
    run.move("building")
    _author_sealed(run)

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
        run.build_texts.append(res.text)
        gate = (ctx.gates.run(run.worktree) if res.ok
                else GateResult("FAIL", f"build worker exited {res.returncode}\n{res.text}"))
        run.log(f"build round {plan.round} gate {gate.verdict}\n{gate.output}")
        if not res.ok and res.text.startswith(SANDBOX_REJECTED_PREFIX):
            extra.append("sandbox rejected path")   # hostile or broken output: park it, no retry
            break
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

    if not stats.paths:
        return _finish(run, "awaiting-human", "PASS", stats, [])
    block = run.budget_block()
    if block:
        return _finish(run, "awaiting-human", "PASS", stats,
                       ["budget exceeded", block, "verification skipped: budget exhausted"])
    run.move("verifying")
    return _verify(run, stats)


def _author_sealed(run: _Run) -> None:
    """Write the sealed acceptance tests from the spec commit. The patch is collected, never applied or
    pushed, and kept outside the repository. Any failure only means the change has no sealed tests."""
    ctx, issue = run.ctx, run.issue

    def unavailable(why: str, detail: str = "") -> None:
        run.log(f"sealed tests unavailable ({why}) {detail}")
        run.pre_reasons.append(f"sealed tests unavailable: {why}")

    block = run.budget_block()
    if block:
        return unavailable("budget exhausted", block)
    ctx.workspace.snapshot(run.worktree)           # a local-mode spec worker may not have committed
    spec_sha = ctx.workspace.head_sha(run.worktree)
    res, patch = run.collect_worker("sealed_test_author",
                                    build_sealed_prompt(issue.number, issue.title, issue.body))
    if not res.ok:
        return unavailable("author failed", res.text)
    try:
        validate_sealed_patch(patch, issue.number, ctx.policy.sealed.max_patch_bytes)
        store = ctx.sealed_store or SealedStore(ctx.state_dir)
        run.sealed = store.save(issue.number, run.attempt, patch, spec_sha)
    except SealedError as e:
        return unavailable("patch invalid or not stored", str(e))


def _verify(run: _Run, stats: DiffStats) -> RunResult:
    ctx, issue = run.ctx, run.issue
    reasons: List[str] = []
    bundle: Optional[bytes] = None
    if run.sealed is not None:
        token = run.sealed.canary
        if token in ctx.workspace.diff_text(run.worktree) or any(token in t for t in run.build_texts):
            reasons.append("sealed canary found in build output")
        try:
            bundle = sealed_bundle((ctx.sealed_store or SealedStore(ctx.state_dir)).load(issue.number, run.attempt))
        except SealedHashMismatch as e:
            run.log(f"sealed bundle refused: {e}")
            reasons.append("sealed bundle hash mismatch")
        except SealedError as e:
            run.log(f"sealed bundle unreadable: {e}")
            reasons.append("sealed tests unavailable: store unreadable")

    vr = (ctx.verifier.verify(run.worktree, issue.number, bundle) if ctx.verifier
          else VerifyResult.unavailable("no verifier configured"))
    run.log(f"verify job: available={vr.available} revert={vr.revert_check} sealed={vr.sealed_status} "
            f"total={vr.sealed_total} failed={vr.sealed_failed} errors={vr.sealed_errors} detail={vr.detail}")
    if vr.available:
        if vr.sealed_status == "no_tests":
            reasons.append("sealed run collected no tests")
        elif vr.sealed_status in ("invalid", "crash", "oversize"):
            reasons.append(f"sealed tests unavailable: verify run reported {vr.sealed_status}")

    builders = {m.strip().casefold() for m in run.models.get("build", [])}
    if ctx.policy.routing["verifier"].strip().casefold() in builders:
        model_verdict = "not_run"
        reasons.append("verifier model equals builder model")
    elif run.budget_block():
        model_verdict = "not_run"
        reasons += ["budget exceeded", "verification skipped: budget exhausted"]
    else:
        res, patch = run.collect_worker("verifier", build_verifier_prompt(issue.number, issue.title, issue.body))
        run.log(f"verifier output (rc {res.returncode}):\n{res.text}")
        if not res.ok:
            model_verdict = "unavailable"
        elif patch.strip():
            model_verdict = "disagree"           # a read-only reviewer that changed files is not agreeing
            reasons.append("verifier returned a patch")
        else:
            model_verdict = parse_agreement(res.text)

    verdict, why = decide_verdict(ctx.policy, stats.paths, model_verdict, vr.revert_check, vr.available)
    reasons += why
    sealed_ran = vr.available and vr.sealed_status == "ran" and bundle is not None   # a result for tests never sent is not trusted
    failures = vr.sealed_failures if sealed_ran else 0
    run.verify_info = {"model_verdict": model_verdict, "revert_check": vr.revert_check,
                       "sealed_available": sealed_ran, "sealed_total": vr.sealed_total if sealed_ran else 0,
                       "sealed_failed": failures}
    return _finish(run, "awaiting-human", "PASS", stats, reasons, verdict=verdict, sealed_failures=failures)


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
