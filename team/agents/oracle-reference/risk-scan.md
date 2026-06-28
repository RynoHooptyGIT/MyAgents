# Oracle prompt: risk-scan (lazy)

Scan for project risks by checking:

1. LIFECYCLE VIOLATIONS: Stories marked "done" that never went through "review" status
2. STALE STORIES: Any stories in "in-progress" that may have been forgotten
3. MISSING REVIEWS: Completed stories that skipped code review
4. MISSING RETROSPECTIVES: Completed epics without retrospectives
5. MISSING STORY FILES: Stories in "in-progress" or later status but no file in stories/ directory
6. MIGRATION CONFLICTS: Check project-context.md for migration directory path; verify no duplicate migration numbers exist
7. TEST GAPS: Note any known coverage gaps
8. BACKLOG HEALTH: Are upcoming stories well-defined or do they need creation?
9. UNPROCESSED BRAINSTORMS: Check if brainstorming session files exist in {output_folder}/analysis/brainstorming-session-*.md that haven't been converted to stories or epic updates
10. AGENT MEMORY STALENESS: Check {project-root}/team/_memory/ for outdated agent mission files

Present findings ranked by severity: CRITICAL, HIGH, MEDIUM, LOW.
For each finding, specify which workflow command I should execute or which agent to route to.
