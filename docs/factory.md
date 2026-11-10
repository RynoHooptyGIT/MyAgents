# Software factory (phase 2: Core)

A deterministic runner takes GitHub issues labelled `factory:queued`, launches
headless `claude -p` workers in git worktrees, runs gates, classifies the change
into a risk tier and writes a ledger row. Design: `docs/specs/2026-11-10-software-factory-design.md`.

## Run it

Run from the repository checkout that holds `.factory/policy.yaml`. Needs `gh`
(authenticated) and `claude` on PATH.

```
python3 -m scripts.factory status
python3 -m scripts.factory run --once --dry-run   # prints the plan, changes nothing
python3 -m scripts.factory run --once             # at most one issue
```

Exit codes: 0 normal (including idle), 2 error (bad or missing policy, corrupt
ledger, gh or git failure), 3 a hard stop blocked the run.

Tests: `python3 -m pytest scripts/factory` (also picked up by `bash scripts/test.sh`).
Tests use fakes; nothing calls GitHub or launches `claude`.

## Label states

`factory:proposed` -> `queued` -> `claimed` -> `building` -> `verifying` ->
`merge-ready` -> `done`, with `awaiting-human` and `failed` as side exits. An
issue carries exactly one state label. A person moves `awaiting-human` or
`failed` back to `queued`, or `awaiting-human` to `done`. Any other transition raises.
`factory:halt` is a control label, not a state.

Only issues whose author is in `allowlisted_authors` are claimed. Issue text is
untrusted: it reaches workers on stdin and is never placed in a command line.

## Hard stops

- `.factory/STOP` file, or `factory:halt` on any open issue: no new claims.
- Per-issue and per-day budget (`budget` in the policy): the runner refuses to start
  a worker once the cap is reached and parks the issue at T2.
- `queue.max_awaiting_human`: no new claims while that many issues wait for a person.

## Policy and ledger

`.factory/policy.yaml` holds tiers, protected paths, size caps, promotion count,
budgets, queue caps, allowed authors and the role-to-model table. A missing or
malformed policy stops the run; there are no silent defaults.

`.factory/ledger.jsonl` is append-only, one row per issue run, and is gitignored
(`.factory/.gitignore`) because it is local runtime state and holds cost data.

## What phase 2 does not do yet

- Every category is forced to T2 at integration. Nothing auto-merges.
- Verify and sealed-test steps are stubs that report "not implemented in phase 2" and force T2.
- The spec ambiguity check is a stub.
- There is no merge step and no merge workflow. The runner does not push, open PRs or merge.
  Claiming is a label change, not a branch push; the worktree and branch stay local.
- No self-filed issues, no daily digest, no earned autonomy in effect (the ledger reader
  computes levels, but the runner ignores them until phase 4).
