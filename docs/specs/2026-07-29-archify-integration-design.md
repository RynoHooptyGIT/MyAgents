# Archify Integration Design

**Date:** 2026-07-29
**Status:** Approved
**Target release:** v7.6.0
**Upstream:** [tt-a1i/archify](https://github.com/tt-a1i/archify) @ `7b49d0b715fd4ba48116bcdecd1ba3789a279613` (skill v2.12)

## Goal

Vendor upstream Archify skill and wire it into four in-repo agents so that architecture, data-flow, sequence, and documentation-embedded diagrams can be generated as validated standalone HTML directly from agent menus.

## Scope

**In:** Vendor skill payload, add one diagram menu item per agent (architect, data-architect, api-contract, tech-writer), bump `VERSION` to 7.6.0.

**Out:** Global (`~/.claude/skills/`) installation, DevOps agent wiring, generation of any sample diagrams as part of this change, upstream contributions, root-level `package.json` changes.

## Non-Goals

- Introducing a subtree or submodule for upstream sync (plain vendored copy with `.upstream` marker is sufficient for the current cadence).
- Modifying the Archify skill's authoring invariants — we surface the skill as-is; agents defer to `skills/archify/SKILL.md` for authoring rules.

## Design

### Skill Vendoring

Copy the upstream `archify/` skill payload (from `archify.zip` at the pinned commit) to `skills/archify/`. The payload is self-contained: `SKILL.md`, `bin/archify.mjs` (Node.js CLI), `renderers/`, `schemas/`, `examples/`, `references/`, `recipes/`, `scripts/`, `assets/`, `delta/`, `package.json`, `LICENSE`. This mirrors the existing `skills/integration-review/` layout convention (skill-per-directory).

A `skills/archify/.upstream` marker file records the source repo, commit SHA, and skill version so future re-syncs are trivial.

### Runtime Dependency

Archify requires **Node.js ≥ 18** to invoke `node bin/archify.mjs`. No package.json changes at repo root; the skill vendors its own manifest. Verification commands:

```bash
node skills/archify/bin/archify.mjs doctor
node skills/archify/bin/archify.mjs demo /tmp/archify-demo
```

### Agent Wiring

Each of the four target agents gets a new BMAD-style menu item + matching prompt block. Pattern per agent:

```xml
<item cmd="DG or fuzzy match on diagram" action="#archify-diagram">[DG] Generate <flavor> Diagram (archify)</item>
```

Matching `<prompt id="archify-diagram">` instructs the agent to:

1. Load `{project-root}/skills/archify/SKILL.md` for the fast-authoring path.
2. Default `type` per agent (architect → `architecture`, data-architect → `dataflow`, api-contract → `sequence`, tech-writer → user-chosen).
3. Follow the SKILL.md contract exactly: set `meta.quality_profile: "showcase"`, run `node skills/archify/bin/archify.mjs validate <type> <candidate>.json --quality showcase --json` before `deliver`, treat a passing `deliver` as freezing the spec.
4. Write output HTML under `{output_folder}/diagrams/<name>.html`.

Menu code `DG` is verified unused across all four target files before insertion.

### Version Bump

`VERSION` file: `7.5.0` → `7.6.0`. Minor bump per additive-feature convention. No root-level `CHANGELOG.md` exists — commit message carries the release note.

## Verification

After implementation:

1. `node skills/archify/bin/archify.mjs doctor` — expect clean exit.
2. `node skills/archify/bin/archify.mjs demo /tmp/archify-demo` — expect HTML written.
3. Per agent file: XML remains balanced (`</menu>` count = 1, `</prompts>` count = 1).
4. Per agent file: new menu item's `action` id matches a `<prompt id>` in the same file.

## Files Touched

- **Create:** `skills/archify/**` (vendored payload, ~40 files)
- **Create:** `skills/archify/.upstream`
- **Modify:** `team/agents/architect.md`
- **Modify:** `team/agents/data-architect.md`
- **Modify:** `team/agents/api-contract.md`
- **Modify:** `team/agents/tech-writer.md`
- **Modify:** `VERSION`
- **Create:** `docs/specs/2026-07-29-archify-integration-design.md` (this file)

## Rollback

Revert the release commit. Vendored skill directory can be removed with `rm -rf skills/archify`; agent menu items removed by reverse-edit. No shared state or migrations involved.
