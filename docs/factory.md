# Software factory (phase 3: sandboxed workers)

A deterministic runner takes GitHub issues labelled `factory:queued`, launches
headless `claude -p` workers, runs gates, classifies the change into a risk tier and
writes a ledger row. In `sandbox.mode: actions` (the shipped setting) workers and gates run on
ephemeral GitHub Actions runners, not on the operator's machine. Design: `docs/specs/2026-11-10-software-factory-design.md`.

## Run it

Run from the repository checkout that holds `.factory/policy.yaml`. Needs `gh`
(authenticated, able to dispatch workflows and download artifacts) and `git` with push access
to `origin`. `claude` on PATH is only needed in `local` mode.

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

The ledger (`ledger.jsonl`) is append-only, one row per issue run. It and the per-issue
logs (`logs/issue-N.log`, which hold worker and gate output) live in `state_dir`
(policy; default `~/.local/state/myagents-factory`), outside the repository, so a
worker's working directory does not contain them. A `state_dir` inside the repo is refused.
Issue comments carry only the tier and fixed reason codes, never worker output.

## Sandbox mode

Policy section `sandbox` (`mode`, `worker_workflow`, `gates_workflow`, `poll_seconds`,
`timeout_minutes`). Missing or malformed is a policy error. The mode is written to every
ledger row (`sandbox`; older rows without it still load) so phase 4 can refuse autonomy for
rows produced unsandboxed. `status` prints it.

`actions` mode, per worker call:

1. The launcher checks that the worktree is on a `factory/<n>-<slug>` branch and clean, then
   pushes that branch to `origin`. Pushes are never forced; a rejected push is an error result.
2. It dispatches `.github/workflows/factory-worker.yml` with `--ref main`, passing the branch,
   role, model, budget, a random `request_id` and the prompt as gzip+base64. A prompt that
   encodes to more than 48,000 characters fails without dispatching.
3. The workflow checks out `main` into `trusted/` and the branch into `work/` (no credentials
   persisted). `python3 -m scripts.factory.sandbox_worker` from `trusted/` validates every
   input, runs `claude -p` in `work/` with the same argv as the local launcher, snapshots
   uncommitted changes, and uploads `changes.patch` and `result.json` as `factory-result-<request_id>`.
4. The launcher finds the run by its `run-name` (`gh run list`), waits with a hard timeout,
   downloads the artifact into a fresh directory under `state_dir`, and validates `result.json`
   strictly (types, matching `request_id`, `start_sha` equal to the pushed commit).
5. It checks the patch (no absolute paths, `..`, `.git` components, new symlinks or gitlinks;
   those are rejected because the classifier does not force them to T2), applies it with
   `git apply --index`, commits `factory: worker output (<role>)` and pushes again.
6. A timeout maps to return code 124, any other failure to a non-zero code, both with
   `cost_known: false`, so the runner charges the remaining per-issue budget.

Gates work the same way through `factory-gates.yml`: the gate runner makes sure the remote
branch equals local HEAD (pushing if behind, refusing if diverged), dispatches, downloads
`gates-output.txt`, and parses the verdict. A timeout, run error, missing artifact, or output
for a different commit is `MISCONFIGURED`. A forged extra verdict line is `MISCONFIGURED` too.

`local` mode runs `claude` and `gates.sh` on this machine with the scrubbed environment. It is
unsandboxed and for development only.

### One-time owner setup

- Merge the workflows to `main` first. Dispatch uses `--ref main`, so `factory-worker.yml` and
  `factory-gates.yml` must exist there.
- Create the repository secret `FACTORY_ANTHROPIC_API_KEY`. Use a dedicated API key with its own
  spend limit in the Anthropic Console, not a shared or personal key. This is the only secret
  the workflows reference, and only in the `Run worker` step.
- Keep Actions workflow permissions at read-only for the repo and do not add other secrets
  that the dispatched workflows could reach. Branch protection on `main` is still required
  before phase 4.

## What phase 3 does not do yet

- Every category is forced to T2 at integration. Nothing auto-merges.
- Verify and sealed-test steps are stubs that report "not implemented in phase 2" and force T2.
  Building them is the next phase 3 task.
- The spec ambiguity check is a stub.
- There is no merge step and no merge workflow. The runner opens no PRs. In `actions` mode it
  pushes `factory/` branches, never `main`.
- No self-filed issues, no daily digest, no earned autonomy in effect (the ledger reader
  computes levels, but the runner ignores them until phase 4).

## Hardening

- Workers run on an ephemeral GitHub-hosted runner with `permissions: contents: read`, no
  checkout credentials, and none of the operator's credentials. The workflow file and the
  scripts that drive it come from `main`; the worker's branch is data. Workflow inputs reach
  scripts only through environment variables, never inside `run:` bodies.
- The API key is set only on the step that runs the worker, together with
  `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB=1`, which strips it from the environment of everything
  Claude Code spawns (Bash tool, tests, hooks). Documented in the Claude Code environment
  variable reference; it needs Claude Code 2.1.251 or later, and the workflow pins 2.1.311.
  The entrypoint's own git calls run without the key, with hooks disabled.
- Local-side checks on anything a runner sends back: strict `result.json`, patch path and mode
  checks, size caps, gate verdict parsing that needs exactly one final verdict line.
- `gates.sh <worktree> <base_ref>` reports MISCONFIGURED if the worker changed, added or deleted
  the gate entry script, the harnesses it auto-discovers, pytest config or conftest, or the files
  they read, and requires `scripts/test.sh` to equal the base commit's copy.
- Workers are launched with `--max-budget-usd` set to the remaining budget. `claude --help`
  shows no per-run turn-limit flag, so none is passed. A timed-out worker or unknown cost is
  charged the rest of the per-issue budget and the row records `cost_known: false`.
- A requeued issue gets a fresh worktree and branch (`factory/N-slug-a2`); branches are never deleted.

## Known limits

- Cost and gate output come from a machine where worker code ran. A worker can write a forged
  `result.json` or gate output file; the local checks catch malformed or mismatched data, not
  a well-formed lie. The verifier and sealed tests (next in phase 3) are the cross-check, and
  until they exist everything is T2 and a person reviews it.
- GitHub-hosted runners have open network egress. If the subprocess scrub does not hold, the
  API key can leak to anywhere. That is why the key must be dedicated with a spend limit.
  The scrub recognizes credentials by variable name or value shape, so it is one layer, not a guarantee.
- The runner is only as isolated as GitHub makes it. Worker code can modify files on that
  runner, including action code, after the key is in scope for the worker step. The blast
  radius is one disposable runner and one capped key.
- `GITHUB_TOKEN` is read-only but still present on the runner for the workflow's own steps.
  The repo is public, so its contents are not secret.
- `local` mode is unsandboxed: a worker can execute arbitrary code as the operator. Use it for
  development only. Phase 4 must refuse autonomy for rows whose `sandbox` is not `actions`.
- Concurrent dispatches for one branch queue (no cancel). Artifacts are kept 3 days.
