# Project Brief - Navigator Workflow

Generates a comprehensive project state dashboard with epic-level progress rollups, active work summary, recent activity, risk highlights, and a prioritized next-action recommendation. Designed for a 60-second scan to get fully up to speed on project state.

---

## Step 1: Load Sprint Status and Compute Totals

1. Read `{config_source:implementation_artifacts}/sprint-status.yaml` in full.
2. Parse every entry and classify:
   - **Epics**: Entries matching `epic-*` or `mt-epic-*` or `epic-ai-rmf` -- extract status.
   - **Stories**: All other entries (excluding `generated`, `project`, `project_key`, `tracking_system`, `story_location`, `health-check-system`) -- extract status and inline comment.
   - **Retrospectives**: Entries matching `*-retrospective` -- extract `done` vs `optional`.
3. Compute global totals:
   - Total epics (done / in-progress / backlog)
   - Total stories (done / in-progress / review / ready-for-dev / backlog)
   - Overall completion percentage: `(done stories / total stories) * 100`
4. `[CRITICAL]` If sprint-status.yaml cannot be read, STOP and report: "Sprint status unavailable - cannot generate project brief."

---

## Step 2: Build Epic Progress Table

For each epic, compute a progress rollup:

1. Count stories belonging to that epic (story IDs starting with the epic's number prefix, e.g., `24-*` for Epic 24).
2. Count how many are `done` vs total.
3. Compute completion percentage.
4. Determine the epic phase from the YAML section comments (e.g., "PHASE 5: STRATEGIC").
5. Map epic status to a status indicator:

| Epic Status | Indicator |
|-------------|-----------|
| `done` | DONE |
| `in-progress` | IN PROGRESS |
| `backlog` | BACKLOG |

Present as a table sorted by epic number:

```
| Phase | Epic | Name | Status | Stories | Done | % |
|-------|------|------|--------|---------|------|---|
```

`[INFO]` Group epics by phase with a separator row between phases for readability.

---

## Step 3: Identify Active Work

List all stories currently in a non-terminal state:

1. **In-Progress stories**: Status `in-progress` -- these are actively being worked on.
2. **In-Review stories**: Status `review` -- these need code review.
3. **Ready-for-Dev stories**: Status `ready-for-dev` -- these are queued for implementation.

For each active story, extract from the inline comment:
- Completion date (if present, pattern: "Completed YYYY-MM-DD")
- Test results (if present, pattern: "N/M tests passing")
- Review status (if present, pattern: "review: N issues found")
- Story point estimate (if present, pattern: "N SP")

Present active work as:

```
## Active Work
| Story ID | Epic | Status | Context (from inline comment) |
|----------|------|--------|-------------------------------|
```

`[WARNING]` If zero stories are in-progress and zero are ready-for-dev, flag: "No active development pipeline -- next story creation needed."

---

## Step 4: Summarize Recent Activity

Run read-only git commands to capture recent development activity:

| Command | Purpose |
|---------|---------|
| `git log --oneline -10` | Last 10 commits for activity summary |
| `git log --oneline --since="7 days ago" --format="%h %s"` | Week's activity |
| `git shortlog -sn --since="7 days ago"` | Contributor activity |

Summarize as:
- Number of commits in the last 7 days.
- Key areas of change (group commit messages by epic/feature).
- Most recently completed stories (from sprint-status.yaml, stories with recent "Completed" dates in comments).

---

## Step 5: Aggregate Risk Highlights

Perform a lightweight version of the Risk Scan (full scan available via the RS menu command):

1. **Stale stories**: Any `in-progress` story with no commits in 2+ days. (`[WARNING]`)
2. **Missing retrospectives**: Count of completed epics with `optional` retrospective status. (`[INFO]` if < 3, `[WARNING]` if >= 3)
3. **Partial test coverage**: Stories marked `done` whose inline comments show less than 80% test pass rate (e.g., "7/15 tests passing"). (`[WARNING]`)
4. **Backlog depth**: Count of `backlog` stories in the next upcoming epic. (`[INFO]`)
5. **Sprint status staleness**: If the `generated` date is more than 3 days old. (`[WARNING]`)

Present as a compact risk summary:

```
## Risk Highlights
| Severity | Finding | Action |
|----------|---------|--------|
```

`[INFO]` If no risks are detected, state: "No active risks detected. Run full Risk Scan (RS) for deep analysis."

---

## Step 6: Determine Next Recommended Action

Apply the Navigator priority decision tree (same as Next Action workflow, abbreviated):

| Priority | Condition | Route To |
|----------|-----------|----------|
| P1 `[CRITICAL]` | Stuck in-progress story (> 2 days) | Dev (Amelia) -> DS |
| P2 `[HIGH]` | Story in review status | Dev (Amelia) -> CR |
| P3 `[HIGH]` | Ready-for-dev story available | Dev (Amelia) -> DS |
| P4 `[MEDIUM]` | Backlog story needs creation | SM (Bob) -> CS |
| P5 `[MEDIUM]` | Epic done, next epic is backlog | SM (Bob) -> CS |
| P6 `[LOW]` | Epic done, no retrospective | SM (Bob) -> ER |
| P7 `[INFO]` | All clear -- suggest health check | Custodian (Sentinel) -> HC |

Present the single highest-priority recommendation with the specific story ID, agent name, and exact command.

---

## Step 7: Generate Dashboard Report

Output a structured report to `{output_folder}/navigator/project-brief.md` with:

```
============================================
  PROJECT BRIEF | {date}
============================================
  Branch:     {current git branch}
  Progress:   {done}/{total} stories ({percentage}%)
  Epics:      {done_epics}/{total_epics} complete
  Active Epic: {epic name} ({X/Y} stories done)
============================================

## Epic Progress
| Phase | Epic | Name | Status | Done/Total | % |
|-------|------|------|--------|-----------|---|
[one row per epic, grouped by phase]

## Active Work
| Story ID | Epic | Status | Context |
|----------|------|--------|---------|
[or "No active stories" if pipeline is empty]

## Recent Activity (Last 7 Days)
- {count} commits
- Key changes: {summary}
- Last completed: {story ID and name}

## Risk Highlights
| Severity | Finding | Action |
|----------|---------|--------|
[or "No active risks"]

## Recommendation
**Next**: {action with story ID}
**Agent**: {name} ({persona}) -- `{slash command}` -> {menu option}
**Why**: {one-sentence justification}

---
Generated by: Project Navigator (Navi) - Project Brief Workflow
```

---

## Step 8: Present Results

After writing the report file, present the dashboard summary directly to the user in a compact format:

1. **Progress headline**: "{done}/{total} stories complete ({percentage}%) across {epic_count} epics"
2. **Active epic**: Name and completion status.
3. **In-flight work**: Count of in-progress and review stories (or "Pipeline empty").
4. **Top risk**: The single most severe risk finding, or "No active risks."
5. **Recommendation**: The single next action with agent routing.
6. File path to the full brief report.
