# Software Factory Design (Gray Mode)

Status: Approved by CEO 2026-11-10 (direction and the four decisions below). Detailed thresholds are defaults and open to tuning.

## Goal

Turn MyAgents from a prompt library into a factory: a GitHub issue goes in, a gated and merged change comes out, and a person is involved only where the risk warrants it.

Reference: the factories catalogued in `varun1505/awesome-software-factories`. The patterns adopted here come from Stripe Minions (deterministic skeleton, bounded retries), addyosmani/factory (issue labels as state, gates that fail loudly), dark-factory (cross-model verification, sealed tests), Gas Town (serialized merge) and Uber (per-agent model routing, cost per merged change).

## Decisions

1. Autonomy: gray mode, defined below. Unattended by default, human by exception.
2. Backlog: GitHub issues with `factory:*` labels.
3. The product gates in `CLAUDE.md` (tenant, ledger, alembic) move to a template that target projects receive. MyAgents gets gates that fit it.
4. `chore/consolidation-a`, `chore/consolidation-b` and `worktree-fix-instinct-observer-unwire` are already merged into `origin/main`. Their worktrees and branches are removed.

## Gray mode

A light factory puts a person on every spec and every merge. A dark factory puts a person on neither. Gray mode decides per change, from the risk of that change, and widens or narrows its own autonomy from its track record.

### Risk tiers

A deterministic classifier (no model call) assigns each change a tier from the diff and the issue. The highest matching tier wins.

| Tier | Matches | Spec approval | Merge |
|---|---|---|---|
| T0 | Docs, tests, comments, changes under the size cap that touch no protected path | None | Automatic |
| T1 | Ordinary changes inside an existing module, gates green, verifier agrees | None, unless the spec is ambiguous | Automatic, listed in the daily digest, revertable |
| T2 | Any protected path, new dependency, deleted files over the cap, diff over the size cap, verifier disagreement, retries exhausted, budget exceeded, sealed-test failures | Human | Human |

Protected paths, always T2: `scripts/factory/**`, `.factory/policy.yaml`, `.github/**`, `.claude/settings*`, `.agents/hooks/**`, `team/engine/**`, `CLAUDE.md`, anything matching secrets or credentials patterns. The factory can propose changes to its own gates and policy and can never merge them.

Spec ambiguity: two workers on different models each write acceptance tests from the issue without seeing the other's. If the two suites disagree on behaviour past a threshold, the issue goes to a person for clarification before any build.

### Earned autonomy

The ledger records every merged change with its tier, path category, cost and whether it was later reverted or needed a fix-forward within 14 days.

- A path category starts at T2 for its first 5 merged changes.
- It is promoted to T1 after 5 consecutive clean merges, and its T0-eligible changes then merge at T0.
- One revert demotes the category one tier and resets the count.
- Protected paths are never promoted.

### Self-direction

The factory may file its own issues: from gate failures on main, tech-debt scans, pending instincts and its own cost outliers. Self-filed issues carry `factory:proposed`. T0 proposals enter the queue directly. Everything else waits for a person to relabel it `factory:queued`. A cap on open proposals stops it flooding the backlog.

### Hard stops

- Kill switch: the file `.factory/STOP` or the label `factory:halt` on any open issue stops new claims. Running work finishes its current step and parks.
- Spend cap: a per-issue and a per-day budget in `.factory/policy.yaml`. At the cap the runner refuses to start work; it does not warn and continue.
- Queue caps: at most N issues awaiting a person. Past that, the factory stops claiming new T2-bound work.
- Workers never push to `main` and never run `gh pr merge`. Merging is done by a GitHub Actions workflow acting on a label, with required checks.

## Pipeline

Issue labels are the state machine: `factory:queued` → `claimed` → `building` → `verifying` → `merge-ready` → `done`, with `awaiting-human` and `failed` as side exits.

1. Intake. A person or the factory files an issue. The runner picks the oldest `factory:queued` issue.
2. Claim. Pushing the branch `factory/<issue>-<slug>` is the claim; the first non-forced push wins.
3. Spec. A worker writes `specs/<issue>.md` in the branch using the existing `dev-auto` spec format, and the ambiguity check runs.
4. Build. A worker runs `dev-auto` in a dedicated worktree.
5. Gates. `scripts/factory/gates.sh` runs lint, tests and the repo's own checks and prints one verdict line: `PASS`, `FAIL` or `MISCONFIGURED`. A gate that cannot run is `MISCONFIGURED`, which counts as failure.
6. Verify. A fresh worker on a different model reads the diff cold with no access to the builder's transcript. It reverts the change to confirm the new tests fail without it, then runs the sealed tests.
7. Classify. The tier is computed from the final diff.
8. Integrate. A PR is opened. T0 and T1 get `factory:merge-ready` and the merge workflow merges them one at a time after checks pass on the rebased branch. T2 gets `factory:awaiting-human` with a summary of why.
9. Record. The ledger gets one row: issue, tier, models used, tokens, cost, retries, outcome.

### Retry ladder

Round 1: same builder model with the gate output. Round 2: a different model family or the next model up, given only the failing assertion text. After round 2 the issue goes to `awaiting-human`. Identical retries are not allowed.

### Sealed tests

Acceptance tests written at the spec step by a separate worker are stored outside the build worktree, hashed, with a canary file. The builder never sees them. The verifier runs them and reports the fraction failing. Any sealed failure makes the change T2.

## Model routing

`.factory/policy.yaml` maps each role to a model. Defaults:

| Role | Model | Why |
|---|---|---|
| Orchestration | None | The runner is deterministic Python |
| Triage, classification support, mechanical edits | Haiku | Cheapest adequate |
| Spec, build | Sonnet | Best cost for implementation |
| Sealed-test author, verifier | Opus | Must differ from the builder |
| Retry round 2, design of T2 changes | Fable | Highest capability, used rarely |

The ledger reports cost per merged change by role and model so the table can be tuned from data.

## Components

| Path | What |
|---|---|
| `scripts/factory/` | Runner: queue adapter, state machine, classifier, worker launcher, retry ladder, ledger, CLI |
| `scripts/factory/gates.sh` | Gate runner with the verdict line |
| `.factory/policy.yaml` | Tiers, protected paths, caps, model routing |
| `.factory/ledger.jsonl` | One row per attempt |
| `.github/workflows/factory-merge.yml` | Serialized merge of `factory:merge-ready` PRs |
| `.github/workflows/ci.yml` | Runs `scripts/test.sh` on every PR |
| `templates/product-gates/` | The tenant, ledger and alembic gates, for target projects |

The runner reuses what exists: `.agents/hooks` for worktree guard and claims, `dev-auto` as the build worker, the instinct loop for learning, `scripts/test.sh` as the test entry point.

## Phases

1. Cleanup and CI: remove merged worktrees and branches, fix version metadata, retire Maestro leftovers, archive finished plans, add `ci.yml`, move product gates to the template.
2. Core: runner, classifier, gates, retry ladder, ledger, hard stops. Tested with fakes for GitHub and the worker launcher. Ships with every category at T2, so nothing merges unattended yet.
3. Verifier and sealed tests.
4. Merge workflow and earned autonomy. First point at which T0 and T1 merge without a person.
5. Self-direction and the daily digest.

## Rollback and observability

The factory is additive. Creating `.factory/STOP` halts it without touching other tooling, and removing the `factory:*` labels empties its queue. Each phase lands as its own PR and can be reverted alone.

Working in production means: the ledger shows merged changes per day, cost per merged change, revert rate per tier and time spent in `awaiting-human`. A rising revert rate at T0 or T1 is the signal to tighten the tiers.

## Open items

- Worker sandbox, blocking for phase 4. Independent review of phase 2 found that a worker allowed to write files and run the test suite can execute arbitrary code as the operator: it can read credentials, edit the ledger and decide its own gate verdict. Phase 2 adds interim hardening (scrubbed environment, gate scripts taken from the base ref, ledger outside the repo). Unattended merges stay off until workers and gates run in a sandbox with no write access outside the worktree and no operator credentials. Candidates: ephemeral GitHub Actions runners, a container per run, or the Claude Code sandbox mode. Choosing one is the first task of phase 3.
- Gate inputs are protected paths. Everything `scripts/test.sh` runs, test configuration such as `conftest.py`, and test deletions are T2. T0 requires verifier agreement.

- Branch protection and required checks on `main` must be turned on by the repo owner before phase 4.
- The repo is public. Issue text is untrusted input to the workers; the runner only claims issues filed or labelled by the allowlisted accounts in the policy file.
- Thresholds (size cap, ambiguity threshold, promotion count) are starting values.
