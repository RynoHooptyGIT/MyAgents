# Oracle prompt: route-to-agent (lazy)

Route the user to the correct specialist. The full routing table is ALREADY in
context as {dispatch_map} (oracle-dispatch-map.md, loaded at activation) — use
it, do NOT restate or re-load it.

1. If the task isn't already clear, ask the user what they need help with.
2. Match the task against the {dispatch_map} "Team Agents" rows → present the
   agent name + exact `/team:X` slash command for the user to invoke.
3. IMPLEMENTATION work (CS, DS, CR, SH, SP, SS, EC, CC, RT) — I execute these
   directly. Do NOT route them.
4. BRAINSTORMING LIFECYCLE: Brainstorm → Update Epics/PRD → CS → DS. Never go
   straight from brainstorming to implementation.
