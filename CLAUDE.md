# Project Instructions

## Multi-Agent Coordination

This project uses the multi-agent coordination protocol. When running as one
of multiple simultaneous Claude instances:

1. Always run `/agent-coordinator` before beginning work
2. Always run `/agent-shutdown` before ending your session
3. Never operate in the main repo checkout — use your assigned worktree
4. Check `.agents/decisions/` before making architectural choices
5. Write decisions that affect other agents to `.agents/decisions/`
6. Respect file ownership — do not edit files claimed by other agents

### Coordination Files

- `.agents/registry/` — who's running (don't edit manually)
- `.agents/claims/` — who owns what files (don't edit manually)
- `.agents/decisions/` — architectural decisions (read before designing)
- `.agents/requests/` — inter-agent requests
- `.agents/status/` — per-agent progress
- `.agents/config.yaml` — coordination settings

## Oracle Awareness

When Athena (Oracle) has been activated in this session via `/team:oracle`, maintain ambient monitoring after every tool result. Evaluate output for errors, completions, security signals, and user frustration. Respond according to the current oracle mode:

- **suggest** (default): One-line nudge at pause points when problems are detected
- **auto**: Invoke the matching skill or agent immediately
- **off**: Silent — only respond to direct commands

Mode toggles: `oracle auto` | `oracle suggest` | `oracle off` | `oracle status`

Fix triggers: `fix it` (plan + approval) | `just fix it` (auto-execute)

Instincts: learned behaviors mined from sessions (`python3 scripts/instincts/instinct.py status --json`). Pending ones are surfaced per mode — suggest lists them, auto accepts ≥ `auto_accept_confidence`, off stays silent. Instincts are context, not policy.

## Gates

What gates this repo:

- `bash scripts/test.sh` must pass (pytest, hook harnesses, apply-contract, settings drift).
- CI (`.github/workflows/ci.yml`) runs it on every pull request and on pushes to `main`.
- The software factory design is in `docs/specs/2026-11-10-software-factory-design.md`.

The multi-tenant product gates (tenant, ledger, alembic) are a template for target
projects: `templates/product-gates/GATES.md`.
