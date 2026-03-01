# Risk Scan - Navigator Workflow

Proactive risk detection across sprint health, technical debt, test coverage, migration integrity, and process gaps. Produces a severity-ranked risk report with agent-routed remediation recommendations. This workflow is read-only -- it identifies risks but never fixes them.

---

## Step 1: Load Sprint Status and Baseline

1. Read `{config_source:implementation_artifacts}/sprint-status.yaml` in full.
2. Build the sprint health baseline:
   - Total epics and their statuses.
   - Total stories and their statuses (including inline comment metadata).
   - Stories currently `in-progress` or `review` -- note their epic context.
   - Completed epics with retrospective status (`done` vs `optional`).
3. Record the `generated` date from the YAML header -- compare to today's date to assess staleness.
4. `[CRITICAL]` If sprint-status.yaml cannot be read, STOP and report: "Sprint status unavailable - cannot perform risk scan."

---

## Step 2: Detect Stale and Stuck Stories

Check for stories that may be forgotten or blocked:

1. Find all stories with status `in-progress` in sprint-status.yaml.
2. For each, run `git log --oneline --all --grep="{story-id}" --since="2 days ago"` to check for recent commits referencing the story ID.
3. Apply staleness thresholds:

| Threshold | Severity | Condition |
|-----------|----------|-----------|
| > 4 days | `[CRITICAL]` | No commits referencing story ID in 4+ days |
| 2-4 days | `[WARNING]` | No commits referencing story ID in 2-4 days |
| < 2 days | PASS | Recent activity detected |

4. For stories in `review` status, check if they have been in review for more than 2 days without a follow-up commit (code review may be stalled).
5. Check the `generated` date of sprint-status.yaml itself -- if older than 3 days, flag as `[WARNING]` "Sprint status file may be stale."

---

## Step 3: Scan for Review and Process Gaps

1. **Missing code reviews**: Scan sprint-status.yaml for stories marked `done` whose inline comments do NOT contain "review" or "code review" or "code-reviewed". These stories may have skipped the review step.
2. **Missing retrospectives**: List all epics with status `done` where the retrospective entry is `optional` (not `done`). Count total skipped retrospectives.
3. **Stories skipping ready-for-dev**: Check for stories that went directly from `backlog` to `in-progress` without a `ready-for-dev` step (indicated by missing story file in `{config_source:implementation_artifacts}/`).
4. **Superseded story cleanup**: Look for commented-out story entries or entries marked `SUPERSEDED` -- these indicate scope changes that may need backlog grooming.

| Finding | Severity |
|---------|----------|
| Done story with no review evidence | `[WARNING]` |
| 3+ epics with skipped retrospectives | `[WARNING]` |
| Single epic with skipped retrospective | `[INFO]` |
| Superseded stories needing cleanup | `[INFO]` |

---

## Step 4: Check Migration and Schema Risk

Run read-only checks against the Alembic migration chain:

1. **Duplicate migration numbers**: List files in `backend/alembic/versions/` and check for duplicate numeric prefixes (e.g., two files starting with `081_`).
2. **Multiple Alembic heads**: Run `git log --oneline -20 -- backend/alembic/versions/` to see if multiple migrations were added recently without merging heads.
3. **High migration count**: Count total migration files. If > 90, flag as `[INFO]` -- migration chain length may affect startup time and maintainability.
4. **Recent schema changes without tests**: Cross-reference recently added migrations (from `git log --oneline -5 -- backend/alembic/versions/`) with test files in `backend/tests/` to see if corresponding tests exist.

| Finding | Severity |
|---------|----------|
| Duplicate migration numbers | `[CRITICAL]` |
| Multiple unmerged Alembic heads | `[CRITICAL]` |
| Migration without corresponding test | `[WARNING]` |
| Migration count > 90 | `[INFO]` |

---

## Step 5: Assess Technical Debt Signals

Search for debt markers in recently modified files:

1. Run `git diff --name-only HEAD~10` to get recently modified files.
2. In those files, search for:
   - `# TODO` -- planned work not yet done.
   - `# FIXME` -- known bugs or issues.
   - `# HACK` -- temporary workarounds.
   - `# BLOCKED` -- work blocked on external dependency.
3. Count occurrences per category. Apply thresholds:

| Marker | Threshold | Severity |
|--------|-----------|----------|
| BLOCKED | Any occurrence | `[CRITICAL]` |
| FIXME | > 3 in recent files | `[WARNING]` |
| HACK | > 2 in recent files | `[WARNING]` |
| TODO | > 10 in recent files | `[INFO]` |
| TODO | <= 10 | PASS |

4. Also check sprint-status.yaml inline comments for partial test results (e.g., "7/15 tests passing") which indicate incomplete test coverage on done stories.

`[WARNING]` Stories marked `done` with less than 80% test pass rate (from inline comments) represent latent quality risk.

---

## Step 6: Compute Risk Score and Rank Findings

Aggregate all findings and compute an overall risk score:

### Scoring
| Severity | Points per Finding |
|----------|--------------------|
| `[CRITICAL]` | 10 |
| `[WARNING]` | 3 |
| `[INFO]` | 1 |

### Overall Risk Rating
| Total Points | Rating | Color |
|-------------|--------|-------|
| 0 | GREEN | No actionable risks |
| 1-5 | GREEN | Minor items only |
| 6-15 | YELLOW | Attention needed |
| 16-30 | ORANGE | Significant risks present |
| 31+ | RED | Critical risks require immediate action |

Rank all findings by severity (CRITICAL first), then by category.

---

## Step 7: Generate Risk Report

Output a structured report to `{output_folder}/navigator/risk-scan.md` with:

```
============================================
  RISK SCAN REPORT | {date}
============================================
  Branch:     {current git branch}
  Risk Score: {points} / {rating} ({color})
  Findings:   {critical} critical | {warning} warnings | {info} info
============================================

## Risk Heat Map
| Category | CRITICAL | WARNING | INFO |
|----------|----------|---------|------|
| Stale Stories | N | N | N |
| Process Gaps | N | N | N |
| Migration Risk | N | N | N |
| Technical Debt | N | N | N |
| Test Coverage | N | N | N |

## Top Risks (ranked by severity)
1. [{severity}] {description} -- Route to: {agent} ({command})
2. [{severity}] {description} -- Route to: {agent} ({command})
3. [{severity}] {description} -- Route to: {agent} ({command})

## All Findings
| # | Severity | Category | Description | Affected Item | Remediation Agent |
|---|----------|----------|-------------|--------------|-------------------|

## Sprint Health Summary
- Stories in-progress: {count}
- Stories in review: {count}
- Epics without retrospective: {count}
- Recent migrations: {count in last 5 commits}
- Technical debt markers: {TODO count} TODO, {FIXME count} FIXME, {HACK count} HACK

---
Generated by: Project Oracle (Athena) - Risk Scan Workflow
```

---

## Step 8: Present Results

After writing the report file, present a condensed summary directly to the user:

1. **Risk rating**: One-line verdict with color (e.g., "Risk Score: 8 / YELLOW -- attention needed").
2. **Top 3 risks**: Severity, description, and which agent should address each.
3. `[CRITICAL]` items called out individually with specific remediation routing.
4. File path to the full risk report.
