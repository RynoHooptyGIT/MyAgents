---
name: 'agent-coordinator'
description: 'Multi-agent startup protocol — creates worktree, registers agent, claims work, syncs decisions. Run this BEFORE starting any work when multiple Claude instances are active.'
---

# Agent Coordinator — Startup Protocol

You are initializing this Claude instance as a coordinated agent. Follow every step below in exact order. Do not skip steps.

<steps CRITICAL="TRUE">

## Step 1: Generate Identity

Generate a unique 6-character agent ID and store it on disk:

```bash
AGENT_ID=$(date +%s%N | shasum | head -c 6)
echo "$AGENT_ID"
```

Store the ID in a PID-scoped file so hooks can read it:

```bash
REPO_ROOT="$(git rev-parse --path-format=absolute --git-common-dir | sed 's|/.git$||')"
echo "$AGENT_ID" > "$REPO_ROOT/.agents/registry/.current-agent-id-$$"
echo "$REPO_ROOT" > "$REPO_ROOT/.agents/registry/.coord-root-$$"
```

Store `AGENT_ID` and `REPO_ROOT` as values you will reference throughout this protocol.

## Step 2: Create Worktree

Check if you are already in a git worktree:

```bash
GIT_DIR="$(git rev-parse --git-dir)"
GIT_COMMON="$(git rev-parse --git-common-dir)"
if [ "$GIT_DIR" != "$GIT_COMMON" ]; then
  echo "Already in a worktree"
else
  echo "In main repo — need worktree"
fi
```

**If already in a worktree:** Extract your agent ID from the worktree path and continue.

**If in main repo:**
1. Ask the user what task they want to work on (or read from sprint-status.yaml if it exists)
2. Create a task slug from the description (lowercase, hyphens, max 30 chars)
3. Create the worktree:

```bash
git worktree add .worktrees/agent-{AGENT_ID} -b agent/{AGENT_ID}/{task-slug}
```

4. IMPORTANT: Change your working directory to the worktree:

```bash
cd .worktrees/agent-{AGENT_ID}
```

5. Write the coordination root path into the worktree:

```bash
echo "$REPO_ROOT" > .agent-coord-root
```

## Step 3: Scan and Clean Registry

Read all existing agent registrations. For each one, check if the agent is still alive:

```bash
ls "$REPO_ROOT/.agents/registry"/agent-*.yaml 2>/dev/null
```

For each registration file found:
1. Read `last_heartbeat` and `pid` from the YAML
2. Check if heartbeat is older than 10 minutes
3. If stale, check if the process is alive: `kill -0 {pid} 2>/dev/null`
4. If process is dead:
   - Check the agent's worktree for uncommitted work: `git -C "$REPO_ROOT/.worktrees/agent-{id}" status --porcelain 2>/dev/null`
   - If uncommitted work: leave worktree, write orphaned status file, remove registry and claim
   - If clean: remove worktree (`git worktree remove`), remove registry and claim
   - Log recovery to `.agents/status/recovery-log.yaml`

Report what you found: "Found N active agents, cleaned up M stale entries."

## Step 4: Register Self

Write your registration file:

```yaml
# .agents/registry/agent-{AGENT_ID}.yaml
agent_id: {AGENT_ID}
pid: {your PID from $$}
worktree: .worktrees/agent-{AGENT_ID}
branch: agent/{AGENT_ID}/{task-slug}
started_at: {current ISO 8601 UTC}
last_heartbeat: {current ISO 8601 UTC}
persona: {your current agent persona, or "general"}
task_summary: "{brief description of assigned task}"
story_id: "{story ID if applicable, or 'manual'}"
status: active
```

## Step 5: Claim Work

Read all existing claims:

```bash
ls "$REPO_ROOT/.agents/claims"/*.yaml 2>/dev/null
cat "$REPO_ROOT/.agents/claims"/*.yaml 2>/dev/null
```

If sprint-status.yaml exists, cross-reference to find unclaimed stories.

**Claim protocol (with mutex):**
1. `mkdir "$REPO_ROOT/.agents/claims/{feature-slug}.lock"` — if this fails, another agent is claiming. Back off 2s and retry (max 3 times).
2. Read all claims again (inside mutex)
3. Check for story_id overlap and owned_paths overlap
4. If conflict: `rmdir` the lock, report the conflict, and ask the user what to do
5. If no conflict: write your claim file, then `rmdir` the lock

```yaml
# .agents/claims/{feature-slug}.yaml
agent_id: {AGENT_ID}
branch: agent/{AGENT_ID}/{task-slug}
story_id: "{story_id}"
claimed_at: {current ISO 8601 UTC}
owned_paths:
  - {list of directories/files you expect to modify}
description: "{what you're building}"
```

## Step 6: Sync Decisions

Read all decision files and check which ones you haven't acknowledged:

```bash
cat "$REPO_ROOT/.agents/decisions"/*.yaml 2>/dev/null
```

For each decision where `acknowledged_by` does not contain your `AGENT_ID`:
1. Read and understand the decision
2. Tell the user about it: "Decision from agent {id}: {decision}"
3. Add your AGENT_ID to the `acknowledged_by` list in the file

## Step 7: Check for Maestro Integration

```bash
[ -f "$REPO_ROOT/team/engine/agent-comms.xml" ] && echo "Maestro detected" || echo "Standalone mode"
```

If Maestro is detected:
1. Create `team/_memory/_comms/` directories if they don't exist
2. Read `team/_memory/_comms/broadcasts/` for team-wide directives
3. Read `team/_memory/{persona}/mission.md` if it exists for pre-assigned work
4. Report any Maestro directives found

## Step 8: Report and Begin

Display a summary:

```
═══════════════════════════════════════════
  AGENT COORDINATOR — Startup Complete
═══════════════════════════════════════════
  Agent ID:    {AGENT_ID}
  Worktree:    .worktrees/agent-{AGENT_ID}
  Branch:      agent/{AGENT_ID}/{task-slug}
  Story:       {story_id or "manual"}
  Claimed:     {list of owned_paths}
  Mode:        {Maestro | Standalone}

  Active Agents: {N}
  {list other agents and their tasks}

  Decisions to observe:
  {list unacknowledged decisions, or "None"}
═══════════════════════════════════════════
  Ready to work. All operations in worktree.
═══════════════════════════════════════════
```

</steps>
