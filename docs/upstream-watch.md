# Upstream watch

A weekly GitHub Action (`.github/workflows/upstream-watch.yml`) keeps this repo current with BMAD-METHOD and registered plugins. You review PRs; you don't run scripts.

## What it does each Monday

1. Fetches BMAD and lists every non-merge commit since `.team-last-sync-tag`.
2. Classifies each commit against `scripts/upstream/manifest.json`:

   | Status | Meaning | Action |
   |---|---|---|
   | ported | applied cleanly, tests passed | in the PR, one commit each |
   | already-present | change is already here | ledger only |
   | not-applicable | touches nothing this repo carries | ledger only |
   | structural | ticket store, Sofia, rendering, migration and similar | listed for a decision, never auto-ported |
   | conflict | patch does not apply | listed for a hand port |
   | clean | applies, but it is a feature, not a `fix`/`perf` | listed for review |
   | test-failed | applied, broke tests | rolled back, listed |

3. Opens one PR with the ported commits (at most `max_apply`, default 10), plus any `plugins/registry.json` updates from `scripts/plugin-sync.sh`.
4. Updates one open issue, "Upstream sync backlog", with everything that needs a human.

It never merges. While an `upstream/auto-*` PR is open it only refreshes the issue.

## Setup, once

Repo Settings → Actions → General → Workflow permissions: allow read and write, and tick "Allow GitHub Actions to create and approve pull requests". Without it the PR step fails.

## Run it by hand

```bash
python3 scripts/upstream/watch.py scan                    # classify only, changes nothing
python3 scripts/upstream/watch.py apply --max 5           # port in the current checkout
```

Or trigger the workflow from the Actions tab (`workflow_dispatch`).

## Why the baseline doesn't move

`.team-last-sync-tag` stays put. Advancing it past unported structural commits would hide them. Settled commits are tracked in `.team-upstream-ledger.json` instead, which the PR updates. Close a PR without merging and its commits come back next week.

## Adding an upstream

Add an entry to `upstreams` in the manifest: remote name and URL, branch, a baseline file holding the last-synced SHA, the `path_map` from upstream paths to local ones, and the `structural_pattern` and `auto_port_pattern` regexes. Plugins are synced separately through `plugins/registry.json`.

## Limits

- Classification checks each patch against the current tree, so a commit whose file was changed by a later local edit shows as a conflict.
- A commit that touches both mapped and unmapped files ports only the mapped part.
- Tests run after each port: `_bmad/scripts/tests` and `team/core-skills`. Change `test_cmd` in the manifest to widen that.
