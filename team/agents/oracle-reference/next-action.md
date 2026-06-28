# Oracle prompt: next-action (lazy)

Based on sprint-status.yaml, apply this decision tree to determine AND EXECUTE the single best next action:

1. CRITICAL: Are any stories stuck in "in-progress" for a long time? -> Resume work with DS (dev-story)
2. HIGH: Are any stories in "review" status? -> Execute CR (code-review) workflow
3. MEDIUM: Does the next story in the current epic need a story file? -> Execute CS (create-story)
4. NORMAL: Is there a "ready-for-dev" story? -> Execute DS (dev-story)
5. LOW: Is the current epic complete but no retrospective done? -> Execute RT (retrospective)
6. INFO: Everything clear -> Present brief and ask user for direction

Present the recommended action, then ASK the user to confirm before executing the workflow.
Include: which story, which workflow, and what the expected outcome is.
