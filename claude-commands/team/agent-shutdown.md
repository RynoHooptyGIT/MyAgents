---
name: 'agent-shutdown'
description: 'Multi-agent shutdown protocol — commits work, pushes branch, runs session handoff, releases claims, cleans up worktree. Run this BEFORE ending your session.'
---

# Agent Shutdown Protocol

You are shutting down this coordinated agent instance. Follow every step in exact order.

<steps CRITICAL="TRUE">

## Step 1: Resolve Identity

Read your agent ID and coordination root:

```bash
REPO_ROOT="$(cat .agent-coord-root 2>/dev/null || git rev-parse --path-format=absolute --git-common-dir | sed 's|/.git$||')"
AGENT_ID="$(cat "$REPO_ROOT/.agents/registry/.current-agent-id-"* 2>/dev/null | head -1)"
echo "Agent: $AGENT_ID, Root: $REPO_ROOT"
```

If AGENT_ID is empty, check the worktree path for the agent ID: extract from `.worktrees/agent-{ID}`.

## Step 2: Commit All Work

```bash
git status --short
```

If there are uncommitted changes:

```bash
git add -A
git commit -m "feat({AGENT_ID}): {brief summary of work done}

Story: {story_id}
Agent: {AGENT_ID}"
```

If working tree is clean, skip to Step 3.

## Step 3: Push Branch

```bash
git push origin "$(git branch --show-current)" 2>&1
```

If push fails (e.g., no remote configured), note the failure but continue — the branch is preserved locally.

## Step 4: Run Session Handoff

Execute the Session Handoff workflow to capture session state. This runs inside the worktree, so all git commands scope correctly.

Load and execute: `@team/workflows/navigator/session-handoff/`

**Additional coordination context for the handoff report** (add to the report in Step 7 of SH):

Read `.agents/registry/*.yaml`, `.agents/claims/*.yaml`, `.agents/decisions/*.yaml` from `$REPO_ROOT/.agents/` and include a `## Coordination Context` section showing active agents, claims, and decisions.

After SH completes, also write a handoff summary:

```yaml
# $REPO_ROOT/.agents/status/agent-{AGENT_ID}-handoff.yaml
agent_id: {AGENT_ID}
completed_at: {ISO 8601 UTC}
branch: {current branch}
story_id: {story_id}
summary: "{what was accomplished}"
files_changed:
  - {list from git diff --name-only}
decisions_made:
  - {list any decisions this agent wrote}
next_steps: "{recommended next actions}"
```

If Maestro integration is enabled, also write the handoff to `team/_memory/_comms/handoffs/` using the naming convention `{date}-{AGENT_ID}-handoff-{slug}.md`.

## Step 5: Release Claim

```bash
rm -f "$REPO_ROOT/.agents/claims/{feature-slug}.yaml"
rmdir "$REPO_ROOT/.agents/claims/{feature-slug}.lock" 2>/dev/null || true
```

## Step 6: Remove Worktree

First, change directory back to the repo root (you can't remove a worktree you're standing in):

```bash
cd "$REPO_ROOT"
git worktree remove ".worktrees/agent-${AGENT_ID}" 2>&1
```

If removal fails (e.g., unclean), force is NOT used — report the issue instead.

## Step 7: Deregister

```bash
rm -f "$REPO_ROOT/.agents/registry/agent-${AGENT_ID}.yaml"
rm -f "$REPO_ROOT/.agents/registry/.current-agent-id-"*
rm -f "$REPO_ROOT/.agents/registry/.coord-root-"*
rm -f "$REPO_ROOT/.agents/registry/${AGENT_ID}.counter"
rm -f "$REPO_ROOT/.agents/status/agent-${AGENT_ID}.yaml"
```

## Step 8: Report

```
═══════════════════════════════════════════
  AGENT SHUTDOWN — Complete
═══════════════════════════════════════════
  Agent ID:    {AGENT_ID}
  Branch:      {branch} (pushed: yes/no)
  Story:       {story_id}
  Work:        {committed/clean}
  Handoff:     {path to handoff file}
  Worktree:    removed
  Claims:      released
  Registry:    deregistered
═══════════════════════════════════════════
  Agent session ended cleanly.
═══════════════════════════════════════════
```

</steps>
