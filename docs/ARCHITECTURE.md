# My Dev Team — Architecture

This document explains how the system works internally -- the workflow engine, agent activation protocol, Maestro/Oracle orchestration, variable resolution, context generation pipeline, and sprint status tracking.

## System Overview

This is a file-driven methodology. There is no runtime, no server, no database. Everything is markdown files, YAML configurations, and XML task definitions that AI coding tools read and execute. The "engine" is the AI model itself, guided by structured instructions.

```
User Directive
      |
      v
Maestro (project-level) or Oracle (sprint-level)
      |
      +-- Reads config.yaml (project settings)
      +-- Reads sprint-status.yaml (project state)
      +-- Reads context files (codebase knowledge)
      |
      v
Lifecycle Gate Check
      |
      +-- Story file exists?
      +-- Story status correct?
      +-- Prerequisites met?
      |
      v
Workflow Execution (workflow.xml engine)
      |
      +-- Load workflow.yaml config
      +-- Resolve variables
      +-- Execute steps in order
      +-- Save output artifacts
      |
      v
Output: Code, Story Updates, Sprint Status Updates
```

## Workflow Engine

The workflow engine lives at `team/engine/workflow.xml`. It is the core operating system that all workflows run through. When the Oracle or any agent needs to execute a workflow, they load `workflow.xml` and pass it a `workflow.yaml` configuration file.

### Execution Flow

**Step 1: Load and Initialize**

1. Read the `workflow.yaml` from the provided path
2. Load the external config from `config_source` (always `team/config.yaml`)
3. Resolve all `{config_source}:` references with values from config (e.g., `{config_source}:project_name` becomes `My Project`)
4. Resolve system variables: `{project-root}`, `{installed_path}`, `{date}`
5. Ask user for any variables that remain unknown
6. Read instruction files (markdown or XML steps)
7. Read template files if the workflow produces a document
8. Create the output file with template placeholders

**Step 2: Process Each Step**

For each step in the instructions:
1. Handle step attributes: `optional`, `if`, `for-each`, `repeat`
2. Execute step content by processing tags: `action`, `check`, `ask`, `invoke-workflow`, `invoke-task`, `invoke-protocol`, `goto`
3. Handle `template-output` tags: generate content for that section, save to file, present to user
4. At each template-output checkpoint, offer the user: [a] Advanced Elicitation, [c] Continue, [p] Party-Mode, [y] YOLO the rest

**Step 3: Completion**

Confirm the document is saved and report workflow completion.

### Execution Modes

| Mode | Behavior |
|------|----------|
| **Normal** | Full user interaction. Confirms every step at every template output. No exceptions. |
| **YOLO** | Skip all confirmations. The AI simulates expert user responses and produces the entire workflow output automatically. |

### Supported Instruction Tags

| Tag | Purpose |
|-----|---------|
| `step n="X" goal="..."` | Define a step with number and goal |
| `action` | Required action to perform |
| `check if="condition"` | Conditional block wrapping multiple items |
| `ask` | Prompt user and wait for response |
| `goto step="x"` | Jump to another step |
| `invoke-workflow` | Execute another workflow |
| `invoke-task` | Execute a specified task |
| `invoke-protocol` | Execute a reusable protocol (e.g., `discover_inputs`) |
| `invoke-team` | Create an agent team with specified members |
| `message-teammate` | Send message to a specific teammate |
| `broadcast-team` | Send message to all team members |
| `template-output` | Save content checkpoint |
| `optional="true"` | Step can be skipped (asks user unless YOLO) |

### Built-in Protocols

The workflow engine includes reusable protocols that can be invoked via `invoke-protocol`:

**`discover_inputs`** -- Smart file discovery based on `input_file_patterns` in workflow.yaml. Supports three loading strategies:

| Strategy | Behavior |
|----------|----------|
| `FULL_LOAD` | Load all files in a sharded directory (default) |
| `SELECTIVE_LOAD` | Load specific shard using template variable (e.g., a single epic file) |
| `INDEX_GUIDED` | Load index.md, analyze structure, intelligently load relevant documents |

## Agent Activation Protocol

Every agent file (`.md`) follows the same activation structure:

```markdown
---
name: "agent-name"
description: "Agent description"
---

<agent id="..." name="PersonaName" title="Title" icon="...">
  <activation critical="MANDATORY">
    <step n="1">Load persona from this file</step>
    <step n="2">Load config.yaml, read settings</step>
    <step n="3">Remember user name from config</step>
    ...additional activation steps...
  </activation>

  <persona>
    <role>...</role>
    <identity>...</identity>
    <communication_style>...</communication_style>
    <principles>...</principles>
  </persona>

  <menu>
    <item cmd="..." workflow="...">Menu item description</item>
    <item cmd="..." action="#prompt-id">Another menu item</item>
  </menu>

  <prompts>
    <prompt id="prompt-id">Inline instructions to execute</prompt>
  </prompts>
</agent>
```

### Activation Steps

When an agent is invoked (via slash command or direct file reference):

1. The AI reads the full agent file
2. It follows the `<activation>` steps in order
3. It adopts the persona defined in `<persona>` -- role, identity, communication style, principles
4. It loads configuration from `config.yaml` to resolve variables like `{project_name}` and `{user_name}`
5. It presents the menu to the user and waits for input
6. On user selection, it processes menu item handlers:
   - `workflow="path"` -- loads `workflow.xml` and executes the workflow
   - `action="#id"` -- finds and executes the matching inline prompt
   - `exec="path"` -- directly executes the referenced file

The agent stays in character until dismissed via the exit menu item.

## Orchestration: Maestro and Oracle

The system has two orchestrators with distinct roles:

- **Maestro** (`team/agents/maestro.md`) — The primary project-level orchestrator. Scans the full project landscape, assigns agents to tasks, builds per-agent mission briefings (memory), produces the master plan, and enforces CEO approval gates. Use Maestro when starting new projects, major initiatives, or when "Let's ride" scanning is needed.
- **Oracle / Athena** (`team/agents/oracle.md`) — The sprint-level orchestrator. Reads sprint state, presents project briefs, and enforces the implementation lifecycle (create-story → dev-story → code-review → ship). Use Oracle for day-to-day sprint execution.

### Oracle Activation Sequence

### Oracle Activation Sequence

1. Load persona from agent file
2. **Load configuration**: Read `team/config.yaml`, store all fields as session variables
3. **Load context files**: Read `project-context.md`, `module-index.md`, `sprint-digest.md` from `output/`
4. **Check context freshness**: Run `generate_all.py --check`; warn if stale
5. Remember user name from config
6. **Read sprint state**: Load `sprint-status.yaml` completely
7. **Parse sprint data**: Count stories by status, identify active epic, find in-progress/review stories
8. **Present project brief**: Current epic, in-flight stories, awaiting review, backlog count, recommendation
9. Display menu and wait for user input

### Lifecycle Gates

The Oracle enforces pre-conditions before executing any workflow:

| Workflow | Gate Check | Failure Action |
|----------|-----------|----------------|
| **Dev Story (DS)** | Story file must exist in `stories/` directory | Refuse. Redirect to Create Story (CS). |
| **Code Review (CR)** | Story status must be `in-progress` or `review` | Refuse. Redirect to Dev Story (DS). |
| **Ship (SH)** | Story status must be `done` (code review passed) | Refuse. Redirect to Code Review (CR). |

These gates cannot be bypassed. The Oracle evaluates them before every workflow execution.

### Oracle Menu

| Command | Action | Type |
|---------|--------|------|
| [MH] Menu Help | Redisplay menu | Display |
| [CH] Chat | Free-form conversation | Inline |
| [PB] Project Brief | Full project state and recommendation | Prompt |
| [NA] Next Action | Determine and execute highest-priority work | Prompt |
| [CS] Create Story | Generate story file from epic | Workflow |
| [DS] Dev Story | Implement a story | Workflow |
| [CR] Code Review | Adversarial code review | Workflow |
| [SH] Ship | Commit, push, create PR | Workflow |
| [SP] Sprint Planning | Generate sprint status tracking | Workflow |
| [SS] Sprint Status | Summarize sprint and surface risks | Workflow |
| [EC] Epic Consistency | Audit stories for overlap | Workflow |
| [CC] Course Correction | Navigate implementation changes | Workflow |
| [RT] Retrospective | Review after epic completion | Workflow |
| [RA] Route to Agent | Delegate to domain specialist | Prompt |
| [RS] Risk Scan | Identify blockers and drift | Prompt |
| [HO] Session Handoff | Generate continuity summary | Prompt |
| [PM] Party Mode | Multi-agent group discussion | Exec |
| [DA] Dismiss Agent | Exit Oracle | Display |

### Routing Table

When the Oracle routes to a specialist agent, it provides the exact slash command:

| Task Domain | Agent | Command |
|-------------|-------|---------|
| Backend API/data design | Winston (Architect) | `/team:architect` |
| Frontend UI/UX design | Sally (UX Designer) | `/team:ux-designer` |
| Test strategy | Murat (Test Architect) | `/team:tea` |
| Repo health/patterns | Sentinel (Custodian) | `/team:custodian` |
| Security review | Shield (Security Auditor) | `/team:security-auditor` |
| NIST RMF compliance | Atlas (NIST Expert) | `/team:nist-rmf-expert` |
| Docker/CI/CD | Forge (DevOps) | `/team:devops` |
| API contract drift | Pact (API Contract) | `/team:api-contract` |
| AI/Agentic architecture | Nexus (Agentic Expert) | `/team:agentic-expert` |
| ML/model evaluation | Neuron (ML Expert) | `/team:ml-expert` |
| SQL/data/caching | Vault (Data Architect) | `/team:data-architect` |

## Variable Resolution

The system uses a variable system to make workflows and agents portable across projects.

### System Variables

| Variable | Resolves To | Example |
|----------|------------|---------|
| `{project-root}` | Project root directory | `/home/user/my-project` |
| `{installed_path}` | Directory containing the current workflow | `team/workflows/implementation/dev-story` |
| `{config_source}` | Path to the module's config.yaml | `team/config.yaml` |
| `{date}` | Current date (system-generated) | `2026-02-27` |

### Config Variables

Config variables are loaded from `config.yaml` and accessed via the `{config_source}:field_name` syntax:

| Variable | Source Field | Example Value |
|----------|-------------|---------------|
| `{config_source}:project_name` | `project_name` | `My SaaS App` |
| `{config_source}:user_name` | `user_name` | `Sarah` |
| `{config_source}:output_folder` | `output_folder` | `{project-root}/output` |
| `{config_source}:planning_artifacts` | `planning_artifacts` | `{project-root}/output/planning-artifacts` |
| `{config_source}:implementation_artifacts` | `implementation_artifacts` | `{project-root}/output/implementation-artifacts` |
| `{config_source}:communication_language` | `communication_language` | `English` |

### Resolution Order

1. Load config from `config_source` path
2. Replace all `{config_source}:field` references with config values
3. Resolve `{project-root}` and `{installed_path}` with actual paths
4. Generate `{date}` from the system clock
5. Prompt user for any remaining unresolved variables

## Context Generation Pipeline

The system uses a context generation system to keep AI agents informed about the current state of the codebase. This is critical for large projects where scanning the entire repo every session would be impractical.

### Pipeline Flow

```
Git Commit (via Claude Code Bash tool)
      |
      v
PostToolUse Hook fires
      |
      v
post-commit-context.sh
      |
      +-- Reads JSON from stdin (tool_input, tool_response)
      +-- Checks if command was "git commit"
      +-- Checks if commit succeeded
      |
      v
python scripts/context/generate_all.py
      |
      +-- module-index.md    (frontend features + backend services map)
      +-- api-index.md       (all API endpoints by router)
      +-- schema-digest.md   (database tables from models)
      +-- patterns.md        (canonical code patterns)
      +-- sprint-digest.md   (sprint status summary)
      |
      v
JSON response with additionalContext
      |
      v
Claude Code injects message into conversation:
"Context files regenerated in output/context/..."
```

### Manual Commands

```bash
# Regenerate all context files
python scripts/context/generate_all.py

# Regenerate only sprint-related context
python scripts/context/generate_all.py --sprint

# Check if context files are stale
python scripts/context/generate_all.py --check
```

### Hook Configuration

The post-commit hook is registered in `.claude/settings.local.json`:

```json
{
  "hooks": {
    "PostToolUse": [{
      "matcher": "Bash",
      "hooks": [{
        "type": "command",
        "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/post-commit-context.sh"
      }]
    }]
  }
}
```

The hook only triggers on `git commit` commands and exits silently (with zero overhead) for all other Bash operations.

## Sprint Status as Single Source of Truth

`sprint-status.yaml` is the central tracking file that the Oracle reads before every decision. It tracks:

- **Epics**: Name, status (`backlog`, `in-progress`, `done`), story count
- **Stories**: ID, title, status (`backlog`, `ready-for-dev`, `in-progress`, `review`, `done`), epic assignment
- **Sprint metadata**: Sprint number, start/end dates, goals

### Status Transitions

```
backlog  -->  ready-for-dev  -->  in-progress  -->  review  -->  done
   |              |                    |               |           |
   |         Created by           Set by DS       Set by CR    Set by CR
   |         CS workflow          workflow         workflow     (passing)
   |              |                    |               |
   +--- Initial --+                    +--- Dev -------+--- Ship
        state                          completes       review
                                                       passes
```

### How It Gets Updated

| Workflow | Status Change |
|----------|--------------|
| Sprint Planning (SP) | Creates initial file with all stories in `backlog` |
| Create Story (CS) | Sets story to `ready-for-dev` |
| Dev Story (DS) | Sets story to `in-progress` at start |
| Code Review (CR) | Sets story to `review` at start, `done` when passing |
| Ship (SH) | No status change (story already `done`); creates PR |

### Oracle Decision Priority

The Oracle reads sprint-status.yaml and applies this priority:

1. **CRITICAL**: Stories stuck in `in-progress` for a long time -- resume with DS
2. **HIGH**: Stories in `review` status -- execute CR
3. **MEDIUM**: Next story in active epic needs a story file -- execute CS
4. **NORMAL**: A `ready-for-dev` story exists -- execute DS
5. **LOW**: Current epic complete but no retrospective -- execute RT
6. **INFO**: Everything clear -- present brief and ask user

## Engineering Discipline System

The system includes a set of hard enforcement protocols that prevent AI agents from cutting corners during implementation. These are not guidelines — they are mandatory gates with zero tolerance for rationalization.

### Discipline Knowledge Base

Located at `team/data/discipline/`, the knowledge base contains five discipline protocols:

| Discipline | Iron Law | Enforcement |
|------------|----------|-------------|
| **Verification** | No completion claims without fresh evidence in the current context | Refuse to mark tasks complete without visible command output |
| **TDD** | No production code without a failing test first | Delete production code and restart the cycle on violation |
| **Debugging** | No fixes without root cause investigation first | Halt and escalate after 3 failed attempts |
| **Receiving Review** | Read every comment, verify the claim, then respond | No performative agreement — restate technically |
| **Anti-Rationalization** | Even a 1% chance a discipline applies means MUST follow it | Cross-cutting guard against excuse-making |

Each protocol includes an Iron Law, red flag detection, a rationalization defense table, and a hard gate check sequence.

### Engine-Level Enforcement

`team/engine/discipline-gates.xml` provides reusable enforcement gates that workflows invoke via `invoke-task`. Four gates are available: `verification`, `tdd`, `debugging`, and `receiving-review`. Each gate checks compliance and either passes or halts with an explicit violation response.

### Integration Points

- **Dev Agent (Amelia)**: TDD, verification, and debugging disciplines baked into activation, rules, and principles
- **Oracle Agent (Athena)**: Verification enforcement at all workflow completion checkpoints. Refuses to proceed with stale evidence.
- **Dev Story Workflow**: Discipline gates at RED phase, GREEN phase, verification, and task completion
- **Code Review Workflow**: Receiving review discipline when fixing issues — no performative agreement
- **Ship Workflow**: Verification evidence gate before deployment (fresh test output required)
- **Story Checklist**: Explicit discipline compliance section required before marking a story complete

### Evidence Standards

Only **fresh evidence** visible in the current session counts:

- "Tests were passing" is NOT evidence
- "It should work" is NOT evidence
- Exit code alone is NOT evidence
- Only full command output visible after the final code change qualifies

### Discipline Override

Disciplines can be overridden only by explicit user instruction. All overrides are logged as `[DISCIPLINE-OVERRIDE]` in workflow output.

---

## Directory Structure

All agents and workflows are organized in a flat `team/` directory:

```
team/
  config.yaml           # Unified configuration
  manifest.yaml         # Team definitions and metadata
  agent-manifest.csv    # Agent registry
  agents/               # All 27 agents (flat, no module nesting)
  workflows/            # All workflows by category
    analysis/           # Phase 1: Product brief, research
    planning/           # Phase 2: PRD, UX design
    solutioning/        # Phase 3: Architecture, epics
    implementation/     # Phase 4: Dev story, code review, ship
    quick-flow/         # Rapid development workflows
    builders/           # Agent/workflow/module creation
    brainstorming/      # Creative brainstorming sessions
    party-mode/         # Multi-agent group discussions
    feature-orchestrator/ # Parallel feature decomposition
    ... (20+ categories)
  engine/               # Workflow execution engine
    workflow.xml        # Core workflow processor
    discipline-gates.xml # Engineering discipline enforcement gates
    index-docs.xml      # Document indexing task
    shard-doc.xml       # Document sharding task
    review-adversarial-general.xml  # Adversarial review task
  resources/            # Shared resources (excalidraw helpers)
  data/                 # Project data, knowledge bases, testarch
    discipline/         # Engineering discipline protocols (TDD, verification, etc.)
  teams/                # Team composition files
```

## Team System

The system supports agent teams -- multiple agents working in parallel on different aspects of a task. Teams are defined in `team/manifest.yaml`:

```yaml
teams:
  fullstack:
    name: "Team Plan and Architect"
    members: [analyst, architect, pm, ux-designer]
    best_for: ["Planning new features", "Architectural decisions"]

  implementation:
    name: "Dev Team"
    members: [dev, tea, tech-writer]
    best_for: ["Parallel implementation", "Test coverage review"]

  creative:
    name: "Creative Squad"
    members: [creative-thinking-coach, design-strategy-coach, storyteller-presenter]
    best_for: ["Innovation strategy", "Creative problem solving"]
```

Teams can be invoked via `invoke-team` tags in workflow instructions or through the Oracle's Party Mode. Agent teams require the `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` environment variable (Claude Code only).
