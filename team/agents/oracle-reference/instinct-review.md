# Oracle prompt: instinct-review (lazy)

Review learned instincts. Instincts are unreviewed context, not policy.

1. Run `python3 scripts/instincts/instinct.py status` and show the output verbatim.
2. If there are pending instincts, walk them one at a time:
   "{id} · {trigger} → {action} ({confidence}, {domain}) — accept / reject / skip?"
   Apply each answer immediately: `python3 scripts/instincts/instinct.py accept {id}` or `reject {id}`.
   In auto mode, first run `python3 scripts/instincts/instinct.py accept --min-confidence {auto_accept_confidence}` and only ask about the rest.
3. Offer: "[P] Promote to global (patterns active in 2+ projects)" → `python3 scripts/instincts/instinct.py promote`; "[X] Prune stale pending" → `python3 scripts/instincts/instinct.py prune`.
4. Refresh `status --json`, update {oracle_pending_instincts} and {oracle_active_instincts}, and summarize what changed in one line.
5. Remind: accepted project instincts live in `team/_memory/_learnings/instincts/` and ship with the next commit; other agents inherit them.
