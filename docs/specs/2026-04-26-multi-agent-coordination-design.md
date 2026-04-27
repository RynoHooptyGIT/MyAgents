# Multi-Agent Coordination System

**Date**: 2026-04-26
**Status**: Draft (Rev 1 — post-review fixes applied)
**Author**: CEO + Claude
**Scope**: Multi-instance Claude Code coordination for parallel autonomous development

---

## Problem Statement

When multiple Claude Code instances run simultaneously in the same VS Code window, they share a single working directory and git state. This causes:

1. **Branch corruption**: Instance A checks out `feature/auth`, Instance B's working directory changes underneath it, leading to commits on wrong branches
2. **File conflicts**: Two instances edit the same file, one overwrites the other
3. **Redundant work**: Instances independently solve the same problem
4. **Architectural drift**: Conflicting design decisions (REST vs GraphQL for the same feature)
5. **Context loss**: An instance finishes work but the next instance doesn't know what was done
6. **Priority blindness**: Low-priority work proceeds while critical issues sit unaddressed

The root cause is a **shared working directory** with no coordination protocol between independent Claude Code processes.

## Design Goals

- **Fully autonomous**: Agents self-coordinate without human traffic control
- **Variable scale**: Works whether 2 or 8+ agents are running simultaneously
- **Layered portability**: Portable core works in any git repo; Maestro integration adds richer features when present
- **Enforced + conventional**: Hooks provide hard guardrails; conventions enable richer coordination behaviors
- **Non-breaking**: Existing CR and SH workflows are preserved and extended, not modified

## Non-Goals

- Cross-machine coordination (all agents are on the same machine)
- Agent-to-agent direct messaging (file-based shared state instead)
- Daemon processes or background services
- Changes to the workflow engine (`workflow.xml`)
- Replacing Agent Teams (this complements Agent Teams for cross-session coordination)

---

## Architecture Overview

```
my-project/                        (Main repo — coordination hub only)
├── .agents/                       (Shared coordination surface)
│   ├── config.yaml                (Coordination settings)
│   ├── registry/                  (Agent presence — who's alive)
│   │   ├── agent-a1b2c3.yaml
│   │   └── agent-d4e5f6.yaml
│   ├── claims/                    (Work ownership — who's doing what)
│   │   ├── feature-auth.yaml
│   │   └── feature-dashboard.yaml
│   ├── decisions/                 (Architectural decisions log)
│   │   └── 2026-04-26-rest-api.yaml
│   ├── status/                    (Per-agent current state + handoffs)
│   │   ├── agent-a1b2c3.yaml
│   │   └── agent-a1b2c3-handoff.yaml
│   └── requests/                  (Inter-agent requests)
│       └── a1b2c3-to-d4e5f6.yaml
├── .worktrees/                    (Git worktree roots — gitignored)
│   ├── agent-a1b2c3/             (Instance A's isolated checkout)
│   └── agent-d4e5f6/             (Instance B's isolated checkout)
└── team/                          (Maestro system — when present)
    └── _memory/_comms/            (Maestro's comms channel — cross-posted)
```

**Key invariant**: No Claude instance ever operates in the main repo checkout. Every instance works in its own git worktree.

---

## Section 1: Worktree Isolation

### Purpose

Eliminate the root cause — shared working directory — by giving each agent its own isolated copy of the repo. Git worktrees share the same `.git` directory but have independent working directories and can each be on a different branch.

### Startup Sequence

1. Agent generates a unique ID: 6-character hex hash from `$(date +%s%N | shasum | head -c 6)`
2. Agent checks: "Am I already in a git worktree?" by comparing git directories:
   ```bash
   GIT_DIR="$(git rev-parse --git-dir)"
   GIT_COMMON="$(git rev-parse --git-common-dir)"
   if [ "$GIT_DIR" != "$GIT_COMMON" ]; then
     # We ARE in a worktree — already isolated
   else
     # We are in the main repo — need to create a worktree
   fi
   ```
   - **In worktree**: Already isolated, extract agent_id from worktree path, continue
   - **In main repo**: Create worktree: `git worktree add .worktrees/agent-{id} -b agent/{id}/{task-slug}`
3. Agent changes its working context to the worktree directory
4. All subsequent operations happen inside the worktree

### Shutdown Sequence

1. Commit all work: `git add -A && git commit`
2. Push branch: `git push origin agent/{id}/{task-slug}`
3. Run Session Handoff workflow (inside worktree context)
4. Remove worktree: `git worktree remove .worktrees/agent-{id}`

### Directory Conventions

- `.worktrees/` is added to `.gitignore` — worktrees are ephemeral, never committed
- `.agents/` is NOT gitignored — it is the shared coordination surface, located in the main repo root. Worktrees access it via the resolved `AGENT_COORD_ROOT` path (see Worktree ↔ .agents/ Visibility)
- Branch naming: `agent/{id}/{task-slug}` (e.g., `agent/a1b2c3/jwt-auth`)
- Worktree path: `.worktrees/agent-{id}/`

### Worktree ↔ .agents/ Visibility

Git worktrees share the `.git` object database (commits, branches, refs) but do NOT share working directories. `.agents/` lives in the main repo's working tree and is not automatically visible from worktree checkouts.

**Resolution mechanism**: On startup, the agent resolves the main repo root and stores it for all subsequent coordination operations:

```bash
# From within the worktree, resolve the main repo root:
AGENT_COORD_ROOT="$(git rev-parse --path-format=absolute --git-common-dir | sed 's|/.git$||')"

# All coordination paths are then:
# $AGENT_COORD_ROOT/.agents/registry/
# $AGENT_COORD_ROOT/.agents/claims/
# etc.
```

This path is written to a file within the worktree (`.worktrees/agent-{id}/.agent-coord-root`) so hooks and periodic behaviors can read it without re-resolving. All references to `.agents/` throughout this spec are shorthand for `$AGENT_COORD_ROOT/.agents/`.

---

## Section 2: Coordination Layer

### 2.1 Registry (Agent Presence)

Each agent writes a registration file on startup and updates it periodically.

**File**: `.agents/registry/agent-{id}.yaml`

```yaml
agent_id: a1b2c3
pid: 48291
worktree: .worktrees/agent-a1b2c3
branch: agent/a1b2c3/jwt-auth
started_at: 2026-04-26T14:30:00Z
last_heartbeat: 2026-04-26T14:35:00Z
persona: dev
task_summary: "Implementing JWT auth for Epic 24, Story 24-3"
story_id: "24-3"
status: active  # active | paused | completing | shutting-down
```

**Heartbeat**: Updated every ~20 tool calls (approximately 2 minutes). Agents with `last_heartbeat` older than `stale_threshold_minutes` (default: 10) are considered dead.

**Stale cleanup**: On startup, each agent scans the registry. For entries older than the stale threshold, it checks `kill -0 {pid}`. If the process is gone, the entry is cleaned up (see Crash Recovery).

### 2.2 Claims (Work Ownership)

Before starting work, an agent writes a claim file declaring what it owns.

**File**: `.agents/claims/{feature-slug}.yaml`

```yaml
agent_id: a1b2c3
branch: agent/a1b2c3/jwt-auth
story_id: "24-3"
claimed_at: 2026-04-26T14:30:00Z
owned_paths:
  - backend/app/auth/
  - backend/app/models/user.py
  - backend/tests/test_auth/
description: "JWT authentication system - login, refresh, logout endpoints"
```

**Conflict check protocol** (with atomic mutex to prevent TOCTOU race):

```
1. Acquire mutex:  mkdir .agents/claims/{feature-slug}.lock
   - If mkdir FAILS (directory exists) → another agent is claiming simultaneously
     → Back off (sleep 1-2s), re-read claims, retry from step 1 (max 3 retries)
   - If mkdir SUCCEEDS → proceed with exclusive access

2. Read all .agents/claims/*.yaml
3. Check for overlap on story_id — same story cannot be claimed by two agents
4. Check for overlap on owned_paths — path prefix matching
   (if agent A claims backend/app/auth/, agent B cannot claim backend/app/auth/router.py)
5. If conflict detected:
   → Remove mutex: rmdir .agents/claims/{feature-slug}.lock
   → STOP, do not proceed, log conflict to .agents/status/
6. If no conflict:
   → Write .agents/claims/{feature-slug}.yaml
   → Remove mutex: rmdir .agents/claims/{feature-slug}.lock
   → Proceed
```

**Why `mkdir`**: Directory creation is atomic on POSIX filesystems (including macOS APFS). Unlike file writes, `mkdir` either succeeds or fails — there is no partial state. This closes the check-then-write race window that would allow two agents to claim the same work simultaneously.

**Claim release**: On shutdown, the agent deletes its claim file (and mutex dir if present). On crash, the next startup agent cleans it up via stale detection.

### 2.3 Decisions (Architectural Log)

When an agent makes an architectural decision that could affect other agents, it writes a decision record.

**File**: `.agents/decisions/{date}-{slug}.yaml`

```yaml
decided_by: a1b2c3
story_id: "24-3"
date: 2026-04-26
decision: "Auth endpoints use REST with JSON responses, not GraphQL"
rationale: "Simpler for auth flows, consistent with existing API patterns"
affects_agents: all  # "all" or list of specific agent IDs
acknowledged_by: []  # Other agents append their ID after reading
```

**Acknowledgment protocol**: On startup and periodically during work, agents scan `decisions/` for entries where `acknowledged_by` does not contain their `agent_id`. They read the decision, incorporate it into their context, and append their ID to `acknowledged_by`.

### 2.4 Requests (Inter-Agent Communication)

When an agent needs input from another agent, it writes a request file.

**File**: `.agents/requests/{from-id}-to-{to-id}-{slug}.yaml`

```yaml
from: a1b2c3
to: d4e5f6  # or "any" for whoever picks it up
date: 2026-04-26T15:00:00Z
type: input-needed  # input-needed | review-needed | work-needed
blocking: false
subject: "Need User model schema before I can implement auth endpoints"
context: "Auth system requires user_id, email, password_hash fields minimum"
response: null  # Target agent fills this in
responded_at: null
```

**Processing**: Agents periodically scan `requests/` for entries addressed to them. They write their response into the `response` field and set `responded_at`. The requesting agent polls for the response.

### 2.5 Status (Current State)

Each agent maintains a status file reflecting its current state.

**File**: `.agents/status/agent-{id}.yaml`

```yaml
agent_id: a1b2c3
current_task: "Implementing login endpoint"
progress: "3/7 endpoints complete"
last_updated: 2026-04-26T14:45:00Z
files_modified_this_session:
  - backend/app/auth/router.py
  - backend/app/auth/service.py
  - backend/app/auth/schemas.py
blockers: []
warnings: []
```

---

## Section 3: Workflow Integration

### 3.1 Session Handoff (SH) Integration

The existing SH workflow (Steps 1-8) runs unchanged inside the agent's worktree. Git commands (`git log`, `git status`, `git diff`) automatically scope to the worktree's branch and working directory.

**Addition**: Step 7 (Generate Handoff Report) is extended to include a `## Coordination Context` section in the report output. This is an additive extension to Step 7's report generation — not a new step. The SH instructions.md file is modified only to add this section within the existing Step 7 template.

**Coordination Context gathering** (performed as part of Step 7):

1. Read all `.agents/registry/*.yaml` — list active agents
2. Read all `.agents/claims/*.yaml` — list in-flight work
3. Read all `.agents/decisions/*.yaml` with `date` matching today — list decisions
4. Check `.agents/requests/` for unresolved requests involving this agent
5. Include a `## Coordination Context` section in the handoff report:

```
## Coordination Context
Active Agents: 3
| Agent    | Branch              | Story | Status    | Last Seen  |
|----------|---------------------|-------|-----------|------------|
| a1b2c3   | agent/a1b2c3/auth   | 24-3  | completing| now        |
| d4e5f6   | agent/d4e5f6/dash   | 24-5  | active    | 1 min ago  |
| g7h8i9   | agent/g7h8i9/tests  | 24-4  | active    | 3 min ago  |

Decisions Made This Session:
- REST endpoints for auth (not GraphQL) — by a1b2c3 on 2026-04-26

Unresolved Requests:
- None

Potential Conflicts:
- None detected
```

**The existing 8-step structure is preserved.** Step 7's report template gains an additional section. No steps are added, removed, or reordered.

### 3.2 Code Review (CR) Integration

The existing CR workflow runs unchanged. Two additions:

**Pre-review check** (added to CR review preamble, non-blocking):

1. Read `.agents/claims/*.yaml`
2. If the story being reviewed is actively claimed by another agent (status: active), add a `[WARNING: Active Development]` notice to the review context: "Story {id} is actively being modified by agent {agent_id}. Findings may be against a moving target — flag time-sensitive issues with higher priority."
3. If not claimed or agent is in `completing` status, proceed normally without warning

This is a non-blocking annotation, not a prompt. The CR workflow's adversarial review mode runs uninterrupted.

**Post-review decision posting** (after CR completes):

1. For each architectural finding in the CR results, write to `.agents/decisions/`
2. If the CR identifies changes that affect files in another agent's `owned_paths`, write a finding to `.agents/requests/` addressed to that agent

### 3.3 Sprint Status Awareness

When an agent selects work during startup (Step 5 of the lifecycle), it cross-references:

1. `sprint-status.yaml` — stories available for work
2. `.agents/claims/*.yaml` — stories already claimed

Only unclaimed stories with status `ready-for-dev` or `backlog` are eligible for selection.

---

## Section 4: Hook Enforcement

Three Claude Code hooks provide hard guardrails that cannot be rationalized away.

### Agent Identity on Disk

Since Claude Code does not persist environment variables between Bash tool calls, the agent ID and coordination root are stored on disk:

- **During startup**: Write `{agent_id}` to `.agents/registry/.current-agent-id-{pid}` (PID-scoped to avoid conflicts between instances)
- **Hooks read identity from**: The hook script determines its agent ID by reading `.agents/registry/.current-agent-id-{$$}` where `$$` is the parent Claude process PID
- **Coordination root**: Also written to the worktree at `.worktrees/agent-{id}/.agent-coord-root`

### Hook 1: Worktree Guard

**Event**: `PreToolUse` with tool matcher `Bash`
**Purpose**: Prevent branch-switching operations in the main repo

**Claude Code hook definition** (in `.claude/settings.json`):

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "command": "bash .agents/hooks/worktree-guard.sh"
      }
    ]
  }
}
```

**Hook script logic** (`.agents/hooks/worktree-guard.sh`):

The hook receives the tool input via `$CLAUDE_TOOL_INPUT` (JSON containing the `command` field). It:

1. Extracts the command string from the tool input
2. Checks if the command matches: `git checkout`, `git switch`, `git merge`, `git rebase`
3. Checks if the current working directory is inside a worktree:
   ```bash
   GIT_DIR="$(git rev-parse --git-dir 2>/dev/null)"
   GIT_COMMON="$(git rev-parse --git-common-dir 2>/dev/null)"
   if [ "$GIT_DIR" = "$GIT_COMMON" ]; then
     # We are in the main repo, NOT a worktree — block
   fi
   ```
4. If in main repo AND command is a branch operation → exit non-zero with message:
   `"BLOCKED: Branch operations not allowed in main repo. Use your assigned worktree."`
5. If in a worktree → exit 0 (allow)

**Also blocks**: `cd` commands targeting another agent's worktree directory.

**Does NOT block**: Git operations inside the agent's own worktree (normal workflow).

### Hook 2: Claim Check

**Event**: `PreToolUse` with tool matcher `Edit,Write`
**Purpose**: Prevent editing files claimed by another agent

**Claude Code hook definition**:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit,Write",
        "command": "bash .agents/hooks/claim-check.sh"
      }
    ]
  }
}
```

**Hook script logic** (`.agents/hooks/claim-check.sh`):

1. Read agent ID from `.agents/registry/.current-agent-id-{ppid}`
2. Read coordination root from disk
3. Extract target file path from `$CLAUDE_TOOL_INPUT`
4. For each `.agents/claims/*.yaml`:
   - Extract `agent_id` and `owned_paths`
   - If `agent_id` matches self → skip (own claim)
   - For each `owned_path`: check if target file starts with that prefix
   - If match found → exit non-zero:
     `"BLOCKED: File {path} is claimed by agent {agent_id} (story {story_id})."`
5. No match → exit 0 (allow)

**Path matching**: Prefix-based. If agent A claims `backend/app/auth/`, any file under that directory is protected. Exact file claims (e.g., `backend/app/models/user.py`) protect only that file.

### Hook 3: Heartbeat

**Event**: `PostToolUse` (fires on every tool call)
**Purpose**: Keep the agent's registry entry fresh so other agents know it's alive

**Claude Code hook definition**:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "command": "bash .agents/hooks/heartbeat.sh"
      }
    ]
  }
}
```

**Hook script logic** (`.agents/hooks/heartbeat.sh`):

1. Read agent ID from disk
2. Read counter from `.agents/registry/agent-{id}.counter` (default: 0)
3. Increment counter
4. If counter < 20 → write counter, exit (skip heartbeat)
5. If counter >= 20 → reset counter to 0, update timestamps:
   - `.agents/registry/agent-{id}.yaml` → `last_heartbeat: {ISO 8601}`
   - `.agents/status/agent-{id}.yaml` → `last_updated: {ISO 8601}`

**Lightweight**: Only writes a counter file on most calls. Full YAML update every ~20 calls.

### Hook Implementation Notes

- All hooks are shell scripts stored in `.agents/hooks/` (committed to repo, portable)
- Hook definitions go in `.claude/settings.json` (project-level) or `.claude/settings.local.json`
- Hooks read agent identity from PID-scoped files on disk, not environment variables
- Hooks resolve `.agents/` path from the git common directory, not from cwd
- If hook scripts are missing (repo without coordination), hooks no-op gracefully (exit 0)

---

## Section 5: Agent Lifecycle

### 5.1 Startup Protocol

Implemented as the `agent-coordinator` slash command (`claude-commands/team/agent-coordinator.md`).

```
STEP 1: Generate Identity
  → agent_id = $(date +%s%N | shasum | head -c 6)
  → Store identity on disk (PID-scoped):
    Write agent_id to .agents/registry/.current-agent-id-{pid}
  → Resolve and store coordination root:
    AGENT_COORD_ROOT = $(git rev-parse --path-format=absolute --git-common-dir | sed 's|/.git$||')
    Write to .agents/registry/.coord-root-{pid}

STEP 2: Create Worktree
  → Check: am I already in a worktree?
    (compare: git rev-parse --git-dir vs --git-common-dir — if different, already in worktree)
    YES → Use current worktree, extract agent_id from path
    NO  → Determine task slug from user request or sprint-status
        → git worktree add .worktrees/agent-{id} -b agent/{id}/{slug}
        → Set working context to worktree
  → Write AGENT_COORD_ROOT to .worktrees/agent-{id}/.agent-coord-root

STEP 3: Scan and Clean Registry
  → Read all .agents/registry/*.yaml
  → For each entry where last_heartbeat > stale_threshold:
    → kill -0 {pid} to check if process is running
    → If dead: run crash recovery protocol (Section 5.3)
  → Log active agents to own context

STEP 4: Register Self
  → Write .agents/registry/agent-{id}.yaml
    (agent_id, pid, worktree, branch, started_at, persona, status: active)

STEP 5: Claim Work
  → Read sprint-status.yaml for available stories
  → Read .agents/claims/*.yaml for already-claimed work
  → Filter: unclaimed stories with status ready-for-dev or in-progress (assigned to this agent's persona)
  → Select highest-priority unclaimed story
  → Check owned_paths for conflicts with existing claims
  → Write .agents/claims/{feature-slug}.yaml

STEP 6: Sync Decisions
  → Read all .agents/decisions/*.yaml
  → Filter: acknowledged_by does not contain own agent_id
  → Incorporate each decision into context
  → Append own agent_id to acknowledged_by for each

STEP 7: Begin Work
  → Execute assigned workflow (dev-story, CR, etc.) inside worktree
```

### 5.2 Shutdown Protocol

Implemented as the `agent-shutdown` slash command (`claude-commands/team/agent-shutdown.md`).

```
STEP 1: Commit Work
  → git add -A && git commit (inside worktree)
  → Commit message includes agent_id and story_id

STEP 2: Push Branch
  → git push origin agent/{id}/{slug}

STEP 3: Run Session Handoff
  → Execute SH workflow inside worktree context
  → Includes coordination context section (Section 3.1)
  → Write handoff summary to .agents/status/agent-{id}-handoff.yaml

STEP 4: Release Claim
  → Delete .agents/claims/{feature-slug}.yaml
  → Remove mutex dir if present: rmdir .agents/claims/{feature-slug}.lock

STEP 5: Remove Worktree
  → git worktree remove .worktrees/agent-{id}

STEP 6: Deregister
  → Delete .agents/registry/agent-{id}.yaml
  → Delete .agents/registry/.current-agent-id-{pid}
  → Delete .agents/registry/.coord-root-{pid}
  → Delete .agents/status/agent-{id}.yaml
```

### 5.3 Crash Recovery

When an agent dies without running the shutdown protocol:

```
DETECTED BY: Next agent to start (Step 3 of startup)

CONDITION: Registry entry exists with last_heartbeat > stale_threshold
           AND kill -0 {pid} returns non-zero (process not running)

RECOVERY:
  1. Check worktree for uncommitted work:
     → git -C .worktrees/agent-{id} status --porcelain

  2. IF uncommitted work exists:
     → Leave worktree intact
     → Write .agents/status/agent-{id}-orphaned.yaml:
       orphaned_at: {timestamp}
       worktree: .worktrees/agent-{id}
       branch: {branch from registry}
       uncommitted_files: [list from git status]
       action_needed: "Review uncommitted work, commit or discard"
     → Remove registry entry
     → Release claim (delete claim file)

  3. IF worktree is clean (all committed):
     → git worktree remove .worktrees/agent-{id}
     → Delete registry entry
     → Release claim

  4. Log recovery action to .agents/status/recovery-log.yaml:
     - timestamp: {ISO 8601}
       recovered_agent_id: {id}
       action: "cleaned_worktree" | "flagged_orphaned" | "released_claim"
       outcome: "success" | "partial — uncommitted work preserved"
       recovered_by: {recovering agent's id}
```

### 5.4 Work Phase Behaviors

During active work, agents follow these conventions (enforced by CLAUDE.md instructions and the startup skill):

| Behavior | Trigger | Action |
|----------|---------|--------|
| Heartbeat | Every ~20 tool calls | Update registry + status timestamps |
| Decision sync | Before architectural choices | Read decisions/, post new ones |
| Request check | Every ~50 tool calls | Scan requests/ for messages addressed to self |
| Claim validation | Before editing new files outside owned_paths | Check claims, expand own claim if unclaimed |
| Status update | On task milestone | Update status/ with current progress |

---

## Section 6: Maestro Integration Layer

When the Maestro system is present (`team/engine/` exists), the coordination layer gains additional capabilities. These are purely additive — the portable core works without them.

### Detection

On startup, `/agent-coordinator` checks for `team/engine/agent-comms.xml`. If present, Maestro integration is enabled.

### Bootstrap

The `team/_memory/_comms/` directory tree may not exist yet (agent-comms.xml defines the structure but it is not pre-materialized). On first Maestro-integrated startup, create the directory tree if missing:

```
team/_memory/_comms/
├── proposals/
├── findings/
├── requests/
├── handoffs/
└── broadcasts/
```

### Startup Additions

After portable core Step 6 (Sync Decisions):

- Read `team/_memory/_comms/broadcasts/` for team-wide directives
- Read `team/_memory/{agent-persona}/mission.md` for pre-assigned work from Maestro
- If Maestro has pre-assigned a story, use that instead of auto-selecting from sprint-status

### Work Phase Additions

Per `agent-comms.xml` mandate ("ALL inter-agent communication flows through Maestro"), when Maestro integration is enabled, ALL `.agents/` coordination events are cross-posted to the corresponding `_comms/` directory:

- ALL decisions: write to both `.agents/decisions/` AND `team/_memory/_comms/findings/`
- ALL requests: write to both `.agents/requests/` AND `team/_memory/_comms/requests/` (not just blocking requests — Maestro must see all inter-agent communication)
- Security findings: [SECURITY] flag per agent-comms.xml protocol, written to both surfaces

Cross-posted files adopt the `_comms/` naming convention (`{date}-{from}-{type}-{slug}.md`) rather than the `.agents/` convention, per agent-comms.xml rule on line 149.

### Shutdown Additions

- Session handoff also written to `team/_memory/_comms/handoffs/` for Maestro triage (using `_comms/` naming convention)
- Maestro picks up completed work during next scan-and-plan and updates sprint-status.yaml

### Configuration

```yaml
# .agents/config.yaml — maestro_integration section
maestro_integration:
  enabled: auto          # auto-detected from team/engine/ presence
  cross_post_decisions: true
  cross_post_handoffs: true
  cross_post_findings: true
  respect_mission_assignments: true
```

---

## Section 7: Configuration

### `.agents/config.yaml`

```yaml
coordination:
  # Heartbeat
  heartbeat_interval_calls: 20       # Update heartbeat every N tool calls
  stale_threshold_minutes: 10        # Consider agent dead after N minutes no heartbeat

  # Claims
  claim_conflict_action: block       # block | warn | allow
  claim_path_matching: prefix        # prefix | exact

  # Worktrees
  auto_worktree: true                # Enforce worktree creation on startup
  worktree_base_dir: .worktrees     # Relative to repo root
  cleanup_orphaned_worktrees: true   # Clean stale worktrees on startup
  branch_prefix: agent               # Branch naming: {prefix}/{id}/{slug}

  # Decisions
  decision_sync_on_startup: true     # Read all decisions on startup
  decision_sync_interval_calls: 100  # Periodic re-sync (in addition to event-driven sync before architectural choices)

  # Requests
  request_check_interval_calls: 50   # Check for inbound requests periodically

maestro_integration:
  enabled: auto
  cross_post_decisions: true
  cross_post_handoffs: true
  cross_post_findings: true
  respect_mission_assignments: true
```

### `.gitignore` Additions

```
# Agent worktrees (ephemeral)
.worktrees/
```

### CLAUDE.md Additions

**Note**: No `CLAUDE.md` file currently exists in the project root. One must be created as part of implementation (deliverable #9). The following section should be included:

```markdown
## Multi-Agent Coordination

This project uses the multi-agent coordination protocol. When running as one
of multiple simultaneous Claude instances:

1. Always run `/agent-coordinator` before beginning work
2. Always run `/agent-shutdown` before ending your session
3. Never operate in the main repo checkout — use your assigned worktree
4. Check `.agents/decisions/` before making architectural choices
5. Write decisions that affect other agents to `.agents/decisions/`
6. Respect file ownership — do not edit files claimed by other agents
```

---

## Section 8: Implementation Deliverables

### Portable Core

| # | Artifact | Path | Description |
|---|----------|------|-------------|
| 1 | Coordination config | `.agents/config.yaml` | Coordination settings with defaults |
| 2 | Startup slash command | `claude-commands/team/agent-coordinator.md` | Startup protocol: worktree, register, claim, sync |
| 3 | Shutdown slash command | `claude-commands/team/agent-shutdown.md` | Shutdown protocol: commit, push, SH, release, cleanup |
| 4 | Worktree Guard hook script | `.agents/hooks/worktree-guard.sh` | Blocks branch ops in main repo |
| 5 | Claim Check hook script | `.agents/hooks/claim-check.sh` | Blocks edits to files claimed by other agents |
| 6 | Heartbeat hook script | `.agents/hooks/heartbeat.sh` | Periodic heartbeat updates |
| 7 | Hook registration | `.claude/settings.json` (additions) | PreToolUse/PostToolUse hook definitions |
| 8 | Directory scaffold | `.agents/{registry,claims,decisions,status,requests,hooks}/` | Coordination directory tree |
| 9 | Gitignore update | `.gitignore` | Add `.worktrees/` |
| 10 | Project instructions | `CLAUDE.md` (new file) | Multi-agent coordination instructions |

### Maestro Integration Layer

| # | Artifact | Path | Description |
|---|----------|------|-------------|
| 11 | Comms cross-post protocol | `team/engine/agent-comms.xml` (extension) | Cross-post `.agents/` events to `_comms/` |
| 12 | Comms directory bootstrap | `team/_memory/_comms/{proposals,findings,requests,handoffs,broadcasts}/` | Materialized directory tree |
| 13 | SH workflow extension | `team/workflows/navigator/session-handoff/instructions.md` (Step 7 addition) | Coordination Context report section |
| 14 | CR workflow extension | `team/workflows/implementation/code-review/instructions.xml` (preamble addition) | Pre-review claim check + post-review decision posting |
| 15 | Maestro scan awareness | `team/workflows/maestro/scan-and-plan/` (addition) | Read `.agents/` state during triage |

### What Is NOT Built

- No daemon processes or background services
- No changes to `workflow.xml` engine
- No changes to existing workflow step numbering or ordering
- No database, no network services
- No git hooks (only Claude Code hooks)

---

## Testing Strategy

### Manual Verification

1. **Single agent**: Run one Claude instance through full lifecycle (startup → work → shutdown). Verify worktree created, claim written, handoff generated, cleanup complete.
2. **Two agents, no conflict**: Run two instances claiming different stories with non-overlapping paths. Verify both complete independently.
3. **Two agents, path conflict**: Run two instances where one tries to edit a file claimed by the other. Verify hook blocks the edit.
4. **Crash recovery**: Start an agent, kill the process, start a new agent. Verify stale detection and cleanup.
5. **Decision sync**: Agent A writes a decision, Agent B starts and reads it. Verify acknowledgment.

### Edge Cases

- Agent starts when no sprint-status.yaml exists (graceful fallback to manual task assignment)
- All stories claimed (agent reports "no available work" and exits)
- Two agents start simultaneously and race on the same claim (mitigated by `mkdir` mutex — see Section 2.2. The losing agent backs off and retries with max 3 attempts)
- Worktree creation fails (disk space, git lock) — agent reports error and does not register
- Agent's branch has merge conflicts with main — flagged during shutdown, not auto-resolved

---

## Future Considerations

These are explicitly out of scope but noted for future iterations:

- **Cross-machine coordination**: Push `.agents/` state to a shared branch for remote agent awareness
- **Supervisor mode**: A dedicated Maestro instance that actively assigns work and monitors agents
- **Agent-to-agent real-time messaging**: File-watch or IPC for faster communication
- **Automatic merge orchestration**: Agents coordinate branch merges in dependency order
- **Dashboard**: Visual status board showing all active agents, claims, and progress
