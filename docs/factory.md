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
   downloads the artifact into a fresh directory under `state_dir` (deleted after use), and validates `result.json`
   strictly (types, matching `request_id`, `start_sha` equal to the pushed commit).
5. It checks the patch (no absolute paths, `..`, `.git` components, new symlinks or gitlinks,
   and nothing on the hard deny-list below), applies it with `git apply --index`, commits
   `factory: worker output (<role>)` and pushes again. Symlinks and gitlinks are rejected
   because the classifier does not force them to T2.
6. A timeout maps to return code 124, any other failure to a non-zero code, both with
   `cost_known: false`, so the runner charges the remaining per-issue budget.

Gates work the same way through `factory-gates.yml`: the gate runner makes sure the remote
branch equals local HEAD (pushing if behind, refusing if diverged), dispatches, downloads
`gates-output.txt`, and parses the verdict. A timeout, run error, missing artifact, or output
for a different commit is `MISCONFIGURED`. A forged extra verdict line is `MISCONFIGURED` too.

`local` mode runs `claude` and `gates.sh` on this machine with the scrubbed environment. It is
unsandboxed and for development only.

### Denied paths (a deliberate narrowing of the spec)

The spec lets the factory propose changes to its own gates. In sandbox mode it cannot propose
changes to the paths below at all, for now. A pushed commit is read by GitHub (workflows run
from the pushed YAML with repo secrets in scope) and by people and tools that open the
worktree (editor tasks, direnv, agent configs, git hooks, submodules). The list is a constant
in `scripts/factory/actions.py` (`denied_path`), independent of the policy file, matched
case-insensitively on normalised path components, and fails closed:

- `.github/` at any depth
- `.claude/`, `.vscode/`, `.idea/`, `.devcontainer/`, `.husky/` at any depth
- `CLAUDE.md`, `CLAUDE.local.md`, `AGENTS.md`, `.mcp.json`, `.envrc`, `.gitattributes`,
  `.gitmodules`, `.lfsconfig` at any depth
- `.agents/` and `hooks/` at the repo root

A patch that adds, renames into or out of, deletes or changes the mode of any of them is
rejected before anything is applied, committed or pushed. The result carries the marker
`sandbox-rejected-path`; the runner parks the issue at once with the reason code
`sandbox-rejected-path` and does not retry. The same check runs before every push the
launcher and gate runner make: if the branch already differs from `origin/main` on a denied
path (or `origin/main` is missing) nothing is pushed. All operator-side git commands run with
`core.hooksPath=/dev/null` and `core.fsmonitor=false`.

### One-time owner setup

- Merge the workflows to `main` first. Dispatch uses `--ref main`, so `factory-worker.yml` and
  `factory-gates.yml` must exist there.
- Create the repository secret `FACTORY_ANTHROPIC_API_KEY`. Treat the key as burnable: a
  dedicated key, not shared or personal, with a low spend limit set in the Anthropic Console
  and rotated on a schedule and after any suspected leak. This is the only secret the
  workflows reference, and only in the `Run worker` step.
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
  scripts only through environment variables, never inside `run:` bodies. The workflows use
  no concurrency group: the operator side processes one issue at a time, and a group with
  `cancel-in-progress: false` would still cancel an older pending run when a newer one queued.
- The sandboxed `claude` is started with `--setting-sources user` and `--strict-mcp-config`
  (both in the Claude Code CLI reference), so project and local settings (hooks, env
  overrides, `apiKeyHelper`) and project MCP config from the worker's branch are ignored. As a
  second layer the entrypoint refuses to run if `.mcp.json`, `CLAUDE.local.md` or anything under
  `.claude/` in the branch differs from the copy in `trusted/` (or main has none). A branch
  cut from a stale main whose `.claude/` has since changed is refused too; rebase it.
  The local launcher's argv is unchanged.
- The entrypoint's own git calls run without the API key, with hooks disabled.
- `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB=1` is set on the worker step. Per the environment variable
  reference it strips credentials from the environment of what Claude Code spawns (Bash tool,
  hooks, stdio MCP servers); it needs Claude Code 2.1.251 or later and the workflow pins
  2.1.311. It does not protect the key from worker code that can read it another way (see
  Known limits).
- Local-side checks on anything a runner sends back (strict `result.json`, patch path and mode
  checks, the deny-list above, size caps, gate verdict parsing that needs exactly one final
  verdict line) catch accidents, malformed output and naive forgery. They are not protection
  against a hostile worker. The same goes for `gates.sh`'s trusted-base check: it stops a
  worker accidentally or casually editing gate files, nothing more.
- Workers are launched with `--max-budget-usd` set to the remaining budget, but in sandbox mode
  the runner's cost report is only a number the runner sent back. A timed-out worker or unknown
  cost is charged the rest of the per-issue budget and the row records `cost_known: false`.
- A requeued issue gets a fresh worktree and branch (`factory/N-slug-a2`); branches are never deleted.

## Known limits

- The API key is exposed to worker code by design. It is in the worker step's process
  environment and readable through `/proc` whatever the subprocess scrub does, and runners have
  open network egress. The key is burnable: dedicated, low Console spend limit, rotated. The
  Console limit is the only real spend cap. The per-issue and per-day budgets in the policy
  are accounting based on figures the runner reports and can be forged.
- A gate `PASS` on a factory branch is advisory until the verifier exists. Test code runs on the
  same VM that writes the verdict file, so a hostile worker can write whatever verdict it likes.
  Everything is T2 and a person reviews it. The verifier and sealed tests (next in phase 3) are
  the cross-check.
- Result and patch contents are untrusted data. A well-formed lie (a forged cost, a patch that
  does something unwanted inside the allowed paths) passes the local checks.
- Worker code runs on the same runner as the later steps (entrypoint, artifact upload) and can
  modify files there, including action code, after the key is in scope. The blast radius is one
  disposable runner and one capped key. Passwordless sudo and open egress are not removed: no
  documented way to drop sudo on `ubuntu-latest` was found, and an egress allowlist
  (step-security/harden-runner in block mode) was not added because its endpoint format and
  the endpoint set that GitHub's own artifact upload needs could not be verified without
  running it. It is a candidate follow-up, tested on a real run.
- If a dispatched run never appears in `gh run list` within the queue timeout, there is no run
  id to cancel. The operator side reports a timeout, but that run may still start later and
  consume runner minutes and API spend against the key. The branch it would work on is not
  applied locally.
- Queue time (30 minutes for a run to appear and start) and run time (`sandbox.timeout_minutes`
  once started, shipped as 75 against the workflow's 60 minute cap) are limited separately.
- `GITHUB_TOKEN` is read-only and checkouts do not persist it. The repo is public, so its
  contents are not secret.
- `local` mode is unsandboxed: a worker can execute arbitrary code as the operator. Use it for
  development only. Phase 4 must refuse autonomy for rows whose `sandbox` is not `actions`.
- Artifacts are kept 3 days. The operator side deletes its downloaded copy after each use.
