# Session Handoff - Navigator Workflow

Generates a structured handoff document capturing current session state, decisions made, in-flight work, and recommended next-session starting point. Ensures continuity across AI coding sessions.

---

## Step 1: Load Sprint Status

1. Read `{config_source:implementation_artifacts}/sprint-status.yaml` in full.
2. Parse every epic and story entry. Build a status map:
   - Count stories by status: `backlog`, `ready-for-dev`, `in-progress`, `review`, `done`.
   - Count epics by status: `backlog`, `in-progress`, `done`.
3. Identify the **current active epic** (first epic with status `in-progress` or the first `backlog` epic if none are in-progress).
4. `[CRITICAL]` If sprint-status.yaml cannot be read, STOP and report: "Sprint status unavailable - cannot generate handoff."

---

## Step 2: Scan Recent Activity

Run the following read-only git commands to determine what changed during this session:

| Command | Purpose |
|---------|---------|
| `git log --oneline -10` | Last 10 commits to identify recent work |
| `git log --oneline --since="8 hours ago"` | Commits likely from this session |
| `git diff --stat HEAD~5` | Files changed in recent commits |
| `git status --short` | Uncommitted work in the working tree |

From the results, build a **session activity list**:
- Files modified (group by `backend/`, `packages/frontend/`, `team/`, other)
- Commit messages summarizing what was accomplished
- Any uncommitted changes that may represent work-in-progress

`[WARNING]` If `git status` shows uncommitted changes, flag them explicitly -- they will be lost if not committed before the session ends.

---

## Step 3: Identify In-Progress Work

Cross-reference sprint-status.yaml with git activity:

1. Find all stories with status `in-progress` or `review` in sprint-status.yaml.
2. For each in-progress story, check if recent commits reference that story's ID (e.g., `24-3`, `mt-2-5`).
3. For each story, extract the inline comment (text after `#`) which contains completion notes and context.
4. Classify each in-progress item:
   - **Active this session**: Has recent commits matching the story ID.
   - **Stale carry-over**: Status is `in-progress` but no recent commits match it.

`[CRITICAL]` Flag any story marked `in-progress` with no matching recent activity -- it may be stuck or forgotten.
`[INFO]` Stories in `review` status are awaiting code review in a fresh context.

---

## Step 4: Document Decisions and Context

Scan for evidence of architectural decisions or trade-offs made during this session:

1. Search recent commits for keywords: `refactor`, `redesign`, `trade-off`, `defer`, `workaround`, `decision`.
2. Check `git diff HEAD~5` for changes to:
   - `backend/app/core/config.py` (configuration changes)
   - `backend/app/models/*.py` (schema decisions)
   - `backend/alembic/versions/` (new migrations -- note the purpose)
   - `packages/frontend/src/features/*/` (new feature directories)
3. Check for new or modified files in `output/` (planning artifacts, story files).
4. Note any TODO/FIXME/HACK comments added in recently modified files.

`[INFO]` If no decisions are detected, state "No architectural decisions identified this session."

---

## Step 5: Capture Blockers and Open Issues

Scan for unresolved problems:

1. Check `git status` for merge conflicts (files with `UU` status).
2. Search recently modified files for `# TODO`, `# FIXME`, `# HACK`, `# BLOCKED` markers.
3. Look for test files modified this session and note any known failures from story comments (e.g., "7/15 tests passing" in sprint-status.yaml comments).
4. Check for stories whose sprint-status comments mention blockers (search for `blocked`, `deferred`, `issue`, `bug`).

Classify each finding:
- `[CRITICAL]` Merge conflicts, broken migrations, or failing core tests.
- `[WARNING]` Partial test coverage, deferred features, or known workarounds.
- `[INFO]` TODOs and minor cleanup items.

---

## Step 6: Map Next Session Actions

Apply the Oracle priority decision tree to determine what the next session should focus on:

| Priority | Condition | Recommendation |
|----------|-----------|----------------|
| 1 - CRITICAL | Story stuck `in-progress` > 2 days | Resume with Dev (Amelia) -- `/team:dev` -> DS |
| 2 - CRITICAL | Uncommitted work in working tree | Commit or stash before ending session |
| 3 - HIGH | Story in `review` status | Code review with Dev (Amelia) -- `/team:dev` -> CR |
| 4 - MEDIUM | Next story needs creation | Create story with Oracle (Athena) -- `/team:oracle` -> CS |
| 5 - NORMAL | `ready-for-dev` story available | Implement with Dev (Amelia) -- `/team:dev` -> DS |
| 6 - LOW | Epic complete, no retrospective | Run retro with Oracle (Athena) -- `/team:oracle` -> RT |
| 7 - INFO | No recent health check | Run health check with Custodian (Sentinel) -- `/team:custodian` |

Present the **top 3 recommended actions** in priority order with specific story IDs and agent routing.

---

## Step 7: Generate Handoff Report

Output a structured report to `{output_folder}/navigator/session-handoff.md` with:

```
============================================
  SESSION HANDOFF | {date}
============================================
  Branch:    {current git branch}
  Commit:    {HEAD short hash}
  Active Epic: {epic name} ({X/Y} stories done)
============================================

## Session Summary
[Bullet list of what was accomplished, derived from git log]

## In-Progress Work
| Story ID | Title | Status | Session Activity | Stopping Point |
|----------|-------|--------|-----------------|----------------|

## Decisions & Context
[Numbered list of decisions, or "None identified"]

## Open Issues
| Severity | Description | Affected Story |
|----------|-------------|----------------|

## Next Session Start Point
Priority 1: [action] -> [agent] -> [command]
Priority 2: [action] -> [agent] -> [command]
Priority 3: [action] -> [agent] -> [command]

## Coordination Context

If `.agents/registry/` directory exists and contains agent-*.yaml files, include this section:

Active Agents:
| Agent | Branch | Story | Status | Last Seen |
|-------|--------|-------|--------|-----------|
{for each .agents/registry/agent-*.yaml: agent_id, branch, story_id, status, time since last_heartbeat}

Decisions Made Today:
{for each .agents/decisions/*.yaml where date = today: decision summary and decided_by}

Unresolved Requests:
{for each .agents/requests/*.yaml where responded_at = null and (to = this agent or to = "any"): subject}

If `.agents/` does not exist, omit this entire section.

---
Generated by: Project Oracle (Athena) - Session Handoff Workflow
```

---

## Step 8: Present Results

After writing the report file, present a condensed summary directly to the user:

1. One-line session summary (e.g., "Completed 2 stories in Epic 24, 1 in review").
2. `[CRITICAL]` or `[WARNING]` items requiring immediate attention.
3. The single most important next-session action with the exact agent and command to invoke.
4. File path to the full handoff report.
