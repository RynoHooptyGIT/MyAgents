# Oracle prompt: approval-queue (lazy)

Manage pending CEO proposals and deferred items. Load the gate protocol
{project-root}/team/engine/ceo-approval.xml when presenting a proposal.

1. Read all files in {project-root}/team/_memory/_comms/proposals/
2. Separate into: PENDING (no decision), DEFERRED (with revisit date)
3. Check if any deferred items have reached their revisit date
4. Read {project-root}/team/_memory/oracle/deferred-proposals.md if it exists

Present:
---
🔮 CEO APPROVAL QUEUE | {date}

PENDING PROPOSALS:
| # | Date | From | Title | Priority |
|---|------|------|-------|----------|
[table of pending proposals]

DEFERRED (DUE FOR REVIEW):
[any deferred items past their revisit date]

DEFERRED (FUTURE):
[deferred items not yet due]

RECENTLY DECIDED:
[last 5 approved/rejected proposals]
---

For each pending proposal, present the full proposal using the CEO Approval format
from ceo-approval.xml and WAIT for CEO decision: [A] Approve, [R] Reject, [M] Modify, [D] Defer.
