# Upstream Sync — bmad v6.9.0 → v6.10.0

Synced 2026-08-23. Full subsystem port executed from the eight plans in
`docs/archive/2026-07-29-bmad-v6.10-*.md` (archived 2026-09-22 once all eight
plans landed — see `docs/archive/2026-07-29-bmad-v6.10-sync-index.md`). Unlike
the v6.9.0 targeted port, this sync adopts
upstream's `SKILL.md` + `customize.toml` skill format, landing it alongside the fork's existing
`workflow.yaml` / `instructions.xml` agents rather than replacing them.

**True delta: 24 commits** (`d3abb6da` → `081e64ee`). The plan index claimed 132 commits spanning
v6.6.0 → v6.10.0; that baseline was wrong — the trunk was already at v6.9.0. Plans were
re-baselined before execution.

## Ported

- **Plan A — Phase-4 implementation loop** (#2506, #2508, #2519, #2521, #2522, #2536, #2543) —
  `team/workflows/implementation/quick-dev/` and `dev-auto/`, the canonical Phase-4 loop and its
  automated variant. Resolves the `bmad-dev-auto` item deferred in the v6.9.0 sync.
- **Plan B — core-8 skill consolidation** (#2603, #2608, #2611) — new `team/core-skills/` root
  carrying `bmad-review` (merged editorial lenses), `bmad-deep-recon` (research-trio consolidation),
  and `v6-shims/` mapping legacy skill ids onto the consolidated tree.
- **Plan C — review layers** (#2507, #2523, #2526) — normalized review-layer invocation, hardened
  triage severity calibration, Blind Hunter project access, plus project-level overrides via
  `team/custom/`.
- **Plan D — new skills** (#2492, #2417, #2378, #2385, #2413, #2513) — `bmad-forge-idea`,
  `bmad-spec`, `bmad-prd`, `bmad-ux`. Resolves `bmad-forge-idea` deferred in v6.9.0.
- **Plan E — party mode** (#2530, #2484, #2539, #2531) — `team/core-skills/bmad-party-mode/`
  with the anti-consensus club and point-to-point agent-team sync.
- **Plan F — elicitation expansion** (#2515) — adds `Map Is Not the Territory` and `Subtraction`
  (methods 70–71). Note #2062's +19 methods already landed in the v6.9.0 sync; the port was
  reconciled as a superset rather than an overwrite.
- **Plan G — edge-case hunter** (#2524, #2525) — verified as a no-op: both the named-set
  generalization pass (the "implicit branches" bullet) and the folded deletion audit
  (`## Step 3: Deletion check`) were already present via Plan B/C. No changes needed.
- **Plan H — deprecations** (#2641) — removed `team/workflows/implementation/dev-story/`; all live
  references retargeted to `implementation/quick-dev/`. See divergences below.

## Deliberate divergences from upstream

- **`create-story` retained** (upstream removed it in #2641). It is the sole producer of
  `{story_key}.md` and seeds the `sprint-status.yaml` entries that `quick-dev` only *updates*
  (`quick-dev/sync-sprint-status.md` warns and stops when an entry is absent). `bmad-spec` writes
  `stories.yaml` into a spec folder and never touches `{implementation_artifacts}`, so it is not a
  replacement. `oracle.md` hard-gates on story files existing. Upstream could drop it because its
  agents moved to the skill/`customize.toml` architecture; this fork's XML agents did not.
- **`bmad-investigate` retained** (upstream retired it in #2509). The fork's
  `team/workflows/implementation/investigate/` is wired into fork-specific callers upstream never
  had: `quick-flow/quick-spec` (`step-02-investigate`), `maestro/issue-triage`,
  `ml/evaluation-methodology`, and `dev.md`.
- **`automator`** — never existed in this fork, so #2532's deprecation was a no-op. Upstream's
  replacement is `bmad-loop` (#2545), not `dev-auto`.

## Fixes applied during the port

- **CRLF normalization.** The Plan F branch had introduced CRLF line endings into
  `advanced-elicitation/methods.csv` and the core-skills copy. Upstream uses LF and no other CSV
  under `team/` uses CRLF. Both normalized; the core-skills copy is now byte-identical to upstream.
- **Handler-attribute correction.** `dev-story` used the legacy `workflow.yaml` format
  (`handler type="workflow"`); `quick-dev` is the new skill format (`handler type="exec"`).
  Agent menu items had to change *attribute*, not just path — a path-only swap would have broken
  handler dispatch silently.

## Resolved — `quick-dev` name collision

Resolved 2026-08-23 by the consolidation in
`docs/plans/2026-08-23-bmad-skill-consolidation.md`. `quick-flow/quick-dev` was
retired; `implementation/quick-dev` is canonical and `/team:quick-dev` points at
it. `/team:dev-story` was removed; `dev-story` survives as a fuzzy-match alias in
the `dev` and `oracle` menus.

## Deferred

- **v6.10.0 → v6.11.0 (123 commits).** Not ported. Includes the agent menu consolidations
  (`bmad-deep-recon` wiring for MR/DR/TR/TS/CR/UV, `bmad-prd`, `bmad-build`, `bmad-architecture`,
  `bmad-ux`), the `python3` → `uv run` resolver switch, the `bmad-review` lens "Claims check"
  (Step 4), and upstream's move of agent skills into a flat `src/bmm-skills/agents/` directory.
- **Upstream's agent architecture.** Upstream agents are `SKILL.md` + `customize.toml` resolved by
  `resolve_customization.py`. This fork's agents remain XML personas in `team/agents/*.md`. Only 5
  of 28 agents have any upstream counterpart (analyst, architect, dev, pm, ux-designer).

To review the remaining gap, run `bash scripts/sync-upstream.sh --diff`.
