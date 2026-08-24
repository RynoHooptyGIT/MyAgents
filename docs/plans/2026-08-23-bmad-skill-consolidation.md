# bmad Skill Consolidation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the nine ported bmad skills the canonical implementations and retire the legacy workflows they duplicate, so the fork has one tree instead of a live tree beside a dormant twin.

**Architecture:** Vendor the missing Python infrastructure at upstream's exact paths so no call site needs rewriting, then migrate one cluster at a time — wire agents and commands to the ported skill, retire its legacy counterpart, verify — smallest blast radius first.

**Tech Stack:** Markdown, XML agent definitions, Python 3 (stdlib only), `uv` for invocation.

**Spec:** `docs/specs/2026-08-23-bmad-skill-consolidation-design.md`

## Global Constraints

- **Branch:** all work happens on `integration/bmad-v6.10`. Do not touch `main` — it is a stale divergent line (see `docs/sync-notes-v6.10.0.md`).
- **Vendor ref:** `bmad/main`. It is the only ref carrying `config_utils.py`, `word_metrics.py`, `pick_methods.py`, and `recon_kit.py`. Three ported skills (`bmad-review`, `bmad-deep-recon`, `bmad-spec`) do not exist at the v6.10.0 tag at all, so their scripts cannot come from there.
- **Vendor unmodified.** Copy scripts byte-for-byte. Do not reformat, relocate, or "improve" them — drift makes future syncs expensive.
- **Shared script path:** `_bmad/scripts/` at repo root, matching `{project-root}/_bmad/scripts/` as referenced in 37 call sites.
- **Per-skill script path:** `<skill-dir>/scripts/`, matching `{skill-root}/scripts/`.
- **Handler rule:** ported skills are invoked with `exec="…/skill.md"`. Legacy workflows used `workflow="…/workflow.yaml"`. **The attribute changes, not just the path.** A `.md` behind `workflow=` silently routes to the YAML engine and fails.
- **Entry points survive.** Slash command filenames stay; legacy names remain as fuzzy-match aliases in agent menus; menu codes (`[CR]`, `[PM]`, …) are unchanged.
- **No release.** Do not bump `VERSION`, tag, or push. Release is a separate step after this plan completes.
- **Commit per task**, message referencing the cluster.

---

## File Structure

**Created:**
- `_bmad/scripts/{config_utils,memlog,resolve_config,resolve_customization}.py` — shared infra
- `_bmad/scripts/tests/test_*.py` — upstream tests, vendored
- `team/core-skills/bmad-review/scripts/word_metrics.py` (+ `tests/`)
- `team/core-skills/bmad-deep-recon/scripts/recon_kit.py` (+ `tests/`)
- `team/core-skills/bmad-forge-idea/scripts/resolve_personas.py` (+ `tests/`)
- `team/core-skills/bmad-party-mode/scripts/resolve_party.py` (+ `tests/`)
- `team/core-skills/bmad-advanced-elicitation/scripts/pick_methods.py` (+ `tests/`)

**Modified:** agent files in `team/agents/`, commands in `claude-commands/team/`, and workflow files carrying `advancedElicitationTask:` / `partyModeWorkflow:` references.

**Deleted:** nine legacy workflow directories, listed per task.

---

## Task 1: Vendor shared Python infrastructure

**Files:**
- Create: `_bmad/scripts/{config_utils,memlog,resolve_config,resolve_customization}.py`
- Create: `_bmad/scripts/tests/test_{config_utils,memlog,resolve_config,resolve_customization}.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `_bmad/scripts/resolve_customization.py --skill <dir> --key <key>`, `_bmad/scripts/memlog.py`, `_bmad/scripts/resolve_config.py`. All ported skills invoke these via `uv run {project-root}/_bmad/scripts/<name>.py`.

- [ ] **Step 1: Create directories**

```bash
mkdir -p _bmad/scripts/tests
```

- [ ] **Step 2: Vendor the four shared scripts**

```bash
for s in config_utils memlog resolve_config resolve_customization; do
  git cat-file -p "bmad/main:src/scripts/$s.py" > "_bmad/scripts/$s.py"
done
ls -l _bmad/scripts/*.py
```

Expected: four files, non-zero size.

- [ ] **Step 3: Vendor their tests**

```bash
for s in config_utils memlog resolve_config resolve_customization; do
  git cat-file -p "bmad/main:src/scripts/tests/test_$s.py" > "_bmad/scripts/tests/test_$s.py"
done
```

- [ ] **Step 4: Run the tests to verify the vendored infra works**

```bash
uv run --with pytest python -m pytest _bmad/scripts/tests/ -q
```

Expected: all tests pass. If imports fail because tests expect a package root, add an empty `_bmad/scripts/__init__.py` and re-run. If tests import from a path like `scripts.config_utils`, run with `PYTHONPATH=_bmad uv run --with pytest python -m pytest _bmad/scripts/tests/ -q` instead.

- [ ] **Step 5: Verify the resolver runs against a real ported skill**

```bash
uv run _bmad/scripts/resolve_customization.py --skill team/core-skills/bmad-review --key agent
```

Expected: JSON on stdout, exit 0. A non-zero exit here means the vendored infra is not usable — HALT and report rather than continuing to Task 2.

- [ ] **Step 6: Commit**

```bash
git add _bmad/
git commit -m "feat(infra): vendor bmad shared Python scripts at upstream paths

Vendors config_utils, memlog, resolve_config, resolve_customization plus
their upstream tests to _bmad/scripts/, matching the {project-root}/_bmad/
path referenced in 37 call sites across the ported skills. Vendored
unmodified from bmad/main so future syncs stay cheap.

Unblocks the ported v6.10.0 skills, which could not run without these."
```

---

## Task 2: Cluster 1 — adopt `bmad-review`, retire `code-review`

This is the proof cluster: it exercises shared infra, a per-skill script, agent rewiring, command repointing, and a retirement, while touching only 5 references.

**Files:**
- Create: `team/core-skills/bmad-review/scripts/word_metrics.py`, `.../scripts/tests/test_word_metrics.py`
- Modify: `team/agents/dev.md:66`, `team/agents/oracle.md:180`, `team/agents/frontend-dev.md:83`, `team/agents/quick-flow-solo-dev.md:63`, `claude-commands/team/code-review.md`
- Delete: `team/workflows/implementation/code-review/`

**Interfaces:**
- Consumes: `_bmad/scripts/resolve_customization.py` from Task 1.
- Produces: the pattern every later cluster repeats — vendor script, flip `workflow=` to `exec=`, repoint command, delete legacy dir, verify.

- [ ] **Step 1: Vendor the per-skill script and its test**

```bash
mkdir -p team/core-skills/bmad-review/scripts/tests
git cat-file -p "bmad/main:src/core-skills/bmad-review/scripts/word_metrics.py" \
  > team/core-skills/bmad-review/scripts/word_metrics.py
git cat-file -p "bmad/main:src/core-skills/bmad-review/scripts/tests/test_word_metrics.py" \
  > team/core-skills/bmad-review/scripts/tests/test_word_metrics.py
```

- [ ] **Step 2: Run the script's test**

```bash
uv run --with pytest python -m pytest team/core-skills/bmad-review/scripts/tests/ -q
```

Expected: pass.

- [ ] **Step 3: Rewire the four agent menu items**

Each currently reads `workflow="{project-root}/team/workflows/implementation/code-review/workflow.yaml"`. Replace the whole attribute with `exec="{project-root}/team/core-skills/bmad-review/skill.md"` and add `bmad-review` to the fuzzy match. Apply to each file:

```bash
for f in team/agents/dev.md team/agents/oracle.md team/agents/frontend-dev.md team/agents/quick-flow-solo-dev.md; do
  sed -i '' 's|workflow="{project-root}/team/workflows/implementation/code-review/workflow.yaml"|exec="{project-root}/team/core-skills/bmad-review/skill.md"|g' "$f"
  sed -i '' 's|cmd="CR or fuzzy match on code-review|cmd="CR or fuzzy match on bmad-review or code-review|g' "$f"
done
grep -n 'CR or fuzzy' team/agents/dev.md team/agents/oracle.md team/agents/frontend-dev.md team/agents/quick-flow-solo-dev.md
```

Expected: four lines, each with `exec=` and both alias names.

- [ ] **Step 4: Repoint the slash command**

Replace the body of `claude-commands/team/code-review.md` with:

```markdown
---
description: 'Perform a thorough clean-context code review using the bmad review lenses'
---

IT IS CRITICAL THAT YOU FOLLOW THIS COMMAND: LOAD the FULL @team/core-skills/bmad-review/skill.md, READ its entire contents and follow its directions exactly!

> Replaces the retired `implementation/code-review` workflow. The command name is
> retained as the familiar entry point.
```

- [ ] **Step 5: Delete the legacy workflow**

```bash
git rm -r -q team/workflows/implementation/code-review/
```

- [ ] **Step 6: Verify — no dangling refs, handlers correct, gates pass**

```bash
echo "dangling: $(grep -rn 'workflows/implementation/code-review' team/ claude-commands/ 2>/dev/null | wc -l | tr -d ' ')"
echo "bad handlers: $(grep -rn 'workflow="[^"]*\.md"' team/agents/ | wc -l | tr -d ' ')"
bash scripts/team-check.sh >/dev/null 2>&1 && echo "team-check: PASS" || echo "team-check: FAIL"
```

Expected: `dangling: 0`, `bad handlers: 0`, `team-check: PASS`.

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "refactor(review): adopt bmad-review, retire code-review workflow

Wires dev, oracle, frontend-dev and quick-flow-solo-dev menus plus
/team:code-review to team/core-skills/bmad-review/. Vendors word_metrics.py.
Menu items change attribute workflow= -> exec= because the ported skill is
skill format, not the legacy YAML engine. 'code-review' kept as fuzzy alias."
```

---

## Task 3: Cluster 2 — adopt `bmad-ux`, retire `create-ux-design`

**Files:**
- Modify: `team/agents/ux-designer.md:87`, `claude-commands/team/create-ux-design.md`
- Delete: `team/workflows/planning/create-ux-design/`

**Interfaces:**
- Consumes: `_bmad/scripts/{memlog,resolve_customization}.py` from Task 1. No per-skill script.
- Produces: nothing later tasks depend on.

- [ ] **Step 1: Rewire the agent menu item**

The item already uses `exec=`, so only the path changes.

```bash
sed -i '' 's|exec="{project-root}/team/workflows/planning/create-ux-design/workflow.md"|exec="{project-root}/team/workflows/planning/bmad-ux/skill.md"|g' team/agents/ux-designer.md
sed -i '' 's|cmd="UX or fuzzy match on ux-design|cmd="UX or fuzzy match on bmad-ux or ux-design|g' team/agents/ux-designer.md
grep -n 'UX or fuzzy' team/agents/ux-designer.md
```

- [ ] **Step 2: Repoint the slash command**

```bash
sed -i '' 's|@team/workflows/planning/create-ux-design/workflow.md|@team/workflows/planning/bmad-ux/skill.md|g' claude-commands/team/create-ux-design.md
grep -n 'bmad-ux' claude-commands/team/create-ux-design.md
```

- [ ] **Step 3: Delete the legacy workflow**

```bash
git rm -r -q team/workflows/planning/create-ux-design/
```

- [ ] **Step 4: Verify**

```bash
echo "dangling: $(grep -rn 'planning/create-ux-design' team/ claude-commands/ 2>/dev/null | wc -l | tr -d ' ')"
bash scripts/team-check.sh >/dev/null 2>&1 && echo "team-check: PASS" || echo "team-check: FAIL"
```

Expected: `dangling: 0`, `team-check: PASS`.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "refactor(ux): adopt bmad-ux, retire create-ux-design workflow"
```

---

## Task 4: Cluster 3 — adopt `bmad-spec`, retire `quick-spec` and `spec-review`

**Files:**
- Modify: `team/agents/quick-flow-solo-dev.md:61`, `team/agents/oracle.md:179`, `claude-commands/team/quick-spec.md`, `claude-commands/team/spec-review.md`
- Delete: `team/workflows/quick-flow/quick-spec/`, `team/workflows/spec-review/`

**Interfaces:**
- Consumes: `_bmad/scripts/{memlog,resolve_config,resolve_customization}.py` from Task 1.
- Produces: nothing later tasks depend on.

- [ ] **Step 1: Rewire both agent menu items**

`quick-flow-solo-dev.md:61` uses `exec=`; `oracle.md:179` uses `workflow=` and must flip to `exec=`.

```bash
sed -i '' 's|exec="{project-root}/team/workflows/quick-flow/quick-spec/workflow.md"|exec="{project-root}/team/workflows/planning/bmad-spec/skill.md"|g' team/agents/quick-flow-solo-dev.md
sed -i '' 's|workflow="{project-root}/team/workflows/spec-review/workflow.yaml"|exec="{project-root}/team/workflows/planning/bmad-spec/skill.md"|g' team/agents/oracle.md
sed -i '' 's|cmd="SR or fuzzy match on spec-review|cmd="SR or fuzzy match on bmad-spec or spec-review|g' team/agents/oracle.md
grep -n 'TS or fuzzy' team/agents/quick-flow-solo-dev.md; grep -n 'SR or fuzzy' team/agents/oracle.md
```

Expected: both lines carry `exec=` and point at `bmad-spec/skill.md`.

- [ ] **Step 2: Repoint both slash commands**

Replace the body of `claude-commands/team/quick-spec.md` with:

```markdown
---
description: 'Distill any intent into the SPEC kernel — the canonical machine contract for downstream work'
---

IT IS CRITICAL THAT YOU FOLLOW THIS COMMAND: LOAD the FULL @team/workflows/planning/bmad-spec/skill.md, READ its entire contents and follow its directions exactly!

> Replaces the retired `quick-flow/quick-spec` workflow.
```

Replace the body of `claude-commands/team/spec-review.md` with:

```markdown
---
description: 'Validate a SPEC kernel against its source intent and report preservation gaps'
---

IT IS CRITICAL THAT YOU FOLLOW THIS COMMAND: LOAD the FULL @team/workflows/planning/bmad-spec/skill.md, READ its entire contents and follow its directions exactly, running its validation path.

> Replaces the retired `spec-review` workflow.
```

- [ ] **Step 3: Delete both legacy workflows**

```bash
git rm -r -q team/workflows/quick-flow/quick-spec/ team/workflows/spec-review/
```

- [ ] **Step 4: Verify**

```bash
echo "dangling: $(grep -rn 'quick-flow/quick-spec\|workflows/spec-review' team/ claude-commands/ 2>/dev/null | wc -l | tr -d ' ')"
echo "bad handlers: $(grep -rn 'workflow="[^"]*\.md"' team/agents/ | wc -l | tr -d ' ')"
bash scripts/team-check.sh >/dev/null 2>&1 && echo "team-check: PASS" || echo "team-check: FAIL"
```

Expected: all zero / PASS.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "refactor(spec): adopt bmad-spec, retire quick-spec and spec-review"
```

---

## Task 5: Cluster 4 — adopt `bmad-prd`, retire `prd` and `validate-prd`

**Files:**
- Modify: `team/agents/pm.md:69`, `team/agents/oracle.md:182`, `claude-commands/team/prd.md`, `claude-commands/team/validate-prd.md`
- Delete: `team/workflows/planning/prd/`, `team/workflows/validate-prd/`

**Interfaces:**
- Consumes: `_bmad/scripts/{memlog,resolve_customization}.py` from Task 1.
- Produces: nothing later tasks depend on.

- [ ] **Step 1: Rewire both agent menu items**

`pm.md:69` uses `exec=`; `oracle.md:182` uses `workflow=` and must flip.

```bash
sed -i '' 's|exec="{project-root}/team/workflows/planning/prd/workflow.md"|exec="{project-root}/team/workflows/planning/bmad-prd/skill.md"|g' team/agents/pm.md
sed -i '' 's|workflow="{project-root}/team/workflows/validate-prd/workflow.yaml"|exec="{project-root}/team/workflows/planning/bmad-prd/skill.md"|g' team/agents/oracle.md
sed -i '' 's|cmd="VP or fuzzy match on validate-prd|cmd="VP or fuzzy match on bmad-prd or validate-prd|g' team/agents/oracle.md
grep -n 'PRD or fuzzy' team/agents/pm.md; grep -n 'VP or fuzzy' team/agents/oracle.md
```

- [ ] **Step 2: Repoint both slash commands**

```bash
sed -i '' 's|@team/workflows/planning/prd/workflow.md|@team/workflows/planning/bmad-prd/skill.md|g' claude-commands/team/prd.md
```

Replace the body of `claude-commands/team/validate-prd.md` with:

```markdown
---
description: 'Validate a PRD is comprehensive, lean, well organized and cohesive'
---

IT IS CRITICAL THAT YOU FOLLOW THIS COMMAND: LOAD the FULL @team/workflows/planning/bmad-prd/skill.md, READ its entire contents and follow its directions exactly, running its validation path.

> Replaces the retired `validate-prd` workflow. bmad-prd unifies create, update
> and validate — state your intent or the skill will ask.
```

- [ ] **Step 3: Delete both legacy workflows**

```bash
git rm -r -q team/workflows/planning/prd/ team/workflows/validate-prd/
```

- [ ] **Step 4: Verify**

```bash
echo "dangling: $(grep -rn 'workflows/planning/prd/\|workflows/validate-prd' team/ claude-commands/ 2>/dev/null | wc -l | tr -d ' ')"
echo "bad handlers: $(grep -rn 'workflow="[^"]*\.md"' team/agents/ | wc -l | tr -d ' ')"
bash scripts/team-check.sh >/dev/null 2>&1 && echo "team-check: PASS" || echo "team-check: FAIL"
```

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "refactor(prd): adopt bmad-prd, retire prd and validate-prd workflows"
```

---

## Task 6: Cluster 5 — retire `quick-flow/quick-dev`, collapse the command collision

Resolves the collision recorded in `docs/sync-notes-v6.10.0.md`: two workflows named `quick-dev`, with `/team:quick-dev` pointing at the legacy one and `/team:dev-story` at the ported one.

**Files:**
- Modify: `team/agents/quick-flow-solo-dev.md:62`, `claude-commands/team/quick-dev.md`
- Delete: `team/workflows/quick-flow/quick-dev/`, `claude-commands/team/dev-story.md`

**Interfaces:**
- Consumes: nothing — `implementation/quick-dev` has no Python dependencies.
- Produces: a single canonical `/team:quick-dev` entry point.

- [ ] **Step 1: Rewire the agent menu item**

```bash
sed -i '' 's|workflow="{project-root}/team/workflows/quick-flow/quick-dev/workflow.md"|exec="{project-root}/team/workflows/implementation/quick-dev/workflow.md"|g' team/agents/quick-flow-solo-dev.md
grep -n 'QD or fuzzy' team/agents/quick-flow-solo-dev.md
```

Expected: `exec=` pointing at `implementation/quick-dev/workflow.md`.

- [ ] **Step 2: Make `/team:quick-dev` canonical**

Replace the body of `claude-commands/team/quick-dev.md` with:

```markdown
---
description: 'Implement a feature, fix, or story through the canonical Phase-4 loop — clarify, plan, implement, review, present'
---

IT IS CRITICAL THAT YOU FOLLOW THIS COMMAND: LOAD the FULL @team/workflows/implementation/quick-dev/workflow.md, READ its entire contents and follow its directions exactly!

> Canonical implementation loop, ported from bmad v6.10.0. Replaces both the
> retired `quick-flow/quick-dev` workflow and the retired `/team:dev-story`
> command. "dev-story" survives as a fuzzy-match alias in the dev and oracle menus.
```

- [ ] **Step 3: Delete the legacy workflow and the redundant command**

```bash
git rm -r -q team/workflows/quick-flow/quick-dev/
git rm -q claude-commands/team/dev-story.md
```

- [ ] **Step 4: Verify the aliases still resolve**

```bash
echo "dangling: $(grep -rn 'quick-flow/quick-dev' team/ claude-commands/ 2>/dev/null | wc -l | tr -d ' ')"
grep -n 'dev-story' team/agents/dev.md team/agents/oracle.md | head -2
bash scripts/team-check.sh >/dev/null 2>&1 && echo "team-check: PASS" || echo "team-check: FAIL"
```

Expected: `dangling: 0`; both agent files still carry `dev-story` as a fuzzy alias; PASS.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "refactor(quick-dev): resolve name collision, retire quick-flow/quick-dev

Collapses two workflows named quick-dev into one. /team:quick-dev becomes
canonical and points at implementation/quick-dev; /team:dev-story is deleted.
'dev-story' remains a fuzzy alias in the dev and oracle menus."
```

---

## Task 7: Cluster 6 — adopt `bmad-forge-idea`, retire `innovation-strategy`

**Files:**
- Create: `team/core-skills/bmad-forge-idea/scripts/resolve_personas.py`, `.../scripts/tests/test_resolve_personas.py`
- Modify: `team/agents/design-strategy-coach.md:70`, `claude-commands/team/innovation-strategy.md`
- Delete: `team/workflows/innovation-strategy/`

**Interfaces:**
- Consumes: `_bmad/scripts/{memlog,resolve_config,resolve_customization}.py` from Task 1.
- Produces: nothing later tasks depend on.

- [ ] **Step 1: Vendor the per-skill script and test**

```bash
mkdir -p team/core-skills/bmad-forge-idea/scripts/tests
git cat-file -p "bmad/main:src/core-skills/bmad-forge-idea/scripts/resolve_personas.py" \
  > team/core-skills/bmad-forge-idea/scripts/resolve_personas.py
git cat-file -p "bmad/main:src/core-skills/bmad-forge-idea/scripts/tests/test_resolve_personas.py" \
  > team/core-skills/bmad-forge-idea/scripts/tests/test_resolve_personas.py
```

- [ ] **Step 2: Run the test**

```bash
uv run --with pytest python -m pytest team/core-skills/bmad-forge-idea/scripts/tests/ -q
```

Expected: pass.

- [ ] **Step 3: Rewire the agent menu item**

```bash
sed -i '' 's|workflow="{project-root}/team/workflows/innovation-strategy/workflow.yaml"|exec="{project-root}/team/core-skills/bmad-forge-idea/skill.md"|g' team/agents/design-strategy-coach.md
sed -i '' 's|cmd="IS or fuzzy match on innovation-strategy|cmd="IS or fuzzy match on forge-idea or innovation-strategy|g' team/agents/design-strategy-coach.md
grep -n 'IS or fuzzy' team/agents/design-strategy-coach.md
```

- [ ] **Step 4: Repoint the slash command**

Replace the body of `claude-commands/team/innovation-strategy.md` with:

```markdown
---
description: 'Forge and stress-test a raw idea into a defensible strategic concept'
---

IT IS CRITICAL THAT YOU FOLLOW THIS COMMAND: LOAD the FULL @team/core-skills/bmad-forge-idea/skill.md, READ its entire contents and follow its directions exactly!

> Replaces the retired `innovation-strategy` workflow.
```

- [ ] **Step 5: Delete the legacy workflow**

```bash
git rm -r -q team/workflows/innovation-strategy/
```

- [ ] **Step 6: Verify**

```bash
echo "dangling: $(grep -rn 'workflows/innovation-strategy' team/ claude-commands/ 2>/dev/null | wc -l | tr -d ' ')"
echo "bad handlers: $(grep -rn 'workflow="[^"]*\.md"' team/agents/ | wc -l | tr -d ' ')"
bash scripts/team-check.sh >/dev/null 2>&1 && echo "team-check: PASS" || echo "team-check: FAIL"
```

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "refactor(ideation): adopt bmad-forge-idea, retire innovation-strategy"
```

---

## Task 8: Cluster 7 — adopt `bmad-deep-recon`, retire `analysis/research`

**Files:**
- Create: `team/core-skills/bmad-deep-recon/scripts/recon_kit.py`, `.../scripts/tests/test_recon_kit.py`
- Modify: `team/agents/analyst.md:74`, `claude-commands/team/research.md`
- Delete: `team/workflows/analysis/research/`

**Interfaces:**
- Consumes: `_bmad/scripts/{memlog,resolve_config,resolve_customization}.py` from Task 1.
- Produces: nothing later tasks depend on.

- [ ] **Step 1: Vendor the per-skill script and test**

```bash
mkdir -p team/core-skills/bmad-deep-recon/scripts/tests
git cat-file -p "bmad/main:src/core-skills/bmad-deep-recon/scripts/recon_kit.py" \
  > team/core-skills/bmad-deep-recon/scripts/recon_kit.py
git cat-file -p "bmad/main:src/core-skills/bmad-deep-recon/scripts/tests/test_recon_kit.py" \
  > team/core-skills/bmad-deep-recon/scripts/tests/test_recon_kit.py
```

- [ ] **Step 2: Run the test**

```bash
uv run --with pytest python -m pytest team/core-skills/bmad-deep-recon/scripts/tests/ -q
```

Expected: pass.

- [ ] **Step 3: Rewire the agent menu item**

The item already uses `exec=`, so only the path changes.

```bash
sed -i '' 's|exec="{project-root}/team/workflows/analysis/research/workflow.md"|exec="{project-root}/team/core-skills/bmad-deep-recon/skill.md"|g' team/agents/analyst.md
sed -i '' 's|cmd="RS or fuzzy match on research|cmd="RS or fuzzy match on deep-recon or research|g' team/agents/analyst.md
grep -n 'RS or fuzzy' team/agents/analyst.md
```

- [ ] **Step 4: Repoint the slash command**

```bash
sed -i '' 's|@team/workflows/analysis/research/workflow.md|@team/core-skills/bmad-deep-recon/skill.md|g' claude-commands/team/research.md
grep -n 'deep-recon' claude-commands/team/research.md
```

- [ ] **Step 5: Delete the legacy workflow**

```bash
git rm -r -q team/workflows/analysis/research/
```

- [ ] **Step 6: Verify**

```bash
echo "dangling: $(grep -rn 'analysis/research' team/ claude-commands/ 2>/dev/null | wc -l | tr -d ' ')"
bash scripts/team-check.sh >/dev/null 2>&1 && echo "team-check: PASS" || echo "team-check: FAIL"
```

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "refactor(research): adopt bmad-deep-recon, retire analysis/research

bmad-deep-recon consolidates market, domain and technical research into one
skill with selectable research types."
```

---

## Task 9: Cluster 8 — adopt `bmad-advanced-elicitation`, retire `advanced-elicitation`

High reference count (87) but only a few distinct line shapes, so this is a scripted replacement rather than 87 judgment calls.

**Files:**
- Create: `team/core-skills/bmad-advanced-elicitation/scripts/pick_methods.py`, `.../scripts/tests/test_pick_methods.py`
- Modify: every file carrying `advancedElicitationTask:` or an `Execute {project-root}/team/workflows/advanced-elicitation/workflow.xml` line
- Delete: `team/workflows/advanced-elicitation/`

**Interfaces:**
- Consumes: `_bmad/scripts/{resolve_config,resolve_customization}.py` from Task 1.
- Produces: nothing later tasks depend on.

- [ ] **Step 1: Vendor the per-skill script and test**

```bash
mkdir -p team/core-skills/bmad-advanced-elicitation/scripts/tests
git cat-file -p "bmad/main:src/core-skills/bmad-advanced-elicitation/scripts/pick_methods.py" \
  > team/core-skills/bmad-advanced-elicitation/scripts/pick_methods.py
git cat-file -p "bmad/main:src/core-skills/bmad-advanced-elicitation/scripts/tests/test_pick_methods.py" \
  > team/core-skills/bmad-advanced-elicitation/scripts/tests/test_pick_methods.py
```

- [ ] **Step 2: Run the test**

```bash
uv run --with pytest python -m pytest team/core-skills/bmad-advanced-elicitation/scripts/tests/ -q
```

Expected: pass.

- [ ] **Step 3: Record the pre-change reference count**

```bash
grep -rc 'workflows/advanced-elicitation' team/ --include='*.md' --include='*.xml' --include='*.yaml' 2>/dev/null | grep -v ':0$' | wc -l | tr -d ' '
```

Note the number — Step 6 verifies it reaches zero.

- [ ] **Step 4: Replace all references, including the broken relative form**

```bash
grep -rl 'workflows/advanced-elicitation' team/ 2>/dev/null | while IFS= read -r f; do
  sed -i '' 's|{project-root}/team/workflows/advanced-elicitation/workflow.xml|{project-root}/team/core-skills/bmad-advanced-elicitation/skill.md|g' "$f"
  sed -i '' 's|\.\./\.\./\.\./\.\./core/workflows/advanced-elicitation/workflow.xml|{project-root}/team/core-skills/bmad-advanced-elicitation/skill.md|g' "$f"
  sed -i '' 's|{project-root}/team/workflows/advanced-elicitation/methods.csv|{project-root}/team/core-skills/bmad-advanced-elicitation/assets/methods.csv|g' "$f"
done
```

The second substitution also fixes the pre-existing broken `../../../../core/` path documented in the spec.

- [ ] **Step 5: Delete the legacy workflow**

```bash
git rm -r -q team/workflows/advanced-elicitation/
```

- [ ] **Step 6: Verify no references survive**

```bash
echo "dangling: $(grep -rn 'workflows/advanced-elicitation' team/ claude-commands/ 2>/dev/null | wc -l | tr -d ' ')"
echo "methods.csv present: $([ -f team/core-skills/bmad-advanced-elicitation/assets/methods.csv ] && echo yes || echo NO)"
bash scripts/team-check.sh >/dev/null 2>&1 && echo "team-check: PASS" || echo "team-check: FAIL"
```

Expected: `dangling: 0`, `methods.csv present: yes`, PASS. If methods.csv is absent the elicitation skill cannot load its catalog — HALT.

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "refactor(elicitation): adopt bmad-advanced-elicitation, retire legacy workflow

Replaces 87 references across the workflow tree. Also repairs the
pre-existing ../../../../core/workflows/ relative path, which resolved to a
non-existent <repo>/core/ directory."
```

---

## Task 10: Cluster 9 — adopt `bmad-party-mode`, retire `party-mode`

Highest blast radius: 111 references, including all 28 agent files. Deliberately last.

**Files:**
- Create: `team/core-skills/bmad-party-mode/scripts/resolve_party.py`, `.../scripts/tests/test_resolve_party.py`
- Modify: all 28 files in `team/agents/`, plus workflow files carrying `partyModeWorkflow:`
- Delete: `team/workflows/party-mode/`

**Interfaces:**
- Consumes: `_bmad/scripts/{memlog,resolve_config,resolve_customization}.py` from Task 1.
- Produces: nothing.

- [ ] **Step 1: Vendor the per-skill script and test**

```bash
mkdir -p team/core-skills/bmad-party-mode/scripts/tests
git cat-file -p "bmad/main:src/core-skills/bmad-party-mode/scripts/resolve_party.py" \
  > team/core-skills/bmad-party-mode/scripts/resolve_party.py
git cat-file -p "bmad/main:src/core-skills/bmad-party-mode/scripts/tests/test_resolve_party.py" \
  > team/core-skills/bmad-party-mode/scripts/tests/test_resolve_party.py
```

- [ ] **Step 2: Run the test**

```bash
uv run --with pytest python -m pytest team/core-skills/bmad-party-mode/scripts/tests/ -q
```

Expected: pass.

- [ ] **Step 3: Confirm the party memory directory is preserved**

```bash
ls -d team/_memory/party* 2>/dev/null || echo "no party memory dir"
```

Party memory lives under `team/_memory/` and must NOT be deleted with the workflow.

- [ ] **Step 4: Replace all references, including the broken relative form**

```bash
grep -rl 'workflows/party-mode' team/ claude-commands/ 2>/dev/null | while IFS= read -r f; do
  sed -i '' 's|{project-root}/team/workflows/party-mode/workflow.md|{project-root}/team/core-skills/bmad-party-mode/skill.md|g' "$f"
  sed -i '' 's|\.\./\.\./\.\./\.\./core/workflows/party-mode/workflow.md|{project-root}/team/core-skills/bmad-party-mode/skill.md|g' "$f"
done
```

- [ ] **Step 5: Delete the legacy workflow**

```bash
git rm -r -q team/workflows/party-mode/
```

- [ ] **Step 6: Verify all 28 agents still resolve**

```bash
echo "dangling: $(grep -rn 'workflows/party-mode' team/ claude-commands/ 2>/dev/null | wc -l | tr -d ' ')"
echo "agents referencing bmad-party-mode: $(grep -rl 'bmad-party-mode' team/agents/ | wc -l | tr -d ' ')"
echo "party memory intact: $([ -d team/_memory ] && echo yes || echo NO)"
bash scripts/team-check.sh >/dev/null 2>&1 && echo "team-check: PASS" || echo "team-check: FAIL"
```

Expected: `dangling: 0`, 28 agents referencing the new skill, memory intact, PASS.

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "refactor(party-mode): adopt bmad-party-mode, retire legacy workflow

Replaces 111 references including all 28 agent files. Party memory under
team/_memory/ is preserved. Also repairs the pre-existing
../../../../core/workflows/ relative path."
```

---

## Task 11: Whole-project verification and documentation

**Files:**
- Modify: `docs/sync-notes-v6.10.0.md` (resolve the "Known issue" section), `docs/WORKFLOW-CATALOG.md`, `docs/ARCHITECTURE.md`

**Interfaces:**
- Consumes: all prior tasks.
- Produces: a release-ready branch.

- [ ] **Step 1: Confirm no legacy workflow survives**

```bash
for w in implementation/code-review planning/create-ux-design quick-flow/quick-spec spec-review planning/prd validate-prd quick-flow/quick-dev innovation-strategy analysis/research advanced-elicitation party-mode; do
  [ -d "team/workflows/$w" ] && echo "STILL PRESENT: $w"
done
echo "sweep complete"
```

Expected: only `sweep complete`.

- [ ] **Step 2: Confirm every ported skill is now referenced**

```bash
for s in bmad-review bmad-deep-recon bmad-forge-idea bmad-party-mode bmad-advanced-elicitation bmad-prd bmad-ux bmad-spec; do
  printf "%-30s %s\n" "$s" "$(grep -rl "$s" team/agents/ claude-commands/team/ 2>/dev/null | wc -l | tr -d ' ')"
done
```

Expected: every count greater than zero. A zero means that cluster's wiring was missed.

- [ ] **Step 3: Handler audit across all agents**

```bash
echo "md behind workflow=: $(grep -rn 'workflow="[^"]*\.md"' team/agents/ | wc -l | tr -d ' ')"
echo "yaml behind exec=:   $(grep -rn 'exec="[^"]*\.yaml"' team/agents/ | wc -l | tr -d ' ')"
```

Expected: both zero.

- [ ] **Step 4: Run all gates**

```bash
bad=0; while read f; do c=$(grep -c '^---$' "$f"); [ "$c" -eq 2 ] || { echo "BAD($c) $f"; bad=1; }; done < <(find team/core-skills team/workflows -iname 'skill.md'); [ $bad -eq 0 ] && echo "frontmatter: PASS"
miss=0; while read f; do d=$(dirname "$f"); for r in $(grep -oE 'references/[a-zA-Z0-9._-]+\.md' "$f" 2>/dev/null|sort -u); do [ -f "$d/$r" ] || { echo "MISSING $d/$r"; miss=1; }; done; done < <(find team/core-skills team/workflows -iname 'skill.md'); [ $miss -eq 0 ] && echo "references: PASS"
bash scripts/team-check.sh >/dev/null 2>&1 && echo "team-check: PASS" || echo "team-check: FAIL"
uv run --with pytest python -m pytest _bmad/scripts/tests/ team/core-skills/*/scripts/tests/ -q
```

Expected: three PASS lines and a green pytest run.

- [ ] **Step 5: Confirm the broken `core/` paths are gone**

```bash
echo "broken core/ refs: $(grep -rn 'core/workflows/' team/ 2>/dev/null | wc -l | tr -d ' ')"
```

Expected: zero. Any survivor belongs to a workflow no cluster touched — repoint it to `{project-root}/team/workflows/…` now.

- [ ] **Step 6: Update the sync notes**

In `docs/sync-notes-v6.10.0.md`, replace the "Known issue — `quick-dev` name collision" section with:

```markdown
## Resolved — `quick-dev` name collision

Resolved 2026-08-23 by the consolidation in
`docs/plans/2026-08-23-bmad-skill-consolidation.md`. `quick-flow/quick-dev` was
retired; `implementation/quick-dev` is canonical and `/team:quick-dev` points at
it. `/team:dev-story` was removed; `dev-story` survives as a fuzzy-match alias.
```

- [ ] **Step 7: Refresh the catalogs**

```bash
grep -rn 'code-review\|create-ux-design\|quick-spec\|validate-prd\|innovation-strategy\|analysis/research\|advanced-elicitation\|party-mode' docs/WORKFLOW-CATALOG.md docs/ARCHITECTURE.md | head -20
```

Update each hit to name the adopting skill instead of the retired workflow. These are documentation tables; edit the rows in place.

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "docs: record skill consolidation, resolve quick-dev collision note

Updates sync notes, workflow catalog and architecture docs to reflect the
retired legacy workflows and the adopted bmad skills."
```

---

## Definition of Done

- All eleven tasks committed on `integration/bmad-v6.10`.
- Zero references to any retired workflow outside `docs/plans/`.
- Every ported skill referenced by at least one agent or command.
- Handler audit clean: no `.md` behind `workflow=`, no `.yaml` behind `exec=`.
- `team-check.sh` returns 0; frontmatter and reference gates pass; all vendored tests pass.
- `VERSION` still `7.9.1` and no tag created — release is a separate, later step.
