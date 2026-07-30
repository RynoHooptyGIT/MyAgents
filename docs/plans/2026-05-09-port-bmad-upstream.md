# Port bmad Upstream Changes Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port 6 relevant upstream commits (3 features) from bmad into the fork, adapting from bmad's `src/bmm-skills/` layout to the fork's `team/` layout.

**Architecture:** Each feature is ported as a self-contained task. The fork uses `team/agents/*.md` for agent/skill definitions and `team/workflows/<phase>/<workflow>/` for multi-step workflows. Bmad uses `src/bmm-skills/<phase>/<skill>/SKILL.md` with `customize.toml` and `references/` subdirectories.

**Skipped commits:** `e36f219c` (catalog rename — fork doesn't use module-help.csv) and `3da984a4` (config promote — fork doesn't use installer config system).

---

## Task 1: Port bmad-investigate skill (4 commits)

**Upstream commits:** `380590aa`, `7b590b0a`, `697d92e3`, `32258a53`

**What:** New forensic investigation skill with evidence grading, stronghold-first methodology, and resumable case files.

**Files:**
- Create: `team/workflows/implementation/investigate/skill.md`
- Create: `team/workflows/implementation/investigate/customize.toml`
- Create: `team/workflows/implementation/investigate/references/case-file-template.md`

**Mapping:** Bmad puts this in `src/bmm-skills/4-implementation/bmad-investigate/`. The fork organizes by phase under `team/workflows/`, so it maps to `team/workflows/implementation/investigate/`.

- [ ] **Step 1: Create the investigate workflow directory**

```bash
mkdir -p team/workflows/implementation/investigate/references
```

- [ ] **Step 2: Create skill.md**

Read the final state of `SKILL.md` from bmad/main:
```bash
git cat-file -p bmad/main:src/bmm-skills/4-implementation/bmad-investigate/SKILL.md
```

Write the content to `team/workflows/implementation/investigate/skill.md`. Adapt any bmad-specific path references:
- Replace `src/bmm-skills/` paths with `team/workflows/` equivalents
- Keep all skill logic, evidence grading, outcomes, and procedures intact

- [ ] **Step 3: Create customize.toml**

Read from bmad/main:
```bash
git cat-file -p bmad/main:src/bmm-skills/4-implementation/bmad-investigate/customize.toml
```

Write to `team/workflows/implementation/investigate/customize.toml`. Update:
- `case_file_template` path to `references/case-file-template.md` (already relative, should work)
- `persistent_facts` glob pattern if needed for fork's structure

- [ ] **Step 4: Create case-file-template.md**

Read from bmad/main:
```bash
git cat-file -p bmad/main:src/bmm-skills/4-implementation/bmad-investigate/references/case-file-template.md
```

Write to `team/workflows/implementation/investigate/references/case-file-template.md`. No adaptation needed — this is a standalone template.

- [ ] **Step 5: Verify file structure**

```bash
find team/workflows/implementation/investigate -type f
```

Expected:
```
team/workflows/implementation/investigate/skill.md
team/workflows/implementation/investigate/customize.toml
team/workflows/implementation/investigate/references/case-file-template.md
```

- [ ] **Step 6: Commit**

```bash
git add team/workflows/implementation/investigate/
git commit -m "feat: port bmad-investigate skill from upstream v6.6.0

Forensic investigation skill with evidence grading (Confirmed/Deduced/
Hypothesized), stronghold-first methodology, and resumable case files.

Ported from bmad commits: 380590aa, 7b590b0a, 697d92e3, 32258a53"
```

---

## Task 2: Port bmad-product-brief refactor (2 commits)

**Upstream commits:** `1c1abaa5`, `c19f6cd7`

**What:** Complete rewrite of product-brief from step-file architecture to lean outcome-driven facilitator with 3 intent modes (Create/Update/Validate), config-driven reviewer panel, and comprehensive eval patterns.

**Files:**
- Rewrite: `team/workflows/analysis/create-product-brief/workflow.md` — replace step-file controller with new facilitator skill
- Create: `team/workflows/analysis/create-product-brief/assets/brief-template.md` — new unified template
- Rewrite: `team/workflows/analysis/create-product-brief/product-brief.template.md` — replace with new template content or remove
- Create: `team/workflows/analysis/create-product-brief/customize.toml` — new config surface
- Remove: `team/workflows/analysis/create-product-brief/steps/step-01-init.md`
- Remove: `team/workflows/analysis/create-product-brief/steps/step-01b-continue.md`
- Remove: `team/workflows/analysis/create-product-brief/steps/step-02-vision.md`
- Remove: `team/workflows/analysis/create-product-brief/steps/step-03-users.md`
- Remove: `team/workflows/analysis/create-product-brief/steps/step-04-metrics.md`
- Remove: `team/workflows/analysis/create-product-brief/steps/step-05-scope.md`
- Remove: `team/workflows/analysis/create-product-brief/steps/step-06-complete.md`

**Design decision:** The upstream completely replaced the step-file approach with a single SKILL.md. Rather than trying to retrofit the new logic into the old step-file architecture, adopt the new approach — it's intentionally simpler and more flexible.

- [ ] **Step 1: Read the new SKILL.md from upstream**

```bash
git cat-file -p bmad/main:src/bmm-skills/1-analysis/bmad-product-brief/SKILL.md
```

- [ ] **Step 2: Read the new template and customize.toml**

```bash
git cat-file -p bmad/main:src/bmm-skills/1-analysis/bmad-product-brief/assets/brief-template.md
git cat-file -p bmad/main:src/bmm-skills/1-analysis/bmad-product-brief/customize.toml
```

- [ ] **Step 3: Replace workflow.md with the new skill content**

Write the SKILL.md content to `team/workflows/analysis/create-product-brief/workflow.md`. Adapt:
- Replace any `src/bmm-skills/` references with `team/workflows/` paths
- Update `doc_standards` skill references if the fork uses different skill names
- Keep `{project_name}`, `{planning_artifacts}` variables — they're standard across both layouts

- [ ] **Step 4: Create assets/brief-template.md**

```bash
mkdir -p team/workflows/analysis/create-product-brief/assets
```

Write the upstream template to `team/workflows/analysis/create-product-brief/assets/brief-template.md`.

- [ ] **Step 5: Create customize.toml**

Write upstream customize.toml to `team/workflows/analysis/create-product-brief/customize.toml`. Update `brief_template` path to `assets/brief-template.md` (should already be relative).

- [ ] **Step 6: Remove old step files**

```bash
rm -rf team/workflows/analysis/create-product-brief/steps/
rm team/workflows/analysis/create-product-brief/product-brief.template.md
```

- [ ] **Step 7: Verify file structure**

```bash
find team/workflows/analysis/create-product-brief -type f
```

Expected:
```
team/workflows/analysis/create-product-brief/workflow.md
team/workflows/analysis/create-product-brief/customize.toml
team/workflows/analysis/create-product-brief/assets/brief-template.md
```

- [ ] **Step 8: Commit**

```bash
git add team/workflows/analysis/create-product-brief/
git commit -m "refactor: port product-brief rewrite from upstream v6.6.0

Replaces step-file architecture with lean outcome-driven facilitator:
- Three intent modes: Create, Update, Validate
- Config-driven doc_standards (replaces polish_skills subagents)
- Mandatory audit trail for Update mode
- Real-time persistence with resume support
- Extract-don't-ingest artifact handling

Ported from bmad commits: 1c1abaa5, c19f6cd7"
```

---

## Task 3: Port brownfield epic scoping (1 commit)

**Upstream commit:** `1ad1f91e`

**What:** Adds file churn detection to epic design — prevents multiple epics from repeatedly modifying the same core files when consolidation would be more efficient.

**Files:**
- Modify: `team/workflows/solutioning/create-epics-and-stories/steps/step-02-design-epics.md`
- Modify: `team/workflows/solutioning/create-epics-and-stories/steps/step-04-final-validation.md`

- [ ] **Step 1: Read the upstream diff**

```bash
git show 1ad1f91e -p
```

Identify the exact additions to step-02 and step-04.

- [ ] **Step 2: Update step-02-design-epics.md**

Add three things from upstream:

1. **New Principle 6** in the EPIC DESIGN PRINCIPLES section:
   - `"Implementation Efficiency": Consider consolidating epics that all modify the same core files into fewer epics`

2. **WRONG/CORRECT Examples** section showing file churn anti-pattern:
   - WRONG: Multiple epics all modifying model, controller, web form, web API
   - CORRECT: One consolidated epic with ordered stories

3. **New Step C: "Review for File Overlap"** after existing epic design steps:
   - Assess whether multiple proposed epics repeatedly target the same core files
   - Distinguish meaningful overlap from incidental sharing
   - Ask whether to consolidate into one epic with ordered stories

- [ ] **Step 3: Update step-04-final-validation.md**

Add **File Churn Check** to the Epic Structure Validation section:
- Do multiple epics repeatedly modify the same core files?
- Assess whether the overlap suggests unnecessary churn or is incidental
- If significant overlap: validate that splitting provides genuine value
- WRONG/RIGHT examples

- [ ] **Step 4: Verify changes**

Read both modified files and confirm the new sections are present and well-integrated with existing content.

- [ ] **Step 5: Commit**

```bash
git add team/workflows/solutioning/create-epics-and-stories/steps/
git commit -m "feat: port brownfield epic scoping from upstream v6.6.0

Adds file churn detection to epic design workflow:
- New principle: Implementation Efficiency
- File overlap review step with WRONG/CORRECT examples
- File churn check in final validation

Ported from bmad commit: 1ad1f91e"
```

---

## Task 4: Mark upstream as synced

- [ ] **Step 1: Record sync state**

```bash
./scripts/sync-upstream.sh --mark-synced
```

- [ ] **Step 2: Commit sync markers**

```bash
git add .team-upstream-version .team-last-sync-tag
git commit -m "chore: mark synced with bmad upstream v6.6.0"
```

- [ ] **Step 3: Push all changes**

```bash
git push origin main
```
