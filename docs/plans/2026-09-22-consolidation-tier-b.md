# Consolidation Tier B Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use `- [ ]` syntax.

**Goal:** Make five config/install surfaces truthful: customization overrides load from `team/custom/`, coordination config is read (or removed), one context output path, one test command in release preflight, one install manifest shared by setup and update with a settings-drift check.
**Spec:** `docs/specs/2026-09-22-consolidation-tier-b-design.md` — read it; each task below names its spec section and the spec text is the requirement.
**Tech:** bash, Python 3.8+ stdlib (TOML via existing `config_utils.load_toml`), pytest, bash harnesses in the `.agents/hooks/test-*.sh` style.

## Global Constraints
- Every existing test stays green: `python3 -m pytest -q` (≥164) and all `.agents/hooks/test-*.sh` + `scripts/test-*.sh`.
- Hooks keep their contract: exit 0 always; `heartbeat.sh` must still work with no python3 (default 20).
- No behaviour change for a project whose `_bmad/custom/` overrides exist — `team/custom/` wins only when both are present.
- Commit per task; message ends with `Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>`.
- Work in `.worktrees/consolidation-b` on `chore/consolidation-b`; never checkout/switch; stage explicit paths.

### Task 1: Customization loader (spec B1)
Files: modify `_bmad/scripts/config_utils.py`, `team/custom/README.md`, the 12 `customize.toml` headers (`grep -rl '_bmad/custom' --include=customize.toml`); create `_bmad/scripts/tests/test_config_utils.py`.
- [ ] Test (tmp project): `team/custom/<skill>.toml` override applied; `_bmad/custom/<skill>.toml` still applied when alone; both present → `team/custom` wins; `load_central_config` on a tree with no `_bmad/config.toml` returns a dict, no raise.
- [ ] Run → fail. Implement per spec B1. Run → pass. `python3 _bmad/scripts/resolve_config.py --project-root . --key agents` no longer errors.
- [ ] Update headers/README. Commit `fix(config): customization overrides load from team/custom; central config optional`.

### Task 2: Coordination config read or removed (spec B2)
Files: create `scripts/lib/__init__.py`, `scripts/lib/config.py`, `scripts/lib/tests/test_config.py`; modify `scripts/instincts/config.py` (thin wrapper), `.agents/hooks/heartbeat.sh`, `.agents/hooks/test-heartbeat.sh`, `claude-commands/team/agent-coordinator.md`, `.agents/config.yaml`, `docs/specs/2026-04-26-multi-agent-coordination-design.md` (note which keys were removed and why).
- [ ] Tests for `lib.config.load(root, section, defaults)`: section parsing, defaults, bool/int/float coercion (port the four instinct config tests to the generic loader); `scripts/instincts/tests/test_config.py` unchanged and green through the wrapper.
- [ ] `heartbeat.sh`: `INTERVAL="$(python3 "$COORD_ROOT/scripts/lib/config.py" --root "$COORD_ROOT" --section coordination heartbeat_interval_calls 2>/dev/null || echo 20)"; case "$INTERVAL" in ''|*[!0-9]*) INTERVAL=20;; esac` and `-lt "$INTERVAL"`. Harness: add a case with `heartbeat_interval_calls: 3` in a temp `.agents/config.yaml` → stamps on the 3rd call.
- [ ] Grep every remaining `coordination:`/`orchestrator_integration:` key name across `team/ claude-commands/ .agents/hooks/ scripts/`; delete keys with zero hits; keep + document the rest. Update `agent-coordinator.md` stale wording.
- [ ] Commit `refactor(config): generic section loader; heartbeat reads interval; drop unread coordination keys`.

### Task 3: One context output path (spec B3)
Files: `scripts/context/context-config.yaml`, `context-config.example.yaml`, `generate_all.py`, `gen_{api_index,module_index,patterns,schema_digest,sprint_digest}.py`.
- [ ] Test: `python3 scripts/context/generate_all.py --check` (or a dry-run flag if present) resolves to `output/context`; `grep -rn '_bmad-output' scripts/context/` → 0 hits after the change.
- [ ] Implement per spec B3. Commit `fix(context): single output path output/context`.

### Task 4: One test command (spec B4)
Files: create `scripts/test.sh`; modify `scripts/release.sh` (preflight block lines ~72-77), `docs/ARCHITECTURE.md`, `README.md`.
- [ ] `scripts/test.sh` runs pytest then every harness; summary line `TESTS: pytest <n> passed · harnesses <k>/<k> green`; non-zero on any failure. Verify by running it; then temporarily break a harness in a scratch copy to confirm non-zero (do not commit the break).
- [ ] `release.sh` preflight calls `scripts/test.sh`. Commit `chore(test): scripts/test.sh runs everything; release preflight uses it`.

### Task 5: Shared install manifest + drift check (spec B5)
Files: create `templates/install-manifest.txt`, `scripts/lib/install-manifest.sh`, `scripts/check-settings-drift.sh`, `scripts/test-install-manifest.sh`; modify `scripts/setup.sh`, `scripts/team-update.sh`, `templates/settings.local.json.template`, `scripts/test.sh` (add drift check), `docs/ARCHITECTURE.md` (install section).
- [ ] Write `scripts/test-install-manifest.sh` first (scratch SRC/DST; apply twice; assert copy/init/exec semantics; dry-run writes nothing) → fails.
- [ ] Implement manifest + `apply_manifest`; harness passes. Replace the per-file `cp` lines in `setup.sh` and the tooling block in `team-update.sh` with `apply_manifest`; `bash -n` both; run `bash scripts/setup.sh <scratch>/proj` with piped defaults and assert the manifest files landed (hooks executable, `.agents/config.yaml` present, `settings.local.json` parses).
- [ ] Bring the template's hook list up to the local one (+`slim-prompt`, `worktree-guard`, `claim-check`, `heartbeat`); write `check-settings-drift.sh` with an explicit allow-list (`post-commit-context.sh` template-only); wire into `scripts/test.sh`; verify it passes now and fails when a hook is removed from the template in a scratch copy.
- [ ] Commit `feat(install): shared install manifest for setup/update; settings drift check`.

### Finish
`bash scripts/test.sh` green; `bash scripts/release.sh --help`/dry-run unaffected; hand off via finishing-a-development-branch (PR against main; expect a trivial `setup.sh` conflict with Tier A's cosmetic commit).
