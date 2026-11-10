# Consolidation Tier B — "config that lies" — Design

**Date:** 2026-09-22 · **Status:** approved · **Companion:** Tier A (`chore/consolidation-a`, deletions) · **Source:** repo consolidation audit 2026-09-22

## Problem

Five places where what the repo *says* and what it *does* disagree:

1. **Customization loader** (`_bmad/scripts/config_utils.py`) requires `_bmad/config.toml` (does not exist) and reads overrides from `_bmad/custom/`, while `team/custom/README.md` and 12 `customize.toml` headers document `team/custom/`. `resolve_config.py`, `resolve_party.py`, `resolve_personas.py` silently fall back on every call.
2. **`.agents/config.yaml` `coordination:`/`orchestrator_integration:`** — 14 keys, zero code readers. `heartbeat.sh` hardcodes 20; `agent-coordinator.md` hardcodes "10 minutes".
3. **Context output path** — `scripts/context/context-config.yaml` and 5 generators default to `_bmad-output/context`; 13 docs and `hooks/post-commit-context.sh` say `output/context`.
4. **Tests** — 164 pytest tests + 7 bash harnesses, no single command; `scripts/release.sh` preflight runs 4 harnesses and 0 pytest.
5. **Install vs update** — `scripts/setup.sh` and `scripts/team-update.sh` maintain separate copy lists; updates never deliver coordination/instinct hooks, `slim-prompt.sh`, or `.agents/config.yaml`; `.claude/settings.local.json` registers 9 hooks, `templates/settings.local.json.template` 6.

## Design

### B1 — Customization loader
- `load_central_config`: `_bmad/config.toml` becomes optional (`required=False`); add `team/config.toml` and `team/custom/config.toml` layers after the `_bmad` ones (later wins).
- `load_customization`: override dirs become `[project_root/"team"/"custom", project_root/"_bmad"/"custom"]` — `team/custom` wins; both optional.
- Update the 12 `customize.toml` header comments and `team/custom/README.md` (remove the "TODO: loader" line).
- Tests: `_bmad/scripts/tests/test_config_utils.py` — override in `team/custom/<skill>.toml` is applied; missing `_bmad/config.toml` does not raise.

### B2 — Coordination config is read or removed
- Generalize `scripts/instincts/config.py` into `scripts/lib/config.py` with `load(root, section, defaults) -> dict`; `scripts/instincts/config.py` becomes a thin wrapper (`load(root)` → `lib.load(root, "instincts", DEFAULTS)`), keeping its CLI and all existing tests green.
- `heartbeat.sh` reads `heartbeat_interval_calls` via `python3 scripts/lib/config.py --root R --section coordination heartbeat_interval_calls` (default 20 if python3/config missing).
- `claude-commands/team/agent-coordinator.md` step "older than 10 minutes" → "older than `coordination.stale_threshold_minutes` from `.agents/config.yaml` (default 10)".
- Delete keys with no reader after this change: `claim_conflict_action`, `claim_path_matching`, `auto_worktree`, `cleanup_orphaned_worktrees`, `decision_sync_on_startup`, `decision_sync_interval_calls`, `request_check_interval_calls`, and the whole `orchestrator_integration:` block — unless a prompt file references the key by name (grep before deleting; a prompt reference counts as a reader and the key stays, with the prompt told to read it).
- Keep `worktree_base_dir`, `branch_prefix` only if `agent-coordinator.md` names them (same rule).

### B3 — One context output path
- `scripts/context/context-config.yaml` (and `.example.yaml`): `output_dir: "output/context"`.
- `generate_all.py`: the fallback default becomes `output/context`; the 5 `gen_*.py` `main()` blocks resolve the dir through `generate_all`'s loader instead of a literal (or, minimal: change the 5 literals to `output/context` and add a comment pointing at the config).
- `docs/CUSTOMIZATION.md` / `README.md`: no change needed (already say `output/context`); `scripts/migrate-to-team.sh` untouched (historical one-shot).

### B4 — One test command
- `scripts/test.sh`: runs `python3 -m pytest -q` from repo root, then every `.agents/hooks/test-*.sh` and `scripts/test-*.sh`; prints one summary line; exit non-zero on any failure.
- `scripts/release.sh` preflight: replace the four hard-coded harness lines with `bash "$REPO_ROOT/scripts/test.sh"`.
- Document in `docs/ARCHITECTURE.md` (Testing) and `README.md` (one line).

### B5 — Shared install manifest + drift check
- `templates/install-manifest.txt`: one entry per line, `mode<TAB>src<TAB>dst`, `mode ∈ {copy, init, exec}` (`copy` = overwrite; `init` = copy only if absent; `exec` = copy + chmod +x). Covers: `.claude/hooks/{check-for-updates,slim-prompt}.sh`, `hooks/post-commit-context.sh → .claude/hooks/`, `.agents/hooks/{worktree-guard,claim-check,heartbeat,lib-identity,observe,instinct-mine,instinct-inject}.sh`, `scripts/instincts/*.py`, `scripts/lib/config.py`, `scripts/context/*.py` + `context-config.example.yaml`, `scripts/{team-update,team-check,test}.sh`, `.agents/config.yaml` (init), `templates/settings.local.json.template → .claude/settings.local.json` (init).
- `scripts/lib/install-manifest.sh`: `apply_manifest SRC_ROOT DST_ROOT [--dry-run]` — expands globs, creates dirs, honors mode, prints one line per file.
- `setup.sh`: its per-file `cp` lines for the items above are replaced by one `apply_manifest` call (the `team/` tree copy, config templating, and `claude-commands` copy stay as they are). `team-update.sh`: the "tooling" section (lines ~325-347) becomes one `apply_manifest "$UPSTREAM_DIR" "$PROJECT_ROOT"` call — `init` entries never clobber a project's `settings.local.json` or `.agents/config.yaml`.
- `templates/settings.local.json.template` gains the coordination hooks (`worktree-guard`, `claim-check`, `heartbeat`) and `slim-prompt.sh` so it matches `.claude/settings.local.json`.
- `scripts/check-settings-drift.sh`: extracts the set of hook commands from both JSON files (python3 one-liner), normalizes `$CLAUDE_PROJECT_DIR`, and fails if the template's set ≠ the local set (ignoring `post-commit-context.sh`, which is template-only by design — list allowed differences in the script). Wired into `scripts/test.sh`.
- Tests: `scripts/test-install-manifest.sh` — scratch SRC/DST, applies the manifest twice, asserts files present, `init` files untouched on second run, `exec` files executable, dry-run writes nothing.

## Non-goals
Generating the settings template (Tier C); merging `team/_memory/_comms` with `.agents/`; generated command loaders.

## Rollback
Each B-item is one commit; revert individually. B5's manifest is additive — the old `cp` lines are removed only after the manifest test passes.
