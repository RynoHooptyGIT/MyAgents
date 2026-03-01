# Next Action - Navigator Workflow

Analyzes sprint-status.yaml to determine the single highest-priority next action and routes to the correct specialist agent with a specific command. Uses a weighted priority decision tree to ensure the most impactful work is recommended first.

---

## Step 1: Load and Parse Sprint Status

1. Read `{config_source:implementation_artifacts}/sprint-status.yaml` in full.
2. Build a complete status inventory:
   - **Epics**: List each epic with its status (`backlog`, `in-progress`, `done`).
   - **Stories**: For each epic, list every story with its status and inline comment (text after `#`).
   - **Retrospectives**: Note which completed epics have `optional` vs `done` retrospectives.
3. Identify the **current active epic**: the first epic with status `in-progress`, or the first `backlog` epic if all active epics are `done`.
4. `[CRITICAL]` If sprint-status.yaml cannot be read, STOP and report: "Sprint status unavailable - cannot determine next action."

---

## Step 2: Evaluate Story Pipeline

Classify all stories into buckets:

| Bucket | Definition | Count |
|--------|-----------|-------|
| Done | Status is `done` | N |
| In-Progress | Status is `in-progress` | N |
| In Review | Status is `review` | N |
| Ready for Dev | Status is `ready-for-dev` | N |
| Backlog | Status is `backlog` | N |
| Superseded | Commented out or marked superseded | N |

For the current active epic specifically, compute:
- Total stories in the epic (excluding superseded)
- Stories completed vs remaining
- Completion percentage

`[INFO]` Report the pipeline counts as a one-line summary (e.g., "Pipeline: 95 done | 0 in-progress | 0 review | 0 ready | 30 backlog").

---

## Step 3: Check Dependencies and Blockers

1. Scan sprint-status.yaml comments for dependency signals:
   - Keywords: `blocked`, `depends on`, `requires`, `after`, `deferred`.
   - Cross-references: Story IDs mentioned in other stories' comments (e.g., "split to 14.6.1").
2. For stories in the current active epic with status `backlog`, verify that prerequisite stories (earlier numbers in the same epic) are `done`.
3. Check for stories marked `ready-for-dev` that reference incomplete dependencies.
4. Check for `SUPERSEDED` or commented-out stories that may have replacement stories.

`[WARNING]` Flag any `ready-for-dev` story whose dependencies are not fully met.
`[INFO]` Note stories that were split or deferred (these may need SM attention to create replacement stories).

---

## Step 4: Apply Priority Decision Tree

Evaluate conditions top-to-bottom. The **first matching condition** determines the recommendation:

| Priority | Severity | Condition | Check Method |
|----------|----------|-----------|-------------|
| P1 | `[CRITICAL]` | Story stuck `in-progress` with no commits in 48+ hours | `git log --oneline --since="2 days ago"` vs in-progress story IDs |
| P2 | `[CRITICAL]` | Uncommitted changes in working tree | `git status --short` has output |
| P3 | `[HIGH]` | Story in `review` status | sprint-status.yaml has `review` entries |
| P4 | `[HIGH]` | Current epic has `ready-for-dev` story | First `ready-for-dev` in active epic |
| P5 | `[MEDIUM]` | Current epic has `backlog` stories needing creation | First `backlog` story in active epic |
| P6 | `[MEDIUM]` | Current epic fully `done`, next epic exists in `backlog` | All stories done, next epic is backlog |
| P7 | `[LOW]` | Completed epic missing retrospective | Epic status `done` with retro `optional` |
| P8 | `[INFO]` | No immediate work -- suggest health check or audit | All epics done or no actionable items |

Only one recommendation should be made -- the highest priority match.

---

## Step 5: Route to Agent

Map the recommended action to the correct agent using this routing table:

| Action Type | Agent | Name | Invoke Command | Menu Command |
|-------------|-------|------|----------------|--------------|
| Resume stuck story | Dev | Amelia | `/bmad:bmm:agents:dev` | DS (Dev Story) |
| Code review | Dev | Amelia | `/bmad:bmm:agents:dev` | CR (Code Review) |
| Implement ready story | Dev | Amelia | `/bmad:bmm:agents:dev` | DS (Dev Story) |
| Create next story | Oracle | Athena | `/bmad:bmm:agents:oracle` | CS (Create Story) |
| Epic retrospective | Oracle | Athena | `/bmad:bmm:agents:oracle` | RT (Retrospective) |
| Sprint planning | Oracle | Athena | `/bmad:bmm:agents:oracle` | SP (Sprint Plan) |
| Repo health check | Custodian | Sentinel | `/bmad:bmm:agents:custodian` | HC (Health Check) |
| Architecture review | Architect | Winston | `/bmad:bmm:agents:architect` | -- |
| Test strategy | Test Architect | Murat | `/bmad:bmm:agents:tea` | -- |
| Security audit | Security Auditor | Shield | `/bmad:bmm:agents:security-auditor` | -- |
| NIST compliance | NIST Expert | Atlas | `/bmad:bmm:agents:nist-rmf-expert` | -- |

`[CRITICAL]` This workflow is read-only — it recommends actions but does not execute them. Route to the appropriate specialist agent.

---

## Step 6: Generate Report

Output a structured report to `{output_folder}/navigator/next-action.md` with:

```
============================================
  NEXT ACTION RECOMMENDATION | {date}
============================================
  Branch:     {current git branch}
  Active Epic: {epic name} ({X/Y} stories done)
  Pipeline:    {done} done | {in-progress} in-progress | {review} review | {ready} ready | {backlog} backlog
============================================

## Recommendation
**Priority**: {P1-P8} [{severity}]
**Action**: {specific action description with story ID}
**Why**: {one-sentence justification}
**Agent**: {agent name} ({persona name})
**Command**: {exact slash command and menu option}

## Pipeline Status
| Epic | Status | Stories Done | Total | % |
|------|--------|-------------|-------|---|

## Decision Log
[Which priority conditions were checked and their results]

---
Generated by: Project Oracle (Athena) - Next Action Workflow
```

---

## Step 7: Present Results

After writing the report, present a condensed recommendation directly to the user:

1. **One-liner**: "Next: {action} -- invoke {agent} with `{command}` -> {menu option}"
2. **Context**: One sentence explaining why this is the highest priority.
3. **Alternative**: If a close second-priority action exists, mention it briefly.
4. `[CRITICAL]` or `[WARNING]` flags if any blocking conditions were detected.
