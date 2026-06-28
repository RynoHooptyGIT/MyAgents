# Oracle prompt: session-handoff (lazy)

Generate a session handoff summary for continuity:

1. Read current sprint-status.yaml
2. Note what the current state is
3. Identify what was likely worked on (most recently changed stories)
4. Check {project-root}/team/_memory/_comms/ for any unprocessed agent messages
5. List what should be done next (apply the next-action decision tree)
6. Note any open risks or blockers
7. Note any pending CEO proposals (see approval-queue)
8. Specify which workflow command should be executed first in the next session

Format as a brief markdown summary that the next session can quickly scan to get up to speed.
Save to {output_folder}/session-handoff-{date}.md
