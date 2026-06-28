# Doc-Sync Workflow — Documentation Patrol ("Scribe")

Keep documentation continuously aligned with what the team is actually building.
Reconcile `docs/` against the PRD, epics, and live code; **update** stale docs,
**flag/prune** non-viable ones, and **report** drift. Run by Paige (tech-writer).

> **NON-BLOCKING CONTRACT.** This patrol NEVER blocks a push, PR, or merge. It
> proposes and applies documentation changes only. The worst outcome is a
> drift report — never a failed gate. It never edits production code.

> **PATH NOTE.** In this repo the real planning artifacts live under
> `_bmad-output/` (NOT `output/` — the config path is historically wrong).
> Read PRDs from `_bmad-output/planning-artifacts/prds/`, epics from
> `_bmad-output/planning-artifacts/`, sprint state from
> `_bmad-output/implementation-artifacts/sprint-status.yaml`.

---

## Step 1: Establish the Intent Baseline (source of truth)

Load what the project is *supposed* to be:

1. Read every PRD under `_bmad-output/planning-artifacts/prds/**/*.md`
2. Read epics/stories: `_bmad-output/planning-artifacts/*epics*.md`
3. Read sprint state: `_bmad-output/implementation-artifacts/sprint-status.yaml`
   — which epics/stories are `done` vs `in-progress` vs `backlog`

Build a short mental index: features that are **shipped**, **in flight**, and
**planned-but-not-started**. This drives whether a doc should exist yet.

---

## Step 2: Scope the Patrol

Determine what changed since the last patrol (keep it cheap):

- If invoked from `ship` (a PR just went out): diff the PR range —
  `git diff --name-only origin/main...HEAD` — to find code/areas that moved.
- If invoked standalone: `git log --oneline -20` + `git diff --stat HEAD~10`
  to find recently active areas.
- Always enumerate `docs/**/*.md` and the root planning docs (`CLAUDE.md`,
  `MEMORY.md` pointer index).

Focus the reconciliation on docs covering code/areas that moved. Untouched,
already-accurate docs are left alone.

---

## Step 3: Reconcile (the three verbs)

For each doc in scope, classify and act:

### 3a. UPDATE — doc is stale vs PRD/code
Doc describes intent or behavior that has since changed. Action: edit the doc to
match current PRD + live code. Preserve voice/structure. Examples: renamed
modules, changed commands, superseded decisions, new acceptance criteria.

### 3b. CREATE — shipped feature has no doc
An epic/story is `done` (Step 1) but no doc covers it, and it warrants one
(user-facing system, architecture decision, non-obvious workflow). Action: draft
a concise doc in `docs/`. Do NOT pre-document planned-but-unstarted work.

### 3c. PRUNE — doc is non-viable
Doc describes a feature that was cut, a path that no longer exists, or a decision
that was reversed. Action: **do not hard-delete blindly.** Verify against PRD +
code first. If confirmed dead → remove the file (or, if it has historical value,
move under `docs/archive/` with a one-line "superseded by X on <date>" header).
Anything you remove or archive MUST be listed in the report (Step 5).

> **Reversal guard:** if what a doc describes contradicts how it was introduced,
> surface that in the report instead of silently deleting. Never prune a doc you
> did not author when the evidence is ambiguous — flag for human review.

---

## Step 4: Keep the Indexes Honest

- If `docs/` gained/lost/renamed files, update any `docs/index.md` (create one
  only if multiple docs exist).
- If a durable fact changed (active project, locked decision, artifact paths),
  update the `MEMORY.md` pointer line — do not write memory *content* into it.
- Verify `CLAUDE.md` references still resolve (no links to moved/removed files).

---

## Step 5: Drift Report (always produced)

Write `{output_folder}/custodian/doc-sync.md` and echo a short summary to chat:

```
============================================
  DOC-SYNC PATROL — <date>
============================================
  Trigger:   [ship PR #NNN / standalone / scheduled]
  Scope:     [N docs reviewed, M in active code areas]
============================================

UPDATED   ([count]):
  - docs/<file>  — [what changed and why, 1 line]

CREATED   ([count]):
  - docs/<file>  — [shipped feature now documented]

PRUNED    ([count]):
  - docs/<file>  — [removed / archived → reason]

FLAGGED   ([count]):   ← needs human decision, NOT auto-applied
  - docs/<file>  — [ambiguous: contradicts PRD §X / reversal suspected]

PRD DRIFT ([count]):   ← PRD itself looks out of date vs shipped code
  - prd-<name> §<section> — [code does X, PRD still says Y]

VERDICT:  [IN SYNC / DRIFT CORRECTED / NEEDS REVIEW]
```

`PRD DRIFT` is the scrum-master/architect's lane: the patrol does NOT silently
rewrite the PRD. It reports where the PRD has fallen behind reality so they can
decide. Adjusting the PRD stays a human (architect) call; the patrol surfaces it.

---

## Step 6: Stage Doc Changes (non-blocking + loop-safe)

- When invoked from `ship` (the only auto-trigger): **stage** applied doc edits so
  they ride along in the SAME PR push — do NOT create a separate commit and do NOT
  push yourself. Ship's Step 7 performs the single push. This is what prevents a
  loop: your doc edits are part of the original push, never a new one.
- When standalone (manual `/team:doc-sync`): leave changes unstaged and tell the
  user what to review, OR — only if they confirm — commit as:

  ```
  docs: doc-sync patrol — <date> [skip-doc-sync]
  ```

  The `[skip-doc-sync]` trailer is **mandatory** on any commit this patrol
  creates. It is the marker the ship loop-guard (Step 6c.1) checks so the patrol
  can never react to its own output. Never push such a commit from here without
  explicit user confirmation.

`[INFO]` If no drift found: report `VERDICT: IN SYNC` and make no edits.
