# bmad Skill Consolidation — Design

**Date:** 2026-08-23
**Status:** Approved for planning
**Branch:** `integration/bmad-v6.10`

## Problem

The v6.10.0 port landed nine bmad skills into the fork but wired none of them. Every ported skill
has a live legacy counterpart, and **nothing in `team/agents/` or `claude-commands/` references any
ported skill** — the sole exceptions are four references to `implementation/quick-dev` added during
the Plan H `dev-story` retirement.

The result is a dormant parallel tree beside the live one. Two implementations of review, PRD, UX,
spec, research, elicitation, party-mode, and quick-dev; one reachable, one not.

**Goal:** one tree. Adopt the ported skills as canonical, retire the legacy workflows they replace.

## Blocker: missing Python infrastructure

The ported skills cannot run as they stand. They invoke eight Python scripts, none present in the
fork, across 37 shared call sites. Only one file anywhere carries fallback prose for a missing
script. This is the infra the v6.9.0 sync explicitly deferred; the v6.10.0 port brought the skills
without it.

| Script | Lines | Scope | Call sites |
|---|---|---|---|
| `memlog.py` | 224 | shared | 21 |
| `resolve_customization.py` | 99 | shared | 10 |
| `resolve_config.py` | 82 | shared | 6 |
| `config_utils.py` | 119 | shared (imported by the above) | — |
| `resolve_party.py` | 282 | `bmad-party-mode` | 3 |
| `recon_kit.py` | 322 | `bmad-deep-recon` | — |
| `pick_methods.py` | 233 | `bmad-advanced-elicitation` | — |
| `resolve_personas.py` | 275 | `bmad-forge-idea` | — |
| `word_metrics.py` | 102 | `bmad-review` | 1 |

Mitigating facts:

- **Python is already a runtime dependency.** `team/agents/oracle.md` shells out to
  `scripts/context/generate_all.py` during activation.
- **`uv` is installed** (0.10.11) and is the invocation form upstream uses (`uv run …`).
- **Scripts are stdlib-only** — no third-party packages. `config_utils` is the only internal import.
- **Upstream ships tests for every script**, which we vendor as-is for free verification.
- **`implementation/quick-dev` has zero Python dependencies**, which is why wiring it during Plan H
  was safe. (`dev-auto`'s `foo.py` is an example file path inside sample review output, not a dep.)

## Approach

Vendor the infrastructure, then migrate cluster by cluster.

### Script placement

Vendor at **upstream's exact paths**. The skills reference `{project-root}/_bmad/scripts/*.py`
verbatim in 37 places; matching that path means zero call-site rewriting now and zero on every
future sync. A fork-native `scripts/bmad/` would read more tidily but costs 37 rewrites today and
re-pays that cost at each sync.

```
_bmad/scripts/
  config_utils.py  memlog.py  resolve_config.py  resolve_customization.py
  tests/           4 upstream test files, vendored unmodified

team/core-skills/<skill>/scripts/
  word_metrics.py  pick_methods.py  recon_kit.py  resolve_personas.py  resolve_party.py
  tests/           per-skill upstream tests
```

Per-skill scripts already resolve via `{skill-root}/scripts/`, so they need only to be dropped in.

`render_skill.py`, `brain.py`, and `list_customizable_skills.py` exist upstream but serve skills
this fork has not ported (`bmad-brainstorming`, `bmad-customize`). They are **out of scope**.

### Migration order

Each cluster is one self-contained unit: vendor script → wire agents and commands → retire legacy →
verify. The tree is never left half-migrated. Ordered by blast radius ascending.

| # | Adopt | Scripts | Retire | Refs |
|---|---|---|---|---|
| 0 | shared infra | 4 shared + tests | — | — |
| 1 | `bmad-review` | `word_metrics` | `implementation/code-review` | 5 |
| 2 | `bmad-ux` | — | `planning/create-ux-design` | 6 |
| 3 | `bmad-spec` | — | `quick-flow/quick-spec`, `spec-review` | 5 |
| 4 | `bmad-prd` | — | `planning/prd`, `validate-prd` | 8 |
| 5 | `quick-dev` | — | `quick-flow/quick-dev` | 4 |
| 6 | `bmad-forge-idea` | `resolve_personas` | `innovation-strategy` | 3 |
| 7 | `bmad-deep-recon` | `recon_kit` | `analysis/research` | 6 |
| 8 | `bmad-advanced-elicitation` | `pick_methods` | `advanced-elicitation` | **87** |
| 9 | `bmad-party-mode` | `resolve_party` | `party-mode` | **111** |

**Cluster 1 is the proof cluster.** It exercises every mechanic — shared infra, a per-skill script,
agent rewiring, slash-command repointing, legacy retirement — while touching only 5 references. If
the pattern does not hold there, work stops with almost nothing changed.

**Clusters 8 and 9 are the risk.** Their reference counts are large but the references are highly
regular — roughly four distinct line shapes repeated mechanically:

```
advancedElicitationTask: '{project-root}/team/workflows/advanced-elicitation/workflow.xml'   ×50
- When 'A' selected: Execute {project-root}/team/workflows/advanced-elicitation/workflow.xml  ×19
partyModeWorkflow: '{project-root}/team/workflows/party-mode/workflow.md'                     ×45
- When 'P' selected: Execute {project-root}/team/workflows/party-mode/workflow.md             ×18
```

These are scripted find/replace, not 87 individual judgment calls. `party-mode` additionally
appears in all 28 agent files, which is why it goes last.

### Handler semantics

Legacy workflows are invoked as `workflow="…/workflow.yaml"` and dispatch through
`team/engine/workflow.xml`. Ported skills are the skill format and must be invoked as
`exec="…/skill.md"` or `exec="…/workflow.md"`.

**The attribute changes, not just the path.** A path-only substitution leaves the item routed to the
`workflow` handler, which will try to load a non-existent YAML. This is the same trap encountered
during the `dev-story` retirement and is the single most likely way to silently break an agent menu.

### Preserving entry points

Retirement moves implementations, not names.

- Slash command **filenames stay**. `/team:code-review` continues to work, repointed at
  `bmad-review`. Each repointed command carries a short note naming its new target.
- Legacy names **stay as fuzzy-match aliases** in agent menus
  (`cmd="CR or fuzzy match on bmad-review or code-review"`).
- Menu codes (`[CR]`, `[PM]`, `[A]`) are unchanged.

Users and muscle memory are unaffected; only the implementation behind the name moves.

**Exception — cluster 5 resolves the `quick-dev` name collision.** Two commands would otherwise
point at `implementation/quick-dev`: `/team:dev-story` (repointed there during Plan H) and
`/team:quick-dev` (currently pointing at the legacy `quick-flow/quick-dev`, which cluster 5
retires). Collapse them: `/team:quick-dev` becomes the canonical command, `/team:dev-story` is
deleted, and `dev-story` survives only as a fuzzy-match alias in the `dev.md` and `oracle.md`
menus. This ends the collision documented in `docs/sync-notes-v6.10.0.md` and leaves one command
per capability.

### Fix in passing

Fifteen files reference `../../../../core/workflows/…`, which resolves to `<repo>/core/` — a
directory that does not exist. These references are already broken and predate the port. Since the
migration touches these same files, repoint them to `{project-root}/team/workflows/…` as part of
whichever cluster owns them.

## Verification

Per cluster, before it is considered done:

1. `uv run` the vendored tests for any script introduced by that cluster.
2. Skill frontmatter: every `skill.md` has exactly two `---` delimiters.
3. Reference integrity: every `references/*.md` linked from a `skill.md` exists.
4. `bash scripts/team-check.sh` returns 0.
5. Dangling sweep: zero path references to the retired workflow outside `docs/plans/`.
6. Handler audit: no menu item points at a `.md` via `workflow=` or a `.yaml` via `exec=`.

Whole-project, at the end: all of the above, plus a manual smoke of one retired entry point per
cluster (e.g. `/team:code-review` still resolves and runs).

## Out of scope

- **`team/workflows/brainstorming/`** — upstream's `bmad-brainstorming` was not ported, so there is
  no replacement. It stays. Not a retirement candidate.
- **`create-story`** and **`implementation/investigate`** — deliberate divergences recorded in
  `docs/sync-notes-v6.10.0.md`. Unaffected.
- **The 6.10.0 → 6.11.0 delta** (123 commits). Adopting this infra makes that sync substantially
  cheaper, but it is separate work.
- **Rewriting the fork's XML agents to upstream's `SKILL.md` + `customize.toml` format.** Only 5 of
  28 agents have any upstream counterpart. Out of scope indefinitely.

## Release

**Nothing ships until this spec is fully implemented.** The v6.10.0 port is deliberately held rather
than released on its own, so consumers never receive the dormant parallel tree. One clean release
follows consolidation.

Target: **7.10.0** (minor). The work adds capability — the `core-skills/` tree, the nine bmad
skills, `quick-dev`, `dev-auto` — and removes `implementation/dev-story`, but every entry point
survives as a command name or menu alias, so nothing a user invokes breaks.

Shipping sequence, once the clusters are done:

1. Fast-forward `main` to `origin/main` (local `main` is a stale divergent line — see
   `docs/sync-notes-v6.10.0.md`), then merge `integration/bmad-v6.10`.
2. `bash scripts/release.sh 7.10.0` — bumps `VERSION`, commits, tags `v7.10.0`, pushes.

Propagation depends on step 2. Downstream projects run `scripts/team-check.sh`, which fetches
`raw.githubusercontent.com/RynoHooptyGIT/MyAgents/main/VERSION` and compares it against their own
`.team-upstream-version`. Equal values mean "up to date" and the `.team-update-available` marker is
removed, so **without the `VERSION` bump reaching `main`, no consumer is notified** regardless of
what else was pushed. The marker is what `oracle.md` activation step 2 reads to show its update
banner.

Note the filename `.team-upstream-version` means different things by position in the chain: here it
records the last **bmad** version synced (`6.10.0`); in a downstream project it records the last
**MyAgents** version synced. Consumers read `VERSION`, not this file.

## Risks

| Risk | Mitigation |
|---|---|
| Handler attribute missed during rewiring | Verification step 6 audits attribute/extension pairing |
| `party-mode` breaks all 28 agents | Goes last; regular reference shapes; cluster is revertible alone |
| Vendored Python drifts from upstream | Vendored unmodified at upstream paths; tests vendored alongside |
| A ported skill has a hidden runtime gap | Proof cluster surfaces it at 5 refs, not 111 |
| `uv` absent on another machine | Scripts are stdlib-only; `python3` fallback works if invocation is adjusted |
