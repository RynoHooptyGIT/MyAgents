---
title: Oracle Ambient Intelligence — Design Spec
date: 2026-05-09
status: approved
author: CEO + Claude (brainstorming session)
---

# Oracle Ambient Intelligence

## Overview

Enhance the existing Oracle agent (Athena) from a menu-driven sprint orchestrator into an **ambient intelligence layer** that monitors the entire session, detects problems, suggests or auto-executes fixes, and dispatches the right combination of Claude Code skills and team agents.

Once activated via `/team:oracle`, Athena stays present for the entire session — watching output, detecting issues, and proactively guiding work.

## Design Decisions

- **Approach:** Two-layer — Oracle core logic + external dispatch map
- **Trigger:** `/team:oracle` activates ambient mode. "fix it" is one capability within the oracle.
- **Context analysis:** Conversation context first, project state scan as fallback
- **Execution mode:** Configurable — suggest (default), auto, or off
- **Dispatch scope:** Both Claude Code skills and team agents
- **Skills location:** Claude Code skills live at `~/.claude/skills/` (systematic-debugging, dispatching-parallel-agents, simplify, etc.) — these are user-level skills, not project-level

## Oracle vs Maestro Boundary

Oracle and Maestro have distinct roles that must not overlap:

| | Oracle (Athena) | Maestro |
|---|---|---|
| **Scope** | Reactive, in-session, tactical | Proactive, strategic, multi-agent |
| **Trigger** | Problems that arise while working | Deliberate full-project scan |
| **Fixes** | Immediate — debug, patch, route to specialist | Plans — assign agents, build memories, master plan |
| **State** | Conversation context + recent tool output | Full project: sprint state, context files, codebase |
| **Escalation** | Routes to Maestro when scope exceeds tactical | Owns the strategic layer |

**Rule:** Oracle handles what just broke. Maestro handles what needs building. When Oracle detects a problem spanning 3+ categories, it escalates to Maestro rather than attempting a strategic fix.

## Ambient Monitoring

### Lifecycle

```
/team:oracle
  -> Athena activates (existing activation sequence)
  -> Presents menu, loads sprint state (existing behavior)
  -> Loads dispatch map
  -> Enters ambient monitoring mode (suggest by default)
  -> From this point: Athena watches all output

User works normally...
  -> Athena sees a test failure -> suggests fix or auto-fixes
  -> Athena sees work complete -> suggests next lifecycle step
  -> Athena sees a security pattern -> flags it, routes to Shield
  -> User says "fix it" -> Athena triages and dispatches (with plan)
  -> User says "just fix it" -> Athena triages and auto-executes
  -> User says any menu command -> executes as normal (CS, DS, CR, etc.)
```

### Oracle Modes

| Mode | Behavior | Toggle |
|------|----------|--------|
| **suggest** (default) | One-line nudge at pause points | `oracle suggest` |
| **auto** | Invokes matching skill/agent immediately | `oracle auto` or `just fix it` |
| **off** | Silent — only responds to direct commands | `oracle off` |

**Mode persistence:** Mode persists for the duration of the session unless explicitly changed. Menu commands (CS, DS, CR, SH, etc.) execute independently of oracle mode — mode only affects the ambient monitoring overlay.

**Status query:** `oracle status` shows current mode, issues detected this session, last action taken, and pending suggestions.

### Detection Categories

| Signal | Detection | Suggest Mode | Auto Mode |
|--------|-----------|-------------|-----------|
| Error output | Non-zero exit, stack traces, build failures | "I see [error]. Want me to debug?" | Invokes systematic-debugging |
| Test failures | Failed assertions, test runner errors | "[N] tests failing. `/fix-it`?" | Dispatches debugging (parallel if independent) |
| Work completion | Story implemented, review passed, tests green | "[Story] done. Next: [CR/SH/next story]" | Queues next lifecycle step |
| Security signals | Hardcoded secrets, missing auth, injection patterns | "Security concern in [file]. Route to Shield?" | Routes to /team:security-auditor |
| Stale state | Story in-progress for 10+ user messages with no related file edits | "[Story X] in-progress. Resume?" | Presents status, waits (never auto-resumes) |
| User frustration | Explicit phrases: "why isn't this working", "what's wrong", "this is broken" | "Let me take a look." | Takes over debugging |
| Questions/uncertainty | "should I...", "which approach", "how do I" | Routes to appropriate specialist | **Always suggest mode** — never auto-decides |

**Detection thresholds (conservative defaults):**
- **Stale state:** Story in-progress for 10+ user messages with no related file edits
- **Frustration:** Requires explicit natural-language signal from the user — never inferred from failure patterns alone. Repeated failures without user complaint are normal debugging; Oracle stays silent.
- **False positive policy:** When in doubt, do not nudge. One missed suggestion is better than one unwanted interruption.

### Monitoring Rules

- Athena does not interrupt mid-thought or mid-tool-chain
- Speaks up at natural pause points — after tool results, after completed actions, after user messages
- Never stacks suggestions — one nudge per pause point, highest priority wins
- Questions and uncertainty ALWAYS stay in suggest mode, even when oracle is in auto mode

## Context Analysis Pipeline

### Stage 1: Conversation Context (always runs first)

1. Scan recent tool output for errors, stack traces, non-zero exits
2. Scan recent user messages for complaints, questions, described problems
3. Identify files recently read/edited as the active working area

If Stage 1 finds actionable problems -> classify and proceed to dispatch.

### Stage 2: Project State Scan (only if Stage 1 finds nothing)

**Gate:** Stage 2 runs ONLY when explicitly triggered by "fix it" / "just fix it". It never auto-triggers in suggest mode. It may take significant time on large projects.

1. `git status` / `git diff` — uncommitted changes, merge conflicts
2. Run test suite (if detectable) — find failing tests
3. Lint/type-check (if detectable) — find static errors
4. Sprint state (`sprint-status.yaml`) — stuck stories, stale in-progress items
5. Recent git log — identify what was last worked on

### Problem Classification

Each detected problem gets:
- **Description** — what's wrong
- **Category** — bug, test failure, build error, security, architecture, sprint blocker, etc.
- **Severity** — critical / high / medium / low
- **Evidence** — the specific error, file, or signal
- **Independence** — can this be fixed independently of other problems?

## Dispatch Logic

### Decision Tree Per Problem

```
Problem identified
  -> Bug/error/test failure?
    -> Single: systematic-debugging skill
    -> Multiple independent: dispatching-parallel-agents skill
  -> Code quality/pattern issue?
    -> simplify skill or /team:custodian
  -> Security concern?
    -> /team:security-auditor (Shield)
  -> Architecture gap?
    -> /team:architect (Winston)
  -> Data/schema issue?
    -> /team:data-architect (Vault)
  -> Test coverage gap?
    -> /team:tea (Murat — Test Architect)
  -> Sprint/lifecycle blocker?
    -> Self (Athena menu commands: CS, DS, CR, SH)
  -> DevOps/CI/CD issue?
    -> /team:devops (Forge)
  -> Frontend/UX issue?
    -> /team:frontend-dev (Pixel) or /team:ux-designer (Sally)
  -> API contract issue?
    -> /team:api-contract (Pact)
  -> No category match?
    -> Fix directly using standard capabilities
```

### Multi-Problem Orchestration

1. Check independence between problems (shared files, related symptoms)
2. Group related problems -> single dispatch
3. Independent problems -> parallel dispatch via `dispatching-parallel-agents`
4. Mix of skills + agents -> skills execute first, then recommend agent invocations

### Escalation Rules

| Condition | Action |
|-----------|--------|
| Problem spans 3+ categories | Recommend Maestro scan-and-plan |
| Major architecture change needed | Route through CEO approval gate |
| 3+ fix attempts failed | Stop, question assumptions, suggest /team:architect |
| Classification ambiguous | Present top 2 routing options to user |

### Plan Mode Output

```
FIX-IT ANALYSIS
Found [N] problems:

1. [CRITICAL] Test failure in auth.test.ts -> systematic-debugging
2. [HIGH] Stale in-progress story 12.3 -> resume via DS
3. [MEDIUM] Missing input validation on /api/users -> /team:security-auditor

Approve? (sh = execute all, or pick numbers)
```

Auto mode skips the presentation and starts executing.

## Deliverables

### 1. Enhance `team/agents/oracle.md`

Add to Athena's activation sequence:
- New step: Load dispatch map, set oracle mode, announce ambient monitoring
- New rules for ambient monitoring behavior
- New "fix-it" prompt for context analysis and dispatch
- Mode toggle commands (oracle auto/suggest/off/status)

### 2. Create `team/agents/oracle-dispatch-map.md`

Standalone routing table containing:
- Skills section: which Claude Code skills map to which problem categories
- Agents section: which team agents map to which domain problems
- Escalation section: when to escalate to Maestro or CEO approval

### 3. Add CLAUDE.md Standing Instruction

Add under a new top-level heading (separate from multi-agent coordination):

```markdown
## Oracle Awareness
When Athena (Oracle) has been activated in this session, maintain ambient
monitoring after every tool result. Evaluate for errors, completions,
security signals, and frustration. Respond per oracle mode (suggest/auto/off).
```

**Limitation acknowledged:** This is a behavioral instruction, not a mechanical enforcement. LLM instruction-following may degrade over very long contexts. The ambient monitoring rules in oracle.md itself provide the primary enforcement; the CLAUDE.md instruction is reinforcement.

### 4. Update README.md

Document the ambient intelligence capability in the Oracle Lifecycle section.

## Testing Strategy

Manual QA checklist (prompt-based system, not automatable):

| # | Scenario | Input | Expected Output |
|---|----------|-------|-----------------|
| 1 | Mode toggle | `oracle auto` | Confirms mode change, starts auto-monitoring |
| 2 | Mode toggle | `oracle off` | Confirms, stops nudging |
| 3 | Mode query | `oracle status` | Shows mode, session stats |
| 4 | Error detection (suggest) | Run a command that fails | One-line nudge suggesting debug |
| 5 | Error detection (auto) | Set auto mode, run failing command | Automatically starts systematic-debugging |
| 6 | Fix-it with plan | `fix it` after visible errors | Presents numbered problem list, waits |
| 7 | Fix-it auto | `just fix it` after visible errors | Immediately starts fixing |
| 8 | Work completion | Complete a story | Suggests next lifecycle step |
| 9 | Multi-category escalation | 3+ different problem types | Recommends Maestro scan-and-plan |
| 10 | Question detection | "should I use X or Y?" | Suggests specialist, never auto-decides |
| 11 | Mode persistence | Set auto, run CS workflow, check mode | Mode still auto after workflow |
| 12 | No false positives | Methodical debugging with failures | Oracle stays silent unless asked |
