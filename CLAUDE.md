# Project Instructions

## Multi-Agent Coordination

This project uses the multi-agent coordination protocol. When running as one
of multiple simultaneous Claude instances:

1. Always run `/agent-coordinator` before beginning work
2. Always run `/agent-shutdown` before ending your session
3. Never operate in the main repo checkout — use your assigned worktree
4. Check `.agents/decisions/` before making architectural choices
5. Write decisions that affect other agents to `.agents/decisions/`
6. Respect file ownership — do not edit files claimed by other agents

### Coordination Files

- `.agents/registry/` — who's running (don't edit manually)
- `.agents/claims/` — who owns what files (don't edit manually)
- `.agents/decisions/` — architectural decisions (read before designing)
- `.agents/requests/` — inter-agent requests
- `.agents/status/` — per-agent progress
- `.agents/config.yaml` — coordination settings
