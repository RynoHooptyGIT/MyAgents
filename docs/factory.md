# Software factory (phase 3: sandboxed workers, sealed tests, verification)

A deterministic runner takes GitHub issues labelled `factory:queued`, launches
headless `claude -p` workers, runs gates, classifies the change into a risk tier and
writes a ledger row. In `sandbox.mode: actions` (the shipped setting) workers and gates run on
ephemeral GitHub Actions runners, not on the operator's machine. Design: `docs/specs/2026-11-10-software-factory-design.md`.

Phase 3 is complete: sandboxed workers and gates, sealed acceptance tests, a deterministic verify
job and a cold-read model verifier. Every change still parks at T2 for a person. Nothing merges
unattended, there is no merge step, and the spec ambiguity check is still a stub.

## Pipeline as it runs

1. Claim: `queued` -> `claimed`.
2. Spec: a worker writes `specs/<issue>.md`. The ambiguity check is a stub (the runner prints
   `ambiguity check: not implemented (stub)`); it never blocks anything.
3. Sealed tests: a `sealed_test_author` worker (opus) runs from the spec commit and writes
   acceptance tests under `tests/sealed/issue-<N>/`. Its patch is collected, validated and stored
   outside the repo. It is never applied to the build worktree and never pushed. If the author
   fails or its patch is invalid, the build goes ahead and the change gets the T2 reason
   `sealed tests unavailable`.
4. Build and gates: unchanged (retry ladder, same model then a different model).
5. Verify, after gates PASS (state `verifying`):
   - the verify job (`factory-verify.yml`): revert check and sealed run;
   - the model verifier: a cold read by a different model.
   Both are skipped, with a reason, if the budget is exhausted.
6. Classify and record: the classifier gets `verifier_verdict` and `sealed_failures`, every
   category is forced to T2, one ledger row is written (with a `verify` object), the issue is
   labelled `awaiting-human` with a comment that holds reason codes only.

## Sealed tests

The sealed set is what the builder must not see. The repo is public, so a pushed branch is readable
by the builder, and the sealed bytes therefore never go into any branch.

- Store: `state_dir/sealed/issue-<N>-a<attempt>/` holds `sealed.patch` and `manifest.json` (patch
  sha256, spec commit SHA, a random canary token generated on the operator side, timestamp). The
  hash is recomputed before every use; a mismatch means the set is refused
  (`sealed bundle hash mismatch`).
- Validation (operator side when collected, again on the runner), fail closed: every touched path
  is a new regular file (mode 100644) under `tests/sealed/issue-<N>/`, named `test_*.py` or
  `__init__.py`, at least one `test_*.py`, no modification, deletion, rename, copy, mode change,
  link or binary content, size under `sealed.max_patch_bytes` (policy, shipped as 100000), and the
  patch must apply to an empty tree.
- Deny rule: `tests/sealed/` is in the hard deny-list (`actions.denied_path`) for every ordinary
  patch (spec, build, retry, verifier) and `assert_pushable` refuses a branch that contains it.
  The policy's `sealed.dir` must equal `tests/sealed` because the code constant cannot move.
- Canary: the bundle sent for verification is the stored patch plus
  `tests/sealed/issue-<N>/canary_<token>.txt`. After the build the runner searches the build diff,
  its commit messages and the builder's result text for the token. A hit adds the T2 reason
  `sealed canary found in build output`. The token exists only in the operator's store and in the
  verification input, so a hit means the builder reached one of them.
- `sealed_failures` for the classifier is failed + errors from the sealed run.

## The verify job (`factory-verify.yml`)

Same rules as `factory-gates.yml`: `workflow_dispatch` only, dispatched on `main`, `contents: read`,
no secrets, `main` in `trusted/` and the branch in `work/` (full history, no persisted credentials),
inputs only through `env:`, a validation step before the branch checkout, no concurrency group.
Inputs: `branch`, `request_id`, `expected_sha`, `issue`, `sealed_b64` (gzip+base64 bundle, may be
empty; capped at 48,000 encoded characters, larger bundles are not dispatched and the sealed set is
reported unavailable). `python3 -m scripts.factory.sandbox_verify` (stdlib only) runs from
`trusted/`, each step in its own scratch git worktree:

1. HEAD of `work/` must equal `expected_sha`.
2. Revert check. From `git diff --name-status origin/main...HEAD`: T = changed or added Python test
   files (policy `test_paths`, `*.py`, not `conftest.py` or `__init__.py`); S = every other changed
   path. Run T with the change (it must pass: exit 0 and at least one test passed, otherwise
   `fails_with_change`), then restore every path in S to its pre-change state (the merge base; paths the
   change added are removed) and run T again with a timeout.

   | Result without the change | Status |
   | :- | :- |
   | pytest exit 1 or 2 | `fails_without_change` (the wanted outcome) |
   | exit 0 | `passes_without_change` |
   | exit 5, or no test files | `no_new_tests` |
   | S is empty (test-only change) | `nothing_to_revert` |
   | anything else, or a timeout | `error` |

   Exit 2 (collection errors) counts as failing: an import error caused by a missing implementation
   is a legitimate failure. Exit 2 also covers a broken test file, which is why the with-change run
   must pass first. The merge base rather than `origin/main` is the pre-change state, so an advanced
   `main` does not leak into the reverted tree.
3. Sealed run: validate the bundle again, `git apply` it in a fresh worktree, run pytest on
   `tests/sealed/issue-<N>/` with `--junitxml`, report total, failed, errors, skipped. Status `ran`,
   `no_tests` (nothing collected, or everything skipped), `invalid`, `crash` (no XML, timeout, other exit
   code, or pytest and its XML disagree) or `not_provided`. Only `ran` counts as a sealed run.
4. `verify.json` (`request_id`, `sha`, `revert_check`, `sealed`) is uploaded as
   `factory-verify-<request_id>` with `if: always()`.

The operator side (`ActionsVerifier`, or `LocalVerifier` in `local` mode, which runs the same
entrypoint here) parses `verify.json` strictly: exact keys, types, `request_id`, `sha`, consistent
counts, and whether a bundle was sent. Anything malformed, missing or from a failed run is
`verification unavailable`, never agreement.

## The model verifier

A `verifier` worker (opus) is given only the issue text and fixed instructions: review
`git diff origin/main...HEAD` against the issue and `specs/<N>.md`, look for code or tests that tamper
with test infrastructure, processes, the environment or files outside the repository, and finish with
one line `FACTORY-VERIFY: AGREE` or `FACTORY-VERIFY: DISAGREE`. It never sees the builder's transcript.
It gets read-only tools from a code constant (`launcher.ROLE_TOOLSETS`): `--tools Read,Glob,Grep,Bash`,
allowed `Read`, `Glob`, `Grep`, `Bash(git diff:*)`, `Bash(git log:*)`, `Bash(git show:*)`, no Edit, Write or
test commands. The verdict must be the single verdict line and the last non-empty line; anything else is
disagreement. A verifier that returns a patch is disagreeing and the patch is dropped (`collect`).
Its model must differ from every model that built the change, including a retry round; if not, it is
not run (`verifier model equals builder model`).

`agree` reaches the classifier only when the model agrees and the revert check is
`fails_without_change`. `no_new_tests` and `nothing_to_revert` are accepted only when every changed
path is docs or tests (policy `t0_paths`): a code change with no new tests cannot be agreed.

## T2 reasons added in phase 3

Issue comments carry the code only. Worker, verifier and verify-job text stays in the local log.

| Code | Reason | Meaning |
| :- | :- | :- |
| `sealed-unavailable` | sealed tests unavailable | no usable sealed set: author failed, patch invalid, store error, budget, or the verify run could not use the bundle (invalid, crash, oversize) |
| `sealed-no-tests` | sealed run collected no tests | the sealed run collected nothing or only skips |
| `sealed-failure` | sealed-test failures: N | failed + errors in the sealed run |
| `sealed-canary` | sealed canary found in build output | the token appeared in the build diff, commits or builder text |
| `sealed-hash-mismatch` | sealed bundle hash mismatch | the stored patch changed after it was saved |
| `sealed-path-touched` | sealed path in build diff | the build diff touches `tests/sealed/` |
| `verify-unavailable` | verification unavailable | the verify job did not return a valid `verify.json` |
| `verify-skipped` | verification skipped: budget exhausted | budget gone before verify |
| `verifier-disagreement` | verifier disagreement | the model verifier did not agree |
| `verifier-patch` | verifier returned a patch | a read-only verifier changed files |
| `verifier-unavailable` | verifier unavailable | the verifier worker failed |
| `verifier-model-equals-builder` | verifier model equals builder model | not run |
| `revert-passes` | revert check: tests pass without the change | new tests prove nothing |
| `revert-fails-with-change` | revert check: new tests do not pass with the change | |
| `revert-no-new-tests` | revert check: no new tests for a code change | |
| `revert-error` | revert check error | timeout or pytest error |
| `phase-forced` | phase 3: all categories forced to T2 | always present |

The ledger row has `verify`: `model_verdict` (agree, disagree, not_run, unavailable), `revert_check`,
`sealed_available`, `sealed_total`, `sealed_failed`. Older rows load without it.

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

Policy section `sandbox` (`mode`, `worker_workflow`, `gates_workflow`, `verify_workflow`,
`poll_seconds`, `timeout_minutes`); policy section `sealed` (`dir`, `max_patch_bytes`). Missing or malformed is a policy error. The mode is written to every
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

`local` mode runs `claude`, `gates.sh` and `sandbox_verify` on this machine with the scrubbed environment. It is
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
- `tests/sealed/` at the repo root (sealed acceptance tests live outside the repo)

A patch that adds, renames into or out of, deletes or changes the mode of any of them is
rejected before anything is applied, committed or pushed. The result carries the marker
`sandbox-rejected-path`; the runner parks the issue at once with the reason code
`sandbox-rejected-path` and does not retry. The same check runs before every push the
launcher and gate runner make: if the branch already differs from `origin/main` on a denied
path (or `origin/main` is missing) nothing is pushed. All operator-side git commands run with
`core.hooksPath=/dev/null` and `core.fsmonitor=false`.

### One-time owner setup

- Merge the workflows to `main` first. Dispatch uses `--ref main`, so `factory-worker.yml`,
  `factory-gates.yml` and `factory-verify.yml` must exist there.
- Authentication is a Claude subscription (Pro, Max, Ultra, Team or Enterprise), not an API key.
  Run `claude setup-token` locally. It opens the browser authorization flow, prints a one-year
  OAuth token and saves it nowhere. Store the token as the repository secret
  `FACTORY_CLAUDE_OAUTH_TOKEN`. The worker workflow maps it to `CLAUDE_CODE_OAUTH_TOKEN`, the
  variable Claude Code reads for it (Claude Code authentication docs, "Generate a long-lived
  token"). It is the only secret the workflows reference, and only in the `Run worker` step.
  `ANTHROPIC_API_KEY` must never be set there: an API key outranks `CLAUDE_CODE_OAUTH_TOKEN` in
  Claude Code's credential order and would bypass the subscription. The token cannot open Remote
  Control sessions or fetch claude.ai connectors; it only makes model requests, which is all the
  worker needs. `--bare` mode ignores it, and the worker does not use `--bare`.
- To rotate or revoke: generate a new token with `claude setup-token` and replace the secret.
  The docs say how to renew a login (`/login`, restart with a new token) but this setup could not
  confirm a documented command that revokes one specific `setup-token` token. Treat the
  revocation route as unverified: after a suspected leak, replace the secret at once, and
  review and remove the Claude Code or API sessions and authorizations on the owner's claude.ai
  account (Settings) if the account offers it. Do not assume deleting the repository secret
  invalidates the token itself.
- Keep Actions workflow permissions at read-only for the repo and do not add other secrets
  that the dispatched workflows could reach. Branch protection on `main` is still required
  before phase 4.

## What phase 3 does not do

- Every category is forced to T2 at integration. Nothing auto-merges.
- The spec ambiguity check is still a stub. It prints that it is not implemented and never blocks.
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
- The entrypoint's own git calls run without the OAuth token or any API key (their environment is
  built from the policy allowlist, which refuses names that look like credentials), with hooks disabled.
- `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB=1` is set on the worker step. Per the environment variable
  reference it strips credentials from the environment of what Claude Code spawns (Bash tool,
  hooks, stdio MCP servers); it needs Claude Code 2.1.251 or later and the workflow pins
  2.1.311. The docs say the scrub recognises a credential by variable name or value shape and
  name `ANTHROPIC_API_KEY` as an example; they do not name `CLAUDE_CODE_OAUTH_TOKEN`. Its name
  contains `TOKEN`, so it is probably removed, but that is not documented, so do not rely on it. The scrub does
  not protect the token from worker code that can read it another way (see Known limits).
- Local-side checks on anything a runner sends back (strict `result.json`, patch path and mode
  checks, the deny-list above, size caps, gate verdict parsing that needs exactly one final
  verdict line) catch accidents, malformed output and naive forgery. They are not protection
  against a hostile worker. The same goes for `gates.sh`'s trusted-base check: it stops a
  worker accidentally or casually editing gate files, nothing more.
- Workers are launched with `--max-budget-usd` set to the remaining budget, but in sandbox mode
  the runner's cost report is only a number the runner sent back. A timed-out worker or unknown
  cost is charged the rest of the per-issue budget and the row records `cost_known: false`.
  Under subscription auth nothing is billed per token. The CLI reference says `--max-budget-usd`
  checks Claude Code's client-side cost estimate, which can differ from a bill, and the same
  estimate is what `total_cost_usd` reports, so under a subscription both are notional
  API-price-equivalent figures. A public issue report describes a Max subscription run stopped by
  `--max-budget-usd` while the usage screen showed nothing spent. The policy budgets are therefore
  a guard on estimated usage, not on money, and they are unchanged.
- A requeued issue gets a fresh worktree and branch (`factory/N-slug-a2`); branches are never deleted.

## Known limits

- The subscription OAuth token is exposed to worker code by design. It is in the worker step's
  process environment and readable through `/proc` whatever the subprocess scrub does, and runners
  have open network egress. Worker code can read it and send it anywhere. A leaked token lets
  its holder use the owner's Claude subscription for up to a year, until it is revoked (the
  revocation route is unverified, see owner setup). There is no per-token spend cap. The subscription's
  own usage limits are the only cap, and a leaked token can also use up the owner's own allowance, so the
  owner's interactive Claude use can be starved. Treat the token as burnable: replace it on a
  schedule and after any suspected leak, and consider a separate account for the factory if the
  plan allows it. The per-issue and per-day budgets in the policy are accounting based on
  estimates the runner reports and can be forged.
- The checks are independent hurdles, not proof. A gate `PASS`, the revert check and the sealed run
  all execute branch code on the same VM that writes the file reporting the result
  (`gates-output.txt`, `verify.json`), so a hostile change can forge any of them. The model
  verifier runs no branch code, but it reads attacker-influenced text (the diff, the issue) and can
  be prompt-injected into AGREE. The sealed tests are written by a model that read the untrusted
  issue. Each check can be wrong or fooled; agreement of all three is evidence, not a guarantee.
  Everything is T2 and a person reviews it.
- Sealed-test exposure: the bundle travels as a `workflow_dispatch` input of a public repo, which
  anyone can see on the run page once the verify run is dispatched (after the build, so it
  cannot help that attempt's builder, but it is public afterwards). The sealed author's run and its
  artifact also exist for three days in a public repo. Downloading the artifact needs a GitHub login
  and the worker's read-only token cannot do it, but the exposure is real.
- Local mode keeps the sealed store in `state_dir` on the same machine as the unsandboxed builder;
  only the canary notices a builder that reads it.
- The verifier's read-only `git diff`, `git log`, `git show` patterns still accept flags such as
  `--output=<file>`. A file written that way makes the collected patch non-empty, which counts as
  disagreement and is dropped, but the write itself happens on the disposable runner.
- Verdicts from the model verifier are truncated with the worker's result text (20,000 characters);
  a verdict that falls outside is read as disagreement.
- Result and patch contents are untrusted data. A well-formed lie (a forged cost, a patch that
  does something unwanted inside the allowed paths) passes the local checks.
- Worker code runs on the same runner as the later steps (entrypoint, artifact upload) and can
  modify files there, including action code, after the token is in scope. The blast radius is one
  disposable runner and one revocable token. Passwordless sudo and open egress are not removed: no
  documented way to drop sudo on `ubuntu-latest` was found, and an egress allowlist
  (step-security/harden-runner in block mode) was not added because its endpoint format and
  the endpoint set that GitHub's own artifact upload needs could not be verified without
  running it. It is a candidate follow-up, tested on a real run.
- If a dispatched run never appears in `gh run list` within the queue timeout, there is no run
  id to cancel. The operator side reports a timeout, but that run may still start later and
  consume runner minutes and subscription usage against the token. The branch it would work on is not
  applied locally.
- Queue time (30 minutes for a run to appear and start) and run time (`sandbox.timeout_minutes`
  once started, shipped as 75 against the workflow's 60 minute cap) are limited separately.
- `GITHUB_TOKEN` is read-only and checkouts do not persist it. The repo is public, so its
  contents are not secret.
- `local` mode is unsandboxed: a worker can execute arbitrary code as the operator. Use it for
  development only. Phase 4 must refuse autonomy for rows whose `sandbox` is not `actions`.
- Artifacts are kept 3 days. The operator side deletes its downloaded copy after each use.
