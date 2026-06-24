# Upstream Sync — bmad v6.8.0 → v6.9.0

Synced 2026-06-24. Targeted high-value port: structurally-compatible, high-impact changes
adapted into the fork's `team/workflows/<name>/` layout (workflow.yaml/instructions.md/workflow.md +
steps). Upstream's v6.9.0 shifted several skills onto a new `SKILL.md` + Python-infra platform
(`memlog.py`, `brain.py`, `resolve_party.py`, `customize.toml`, HTML composers); those pieces are
**deferred** rather than re-architected into this fork.

## Ported

- **Advanced elicitation +19 techniques** (upstream #2062) — appended methods 51–69 to
  `team/workflows/advanced-elicitation/methods.csv` (now 69 total). New `framing` category added.
- **Sprint-status retrospective action items** (upstream #2465) — full producer→consumer chain:
  - `implementation/retrospective/instructions.md` — appends agreed action items to an
    `action_items` section in sprint-status.yaml; updates prior-epic entries from Step 4 follow-through.
  - `implementation/sprint-status/instructions.md` — parses/validates `action_items`, surfaces open
    ones in summary + data mode (`open_action_items`).
  - `implementation/sprint-planning/{instructions.md,checklist.md,sprint-status-template.yaml}` —
    preserves the `action_items` section on regeneration; adds status definitions + example.
- **Party mode** (upstream #2441, #2484) — into `team/workflows/party-mode/`:
  - Stronger conversation-first "Keep It Feeling Like a Party" bar (clash-don't-resolve, single
    woven exchange, pull the user in, let history form).
  - Formalized run modes: `session` / `auto` / `subagent` / `agent-team`.
  - Persistent per-party memory at `team/_memory/party-mode/{party}/.memlog.md` (agent-maintained
    markdown memlog, read-on-entry/top-up-on-exit). NO Python memlog.py — adapted to fork conventions.
- **Brainstorming** (upstream #2445) — three facilitation modes (Facilitator / Creative Partner /
  Ideate For Me) selected up front in `brainstorming/steps/step-01-session-setup.md`, described in
  `brainstorming/workflow.md`. Infra-free adaptation (no brain.py/memlog.py).

## Deferred (need upstream's new SKILL.md + Python-infra platform)

- New skills: `bmad-dev-auto` (#2500), `bmad-architecture` lean spine (#2467, #2475),
  `bmad-forge-idea` (#2492).
- Shared `memlog.py` (#2462, #2483) and the per-skill Python tooling
  (`resolve_party.py`, `brain.py`, HTML selectors/composers, `customize.toml`).
- Brainstorming method-data expansion (`assets/brain-methods.csv` / `analysis/method-matrix.csv`).
- Installer / docs / web-bundles changes — not applicable to this fork.

To revisit deferred items, re-run `scripts/sync-upstream.sh --diff` against the relevant
`src/{core,bmm}-skills/` paths.
