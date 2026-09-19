# Oracle prompt: next-action (lazy)

Based on sprint-status.yaml, apply this decision tree to determine the single best next action and either run it (planning/review) or brief it (implementation):

1. CRITICAL: Are any stories stuck in "in-progress" for a long time? -> Brief a worker to resume DS (quick-dev)
2. HIGH: Are any stories in "review" status? -> Brief a reviewer worker for CR (code-review)
3. MEDIUM: Does the next story in the current epic need a story file? -> Run CS (create-story)
4. NORMAL: Is there a "ready-for-dev" story? -> Brief a worker for DS (quick-dev)
5. LOW: Is the current epic complete but no retrospective done? -> Run RT (retrospective)
6. INFO: Everything clear -> Present brief and ask user for direction

Present the recommended action, then ASK the user to confirm before running or briefing it.
Include: which story, which workflow, and what the expected outcome is.
