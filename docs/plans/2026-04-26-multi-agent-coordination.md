# Multi-Agent Coordination System Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a file-based coordination system that enables multiple Claude Code instances to work simultaneously in the same repo without conflicts, using git worktrees for isolation and shared state files for awareness.

**Architecture:** Portable core (`.agents/` directory with registry, claims, decisions, hooks) that works in any git repo, plus a Maestro integration layer that cross-posts to `team/_memory/_comms/` when the Maestro engine is present. Three Claude Code hooks enforce worktree isolation and claim boundaries.

**Tech Stack:** Shell scripts (bash), YAML state files, Claude Code hooks API, markdown slash commands

**Spec:** `docs/specs/2026-04-26-multi-agent-coordination-design.md`

---

## Chunk 1: Foundation (Directory Scaffold, Config, Gitignore, CLAUDE.md)

Everything depends on the `.agents/` directory structure and config existing first.

### Task 1: Create .agents/ directory scaffold and config

**Files:**
- Create: `.agents/config.yaml`
- Create: `.agents/registry/.gitkeep`
- Create: `.agents/claims/.gitkeep`
- Create: `.agents/decisions/.gitkeep`
- Create: `.agents/status/.gitkeep`
- Create: `.agents/requests/.gitkeep`
- Create: `.agents/hooks/.gitkeep`

- [ ] **Step 1: Create directory scaffold**

```bash
mkdir -p .agents/{registry,claims,decisions,status,requests,hooks}
```

Verify all directories exist:
```bash
ls -la .agents/
```
Expected: 7 subdirectories (registry, claims, decisions, status, requests, hooks, plus config.yaml after next step)

- [ ] **Step 2: Create .gitkeep files so empty dirs are tracked**

```bash
for dir in .agents/registry .agents/claims .agents/decisions .agents/status .agents/requests .agents/hooks; do
  touch "$dir/.gitkeep"
done
```

- [ ] **Step 3: Create .agents/config.yaml**

Write the full config file with all defaults from spec Section 7:

```yaml
# Multi-Agent Coordination Configuration
# See: docs/specs/2026-04-26-multi-agent-coordination-design.md

coordination:
  # Heartbeat
  heartbeat_interval_calls: 20       # Update heartbeat every N tool calls
  stale_threshold_minutes: 10        # Consider agent dead after N minutes no heartbeat

  # Claims
  claim_conflict_action: block       # block | warn | allow
  claim_path_matching: prefix        # prefix | exact

  # Worktrees
  auto_worktree: true                # Enforce worktree creation on startup
  worktree_base_dir: .worktrees      # Relative to repo root
  cleanup_orphaned_worktrees: true   # Clean stale worktrees on startup
  branch_prefix: agent               # Branch naming: {prefix}/{id}/{slug}

  # Decisions
  decision_sync_on_startup: true     # Read all decisions on startup
  decision_sync_interval_calls: 100  # Periodic re-sync (in addition to event-driven sync before architectural choices)

  # Requests
  request_check_interval_calls: 50   # Check for inbound requests periodically

maestro_integration:
  enabled: auto                      # auto-detected from team/engine/ presence
  cross_post_decisions: true
  cross_post_handoffs: true
  cross_post_findings: true
  respect_mission_assignments: true
```

- [ ] **Step 4: Verify config is valid YAML**

```bash
python3 -c "import yaml; yaml.safe_load(open('.agents/config.yaml'))" && echo "VALID" || echo "INVALID"
```

Expected: `VALID`

- [ ] **Step 5: Commit scaffold**

```bash
git add .agents/
git commit -m "feat: add .agents/ coordination directory scaffold and config"
```

---

### Task 2: Update .gitignore and create CLAUDE.md

**Files:**
- Modify: `.gitignore`
- Create: `CLAUDE.md`

- [ ] **Step 1: Add .worktrees/ to .gitignore**

Append to `.gitignore`:

```
# Agent worktrees (ephemeral, per-instance)
.worktrees/

# Agent PID-scoped identity files (ephemeral)
.agents/registry/.current-agent-id-*
.agents/registry/.coord-root-*
.agents/registry/*.counter
```

- [ ] **Step 2: Verify .gitignore change**

```bash
grep -n "worktrees" .gitignore
```

Expected: Line showing `.worktrees/`

- [ ] **Step 3: Create CLAUDE.md**

Create `CLAUDE.md` in the project root with the multi-agent coordination section:

```markdown
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
```

- [ ] **Step 4: Commit**

```bash
git add .gitignore CLAUDE.md
git commit -m "feat: add CLAUDE.md and gitignore worktrees"
```

---

## Chunk 2: Hook Scripts

The three enforcement hooks. These are shell scripts in `.agents/hooks/` that Claude Code invokes automatically. Each script reads the tool input from stdin (Claude Code pipes JSON to hook commands via stdin).

**Important context for the implementer:** Claude Code hooks receive tool input as JSON via stdin. The hook format in `settings.local.json` uses this structure:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "bash .agents/hooks/worktree-guard.sh",
            "timeout": 5000
          }
        ]
      }
    ]
  }
}
```

The JSON piped to stdin has the shape: `{"tool_name": "Bash", "tool_input": {"command": "git checkout main"}}` for Bash, or `{"tool_name": "Edit", "tool_input": {"file_path": "/path/to/file"}}` for Edit/Write.

### Task 3: Create worktree-guard.sh hook

**Files:**
- Create: `.agents/hooks/worktree-guard.sh`

- [ ] **Step 1: Write test fixture**

Create a test script that verifies the hook logic:

```bash
# .agents/hooks/test-worktree-guard.sh
#!/usr/bin/env bash
# Test harness for worktree-guard hook
set -e

HOOK=".agents/hooks/worktree-guard.sh"
PASS=0
FAIL=0

run_test() {
  local desc="$1" input="$2" expected_exit="$3"
  local actual_exit=0
  echo "$input" | bash "$HOOK" > /dev/null 2>&1 || actual_exit=$?

  if [ "$actual_exit" -eq "$expected_exit" ]; then
    echo "  PASS: $desc"
    PASS=$((PASS + 1))
  else
    echo "  FAIL: $desc (expected exit $expected_exit, got $actual_exit)"
    FAIL=$((FAIL + 1))
  fi
}

echo "=== Worktree Guard Tests ==="

# In a worktree, git commands should be allowed (exit 0)
# In main repo, git checkout/switch should be blocked (exit 2)
# Non-git commands should always be allowed (exit 0)

# Test: non-git command always allowed
run_test "non-git command allowed" \
  '{"tool_name":"Bash","tool_input":{"command":"ls -la"}}' 0

# Test: git status always allowed (not a branch operation)
run_test "git status allowed" \
  '{"tool_name":"Bash","tool_input":{"command":"git status"}}' 0

# Test: git log always allowed
run_test "git log allowed" \
  '{"tool_name":"Bash","tool_input":{"command":"git log --oneline -5"}}' 0

echo ""
echo "Results: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ] || exit 1
```

- [ ] **Step 2: Write worktree-guard.sh**

```bash
#!/usr/bin/env bash
# Hook: Worktree Guard
# Blocks git branch operations (checkout, switch, merge, rebase) when
# running in the main repo instead of a worktree.
# Called by Claude Code as a PreToolUse hook on Bash commands.
# Input: JSON on stdin with tool_name and tool_input.command
# Exit 0 = allow, Exit 2 = block (with message on stderr)

set -euo pipefail

# Read tool input from stdin
INPUT="$(cat)"

# Extract the command string — try python3 first, fall back to grep
CMD="$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_input',{}).get('command',''))" 2>/dev/null)" || \
CMD="$(echo "$INPUT" | grep -o '"command"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*: *"//;s/"$//')"

# If no command extracted, allow (not a Bash call we care about)
[ -z "$CMD" ] && exit 0

# Only check git branch operations
case "$CMD" in
  git\ checkout*|git\ switch*|git\ merge*|git\ rebase*)
    ;;
  *)
    # Not a branch operation — allow
    exit 0
    ;;
esac

# Check if we're in a worktree by comparing git-dir to git-common-dir
GIT_DIR="$(git rev-parse --git-dir 2>/dev/null)" || exit 0
GIT_COMMON="$(git rev-parse --git-common-dir 2>/dev/null)" || exit 0

if [ "$GIT_DIR" = "$GIT_COMMON" ]; then
  # We are in the main repo, NOT a worktree — block
  echo "BLOCKED: Branch operations (checkout/switch/merge/rebase) are not allowed in the main repo." >&2
  echo "Use your assigned worktree instead. Run /agent-coordinator to set one up." >&2
  exit 2
fi

# We are in a worktree — allow
exit 0
```

- [ ] **Step 3: Make executable and run tests**

```bash
chmod +x .agents/hooks/worktree-guard.sh .agents/hooks/test-worktree-guard.sh
bash .agents/hooks/test-worktree-guard.sh
```

Expected: All tests pass (note: git checkout test behavior depends on whether we're currently in a worktree or not)

- [ ] **Step 4: Commit**

```bash
git add .agents/hooks/worktree-guard.sh .agents/hooks/test-worktree-guard.sh
git commit -m "feat: add worktree-guard hook — blocks branch ops in main repo"
```

---

### Task 4: Create claim-check.sh hook

**Files:**
- Create: `.agents/hooks/claim-check.sh`

- [ ] **Step 1: Write test fixture**

```bash
# .agents/hooks/test-claim-check.sh
#!/usr/bin/env bash
set -e

HOOK=".agents/hooks/claim-check.sh"
PASS=0
FAIL=0
COORD_ROOT="$(pwd)"

setup() {
  # Create a mock claim from another agent
  mkdir -p .agents/claims .agents/registry
  cat > .agents/claims/feature-auth.yaml << 'EOF'
agent_id: other1
branch: agent/other1/auth
story_id: "24-3"
claimed_at: 2026-04-26T14:30:00Z
owned_paths:
  - backend/app/auth/
  - backend/app/models/user.py
description: "Auth system"
EOF
  # Create own agent identity
  echo "self01" > .agents/registry/.current-agent-id-$$
  echo "$COORD_ROOT" > .agents/registry/.coord-root-$$
}

teardown() {
  rm -f .agents/claims/feature-auth.yaml
  rm -f .agents/registry/.current-agent-id-$$
  rm -f .agents/registry/.coord-root-$$
}

run_test() {
  local desc="$1" input="$2" expected_exit="$3"
  local actual_exit=0
  echo "$input" | bash "$HOOK" > /dev/null 2>&1 || actual_exit=$?

  if [ "$actual_exit" -eq "$expected_exit" ]; then
    echo "  PASS: $desc"
    PASS=$((PASS + 1))
  else
    echo "  FAIL: $desc (expected exit $expected_exit, got $actual_exit)"
    FAIL=$((FAIL + 1))
  fi
}

echo "=== Claim Check Tests ==="
setup
trap teardown EXIT

# File inside claimed path should be blocked
run_test "edit claimed file blocked" \
  '{"tool_name":"Edit","tool_input":{"file_path":"backend/app/auth/router.py"}}' 2

# Exact file claim should be blocked
run_test "edit exact claimed file blocked" \
  '{"tool_name":"Edit","tool_input":{"file_path":"backend/app/models/user.py"}}' 2

# File outside claimed paths should be allowed
run_test "edit unclaimed file allowed" \
  '{"tool_name":"Edit","tool_input":{"file_path":"frontend/src/App.tsx"}}' 0

# .agents/ files should never be blocked (coordination files)
run_test "edit .agents/ file allowed" \
  '{"tool_name":"Write","tool_input":{"file_path":".agents/decisions/test.yaml"}}' 0

echo ""
echo "Results: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ] || exit 1
```

- [ ] **Step 2: Write claim-check.sh**

```bash
#!/usr/bin/env bash
# Hook: Claim Check
# Blocks edits to files claimed by another agent.
# Called by Claude Code as a PreToolUse hook on Edit/Write.
# Input: JSON on stdin with tool_name and tool_input.file_path
# Exit 0 = allow, Exit 2 = block

set -euo pipefail

INPUT="$(cat)"

# Extract file_path from tool input
FILE_PATH="$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_input',{}).get('file_path',''))" 2>/dev/null)" || \
FILE_PATH="$(echo "$INPUT" | grep -o '"file_path"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*: *"//;s/"$//')"

[ -z "$FILE_PATH" ] && exit 0

# Never block writes to .agents/ itself (coordination files)
case "$FILE_PATH" in
  *.agents/*|*/.agents/*) exit 0 ;;
esac

# Resolve coordination root
COORD_ROOT=""
# Try PID-scoped file first
for pidfile in .agents/registry/.coord-root-* ; do
  [ -f "$pidfile" ] && COORD_ROOT="$(cat "$pidfile")" && break
done
# Fallback: derive from git
[ -z "$COORD_ROOT" ] && COORD_ROOT="$(git rev-parse --path-format=absolute --git-common-dir 2>/dev/null | sed 's|/.git$||')" || true
[ -z "$COORD_ROOT" ] && exit 0  # Can't resolve root, allow

CLAIMS_DIR="$COORD_ROOT/.agents/claims"
[ -d "$CLAIMS_DIR" ] || exit 0  # No claims dir, allow

# Read own agent ID
MY_ID=""
for idfile in "$COORD_ROOT/.agents/registry/.current-agent-id-"* ; do
  [ -f "$idfile" ] && MY_ID="$(cat "$idfile")" && break
done

# Make file_path relative to repo root for comparison
REL_PATH="$FILE_PATH"
# Strip leading repo root if present
REL_PATH="${REL_PATH#$COORD_ROOT/}"
# Strip leading slash
REL_PATH="${REL_PATH#/}"

# Check each claim file
for claim in "$CLAIMS_DIR"/*.yaml; do
  [ -f "$claim" ] || continue

  # Extract agent_id from claim (simple grep, no YAML parser needed)
  CLAIM_AGENT="$(grep '^agent_id:' "$claim" | head -1 | sed 's/agent_id:[[:space:]]*//')"
  CLAIM_STORY="$(grep '^story_id:' "$claim" | head -1 | sed 's/story_id:[[:space:]]*//' | tr -d '"')"

  # Skip own claims
  [ "$CLAIM_AGENT" = "$MY_ID" ] && continue

  # Check each owned_path
  while IFS= read -r owned_path; do
    # Clean the path (strip "  - " prefix and whitespace)
    owned_path="$(echo "$owned_path" | sed 's/^[[:space:]]*-[[:space:]]*//' | tr -d '[:space:]')"
    [ -z "$owned_path" ] && continue

    # Prefix match: does the target file start with this owned path?
    case "$REL_PATH" in
      "$owned_path"*|"$owned_path")
        echo "BLOCKED: File '$REL_PATH' is claimed by agent $CLAIM_AGENT (story $CLAIM_STORY)." >&2
        echo "To coordinate, write a request to .agents/requests/ or wait for their claim to release." >&2
        exit 2
        ;;
    esac
  done < <(grep '^  - ' "$claim")
done

# No conflicts found — allow
exit 0
```

- [ ] **Step 3: Make executable and run tests**

```bash
chmod +x .agents/hooks/claim-check.sh .agents/hooks/test-claim-check.sh
bash .agents/hooks/test-claim-check.sh
```

Expected: All 4 tests pass

- [ ] **Step 4: Commit**

```bash
git add .agents/hooks/claim-check.sh .agents/hooks/test-claim-check.sh
git commit -m "feat: add claim-check hook — blocks edits to files claimed by other agents"
```

---

### Task 5: Create heartbeat.sh hook

**Files:**
- Create: `.agents/hooks/heartbeat.sh`

- [ ] **Step 1: Write heartbeat.sh**

This hook is simpler — it just updates a counter and periodically writes timestamps. No blocking behavior.

```bash
#!/usr/bin/env bash
# Hook: Heartbeat
# Updates agent's last_heartbeat timestamp every ~20 tool calls.
# Called by Claude Code as a PostToolUse hook (fires on every tool call).
# Maintains a counter file; only does real work every N calls.
# Exit 0 always (never blocks).

# Resolve coordination root
COORD_ROOT=""
for rootfile in .agents/registry/.coord-root-* ; do
  [ -f "$rootfile" ] && COORD_ROOT="$(cat "$rootfile")" && break
done
[ -z "$COORD_ROOT" ] && exit 0

# Read own agent ID
MY_ID=""
for idfile in "$COORD_ROOT/.agents/registry/.current-agent-id-"* ; do
  [ -f "$idfile" ] && MY_ID="$(cat "$idfile")" && break
done
[ -z "$MY_ID" ] && exit 0

COUNTER_FILE="$COORD_ROOT/.agents/registry/${MY_ID}.counter"
REGISTRY_FILE="$COORD_ROOT/.agents/registry/agent-${MY_ID}.yaml"
STATUS_FILE="$COORD_ROOT/.agents/status/agent-${MY_ID}.yaml"

# Read and increment counter
COUNT=0
[ -f "$COUNTER_FILE" ] && COUNT="$(cat "$COUNTER_FILE")"
COUNT=$((COUNT + 1))

# Check threshold (default 20)
if [ "$COUNT" -lt 20 ]; then
  echo "$COUNT" > "$COUNTER_FILE"
  exit 0
fi

# Reset counter and update heartbeat
echo "0" > "$COUNTER_FILE"
NOW="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# Update registry heartbeat (sed in-place)
if [ -f "$REGISTRY_FILE" ]; then
  sed -i '' "s/^last_heartbeat:.*$/last_heartbeat: $NOW/" "$REGISTRY_FILE" 2>/dev/null || true
fi

# Update status timestamp
if [ -f "$STATUS_FILE" ]; then
  sed -i '' "s/^last_updated:.*$/last_updated: $NOW/" "$STATUS_FILE" 2>/dev/null || true
fi

exit 0
```

- [ ] **Step 2: Make executable**

```bash
chmod +x .agents/hooks/heartbeat.sh
```

- [ ] **Step 3: Quick manual test**

```bash
# Create a mock registry file
cat > .agents/registry/agent-test01.yaml << 'EOF'
agent_id: test01
last_heartbeat: 2026-04-26T00:00:00Z
status: active
EOF
echo "test01" > .agents/registry/.current-agent-id-$$
echo "$(pwd)" > .agents/registry/.coord-root-$$

# Run heartbeat 20 times, verify counter resets and timestamp updates
for i in $(seq 1 21); do
  echo '{}' | bash .agents/hooks/heartbeat.sh
done

# Check that heartbeat was updated (should no longer be 00:00:00Z)
grep "last_heartbeat" .agents/registry/agent-test01.yaml

# Cleanup
rm -f .agents/registry/agent-test01.yaml .agents/registry/.current-agent-id-$$ .agents/registry/.coord-root-$$ .agents/registry/test01.counter
```

Expected: `last_heartbeat` shows current UTC time, not `00:00:00Z`

- [ ] **Step 4: Commit**

```bash
git add .agents/hooks/heartbeat.sh
git commit -m "feat: add heartbeat hook — periodic agent liveness updates"
```

---

### Task 6: Register hooks in Claude Code settings

**Files:**
- Modify: `.claude/settings.local.json`

- [ ] **Step 1: Read current settings**

Read `.claude/settings.local.json` to understand current structure (already known — has `permissions` and `hooks.UserPromptSubmit`).

- [ ] **Step 2: Add hook definitions**

Add the three new hook events to the existing `hooks` object in `.claude/settings.local.json`. The existing `UserPromptSubmit` hook is preserved. Add `PreToolUse` and `PostToolUse` entries:

```json
{
  "permissions": { ... },
  "hooks": {
    "UserPromptSubmit": [ ... existing ... ],
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "bash \"$CLAUDE_PROJECT_DIR/.agents/hooks/worktree-guard.sh\"",
            "timeout": 5000
          }
        ]
      },
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "bash \"$CLAUDE_PROJECT_DIR/.agents/hooks/claim-check.sh\"",
            "timeout": 5000
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "bash \"$CLAUDE_PROJECT_DIR/.agents/hooks/heartbeat.sh\"",
            "timeout": 3000
          }
        ]
      }
    ]
  }
}
```

**Key details:**
- `$CLAUDE_PROJECT_DIR` is a Claude Code variable that resolves to the project root
- The matcher `"Edit|Write"` catches both tool types for claim checking
- PostToolUse with empty matcher `""` fires on every tool call
- Heartbeat has a shorter timeout (3s) since it's lightweight

- [ ] **Step 3: Validate JSON**

```bash
python3 -c "import json; json.load(open('.claude/settings.local.json'))" && echo "VALID" || echo "INVALID"
```

Expected: `VALID`

- [ ] **Step 4: Commit**

```bash
git add .claude/settings.local.json
git commit -m "feat: register coordination hooks in Claude Code settings"
```

---

## Chunk 3: Startup Slash Command

The `/agent-coordinator` command implements the full startup protocol from spec Section 5.1.

### Task 7: Create agent-coordinator slash command

**Files:**
- Create: `claude-commands/team/agent-coordinator.md`

- [ ] **Step 1: Write the slash command**

```markdown
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
```

- [ ] **Step 2: Verify frontmatter matches project conventions**

Compare with existing slash commands (e.g., `claude-commands/team/dev.md`). The frontmatter should have `name` and `description` fields.

- [ ] **Step 3: Commit**

```bash
git add claude-commands/team/agent-coordinator.md
git commit -m "feat: add /agent-coordinator startup slash command"
```

---

## Chunk 4: Shutdown Slash Command

### Task 8: Create agent-shutdown slash command

**Files:**
- Create: `claude-commands/team/agent-shutdown.md`

- [ ] **Step 1: Write the slash command**

```markdown
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
```

- [ ] **Step 2: Commit**

```bash
git add claude-commands/team/agent-shutdown.md
git commit -m "feat: add /agent-shutdown slash command"
```

---

## Chunk 5: Maestro Integration Layer

These modifications extend existing Maestro-system files to cross-post coordination events.

### Task 9: Bootstrap _comms directory and extend agent-comms.xml

**Files:**
- Create: `team/_memory/_comms/{proposals,findings,requests,handoffs,broadcasts}/.gitkeep`
- Modify: `team/engine/agent-comms.xml` (add cross-post protocol section)

- [ ] **Step 1: Create _comms directory tree**

```bash
mkdir -p team/_memory/_comms/{proposals,findings,requests,handoffs,broadcasts}
for dir in team/_memory/_comms/*/; do
  touch "$dir/.gitkeep"
done
```

- [ ] **Step 2: Verify structure**

```bash
find team/_memory/_comms -type f
```

Expected: 5 `.gitkeep` files

- [ ] **Step 3: Extend agent-comms.xml**

Read the current `team/engine/agent-comms.xml` in full. Add a new section before the closing `</task>` tag — a `<coordination-bridge>` section that documents the cross-post protocol between `.agents/` and `_comms/`:

```xml
  <!-- ═══════════════════════════════════════════════════ -->
  <!-- COORDINATION BRIDGE: .agents/ ↔ _comms/            -->
  <!-- ═══════════════════════════════════════════════════ -->
  <coordination-bridge>
    <desc>When multi-agent coordination is active (.agents/ directory exists),
    agents cross-post all coordination events to Maestro's _comms/ channel.
    This preserves Maestro's hub mandate while enabling autonomous coordination.</desc>

    <rule>ALL .agents/decisions/ entries cross-post to findings/ using _comms/ naming: {date}-{from}-finding-{slug}.md</rule>
    <rule>ALL .agents/requests/ entries cross-post to requests/ using _comms/ naming: {date}-{from}-request-{slug}.md</rule>
    <rule>ALL .agents/status/*-handoff.yaml entries cross-post to handoffs/ using _comms/ naming: {date}-{from}-handoff-{slug}.md</rule>
    <rule>Security findings use [SECURITY] prefix in both surfaces</rule>
    <rule>Cross-posting is the responsibility of the agent writing the .agents/ file — write to both locations atomically</rule>
  </coordination-bridge>
```

- [ ] **Step 4: Commit**

```bash
git add team/_memory/_comms/ team/engine/agent-comms.xml
git commit -m "feat: bootstrap _comms directory and add coordination bridge to agent-comms.xml"
```

---

### Task 10: Extend SH workflow with coordination context

**Files:**
- Modify: `team/workflows/navigator/session-handoff/instructions.md`

- [ ] **Step 1: Read current SH instructions in full**

Read `team/workflows/navigator/session-handoff/instructions.md` completely.

- [ ] **Step 2: Add coordination context to Step 7**

Find `## Step 7: Generate Handoff Report` in the instructions. Within that step's report template (the code block showing the report format), add a `## Coordination Context` section after `## Open Issues`:

```markdown
## Coordination Context

If `.agents/registry/` exists and contains agent files, include:

| Agent | Branch | Story | Status | Last Seen |
|-------|--------|-------|--------|-----------|
{for each .agents/registry/agent-*.yaml: agent_id, branch, story_id, status, time since last_heartbeat}

Decisions Made Today:
{for each .agents/decisions/*.yaml where date = today: decision summary and decided_by}

Unresolved Requests:
{for each .agents/requests/*.yaml where responded_at = null and (to = this agent or to = "any"): subject}

If `.agents/` does not exist, omit this section entirely.
```

The key: this section is only included when `.agents/` exists, making it a no-op in non-coordinated repos.

- [ ] **Step 3: Commit**

```bash
git add team/workflows/navigator/session-handoff/instructions.md
git commit -m "feat: extend SH Step 7 with coordination context section"
```

---

### Task 11: Extend CR workflow with claim awareness

**Files:**
- Modify: `team/workflows/implementation/code-review/instructions.xml`

- [ ] **Step 1: Read current CR instructions in full**

Read `team/workflows/implementation/code-review/instructions.xml` completely.

- [ ] **Step 2: Add pre-review claim check to Step 1**

Within `<step n="1">`, after the initial story loading actions but before the file reading begins, add:

```xml
    <!-- Coordination awareness: check if story is actively being developed -->
    <check if=".agents/claims/ directory exists">
      <action>Read all .agents/claims/*.yaml files</action>
      <action>For each claim, check if claim's story_id matches the story being reviewed AND the claim's agent status is "active"</action>
      <check if="active claim found for this story">
        <action>Add to review context: "[WARNING: Active Development] Story {story_id} is actively being modified by agent {agent_id}. Findings may be against a moving target — flag time-sensitive issues with higher priority."</action>
      </check>
    </check>
```

- [ ] **Step 3: Add post-review decision posting**

Find the final step of the CR workflow (where the review report is generated). After the report is written, add:

```xml
    <!-- Post-review: cross-post architectural findings to coordination layer -->
    <check if=".agents/decisions/ directory exists">
      <action>For each CRITICAL or HIGH severity architectural finding in the review:
        Write to .agents/decisions/{date}-cr-{slug}.yaml:
          decided_by: {reviewing agent id or "code-review"}
          story_id: {reviewed story id}
          date: {today}
          decision: {finding summary}
          rationale: {from review analysis}
          affects_agents: all
          acknowledged_by: []
      </action>
      <action>For each finding that affects files in another agent's owned_paths (from .agents/claims/):
        Write a request to .agents/requests/ addressed to that agent with type: review-needed
      </action>
    </check>
```

- [ ] **Step 4: Commit**

```bash
git add team/workflows/implementation/code-review/instructions.xml
git commit -m "feat: extend CR with claim awareness and decision cross-posting"
```

---

### Task 12: Extend Maestro scan-and-plan with .agents/ awareness

**Files:**
- Modify: `team/workflows/maestro/scan-and-plan/instructions.xml`

- [ ] **Step 1: Read current scan-and-plan instructions**

Read `team/workflows/maestro/scan-and-plan/instructions.xml` completely.

- [ ] **Step 2: Add .agents/ scan to Phase 1 (Project Discovery)**

Within `<step n="1">`, after the existing project scans, add:

```xml
    <!-- Multi-agent coordination awareness -->
    <action>Check if {project-root}/.agents/registry/ exists and contains agent files</action>
    <check if=".agents/ coordination is active">
      <action>Read all .agents/registry/agent-*.yaml — store as {active_agents}</action>
      <action>Read all .agents/claims/*.yaml — store as {active_claims}</action>
      <action>Read all .agents/decisions/*.yaml — store as {recent_decisions}</action>
      <action>Read all .agents/status/*-orphaned.yaml — store as {orphaned_agents}</action>
      <action>Display: "Multi-agent coordination detected. {N} active agents, {M} active claims."</action>
      <action>If orphaned agents found, display: "⚠️ {K} orphaned agent worktrees need review."</action>
    </check>
```

- [ ] **Step 3: Add coordination-aware agent assignment**

In the agent assignment phase (where Maestro assigns work to agents), add awareness of existing claims:

```xml
    <!-- When assigning work, respect existing agent claims -->
    <check if="{active_claims} is not empty">
      <action>For each story being assigned: check if it is already claimed in {active_claims}</action>
      <action>If claimed: skip assignment, note "Already claimed by agent {id}"</action>
      <action>If not claimed: proceed with normal assignment</action>
      <action>Include active agent summary in the battle plan output</action>
    </check>
```

- [ ] **Step 4: Commit**

```bash
git add team/workflows/maestro/scan-and-plan/instructions.xml
git commit -m "feat: extend Maestro scan-and-plan with .agents/ coordination awareness"
```

---

## Chunk 6: Verification

### Task 13: End-to-end manual verification

- [ ] **Step 1: Verify directory structure**

```bash
find .agents -type f | sort
```

Expected: config.yaml, .gitkeep files in each subdir, 3 hook scripts, 1 test script per hook

- [ ] **Step 2: Verify hooks are valid bash**

```bash
bash -n .agents/hooks/worktree-guard.sh && echo "worktree-guard: OK"
bash -n .agents/hooks/claim-check.sh && echo "claim-check: OK"
bash -n .agents/hooks/heartbeat.sh && echo "heartbeat: OK"
```

Expected: All 3 show OK (syntax valid)

- [ ] **Step 3: Run hook test suites**

```bash
bash .agents/hooks/test-worktree-guard.sh
bash .agents/hooks/test-claim-check.sh
```

Expected: All tests pass

- [ ] **Step 4: Verify settings.json is valid**

```bash
python3 -c "import json; j=json.load(open('.claude/settings.local.json')); print('Hooks:', list(j.get('hooks',{}).keys()))"
```

Expected: `Hooks: ['UserPromptSubmit', 'PreToolUse', 'PostToolUse']`

- [ ] **Step 5: Verify slash commands exist**

```bash
ls -la claude-commands/team/agent-coordinator.md claude-commands/team/agent-shutdown.md
```

Expected: Both files exist

- [ ] **Step 6: Verify .gitignore**

```bash
grep "worktrees" .gitignore && echo "OK"
```

Expected: `OK`

- [ ] **Step 7: Verify Maestro integration files**

```bash
ls team/_memory/_comms/*/. 2>/dev/null | wc -l
grep "coordination-bridge" team/engine/agent-comms.xml && echo "Bridge: OK"
```

Expected: 5 directories, Bridge: OK

- [ ] **Step 8: Final commit check**

```bash
git log --oneline -10
git status
```

Expected: Clean working tree, commits for all chunks visible in log
