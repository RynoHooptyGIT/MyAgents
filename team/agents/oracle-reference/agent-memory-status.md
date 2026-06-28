# Oracle prompt: agent-memory-status (lazy)

Check {project-root}/team/_memory/ directory and report:

1. Which agents have mission briefings (memory files)
2. When each was last updated
3. Whether assignments are still relevant (cross-check with sprint-status.yaml)
4. Which agents need updated briefings

Present as a status table:
| Agent | Has Memory | Last Updated | Status |
|-------|-----------|-------------|--------|

Offer to re-run [LR] Let's Ride to refresh all agent memories.
