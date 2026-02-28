# BMAD v6 -- Claude Code Setup Guide

Claude Code has the deepest BMAD integration of any supported tool. This guide covers the complete setup and all available features.

## Overview

Claude Code integration includes:
- **CLAUDE.md** auto-loaded every session with Oracle activation protocol
- **81 slash commands** for direct agent and workflow invocation
- **PostToolUse hooks** for automatic context regeneration after commits
- **settings.local.json** for permissions, environment variables, and hooks
- **Agent teams** (experimental) for parallel multi-agent work
- **MCP server** support for browser testing and library documentation

---

## CLAUDE.md -- Session Instructions

`CLAUDE.md` is automatically read by Claude Code at the start of every session. BMAD uses it to:

1. Instruct Claude to activate the Oracle agent before any other work
2. Define the implementation lifecycle (create-story, dev-story, code-review, ship)
3. Point to context files in `_bmad-output/context/`
4. List project-specific technical rules

### Key Sections

**Oracle Activation Protocol** -- Tells Claude to:
- Always invoke the Oracle first: `/bmad:bmm:agents:oracle`
- Read sprint state from `sprint-status.yaml`
- Present a project brief and menu
- Enforce lifecycle gates before executing workflows

**Agent Context System** -- Points to pre-generated context files:
- `module-index.md` -- Feature map of frontend modules and backend services
- `sprint-digest.md` -- Pre-computed sprint summary
- `api-index.md` -- All API endpoints by router
- `schema-digest.md` -- Database schema from models
- `patterns.md` -- Canonical code patterns

**Critical Technical Rules** -- Project-specific rules enforced during implementation and code review.

### Customizing CLAUDE.md

Add your project's rules to the `## Critical Technical Rules` section. These are injected into every session and enforced by agents. Keep them concise and specific:

```markdown
## Critical Technical Rules

- **React 18** with TypeScript strict mode
- **Zustand 4.5+** with skipHydration: true for persisted stores
- **React Query 5** object syntax for useQuery({ queryKey, queryFn })
- **FastAPI** with SQLAlchemy 2.0 async patterns
- **PostgreSQL RLS** -- use set_config(), never SET
```

---

## Slash Commands

BMAD provides 81 slash commands organized by module. In Claude Code, type `/bmad:` and tab-complete to see all available commands.

### Agent Commands

Invoke any agent directly:

```
/bmad:bmm:agents:oracle              # Project Oracle (Athena)
/bmad:bmm:agents:architect           # Architect (Winston)
/bmad:bmm:agents:dev                 # Developer (Amelia)
/bmad:bmm:agents:security-auditor    # Security Auditor (Shield)
/bmad:bmm:agents:tea                 # Test Architect (Murat)
/bmad:bmm:agents:custodian           # Custodian (Sentinel)
/bmad:bmm:agents:devops              # DevOps (Forge)
/bmad:bmm:agents:data-architect      # Data Architect (Oracle)
/bmad:bmm:agents:navigator           # Navigator (Navi)
/bmad:bmm:agents:pm                  # Product Manager (John)
/bmad:bmm:agents:analyst             # Analyst (Mary)
/bmad:bmm:agents:sm                  # Scrum Master (Bob)
/bmad:bmm:agents:ux-designer         # UX Designer (Sally)
/bmad:bmm:agents:tech-writer         # Tech Writer (Paige)
/bmad:bmm:agents:quick-flow-solo-dev # Quick Flow Solo Dev (Barry)
/bmad:bmm:agents:api-contract        # API Contract (Pact)
/bmad:bmm:agents:agentic-expert      # Agentic Expert (Nexus)
/bmad:bmm:agents:ml-expert           # ML Expert (Neuron)
/bmad:bmm:agents:nist-rmf-expert     # NIST RMF Expert (Atlas)
/bmad:bmm:agents:healthcare-expert   # Healthcare Expert (Dr. Vita)
/bmad:bmm:agents:government-expert   # Government Expert (Senator)
/bmad:bmm:agents:financial-expert    # Financial Expert (Sterling)
/bmad:cis:agents:brainstorming-coach     # Brainstorming Coach (Carson)
/bmad:cis:agents:design-thinking-coach   # Design Thinking Coach (Maya)
/bmad:cis:agents:creative-problem-solver # Creative Problem Solver (Dr. Quinn)
/bmad:cis:agents:innovation-strategist   # Innovation Strategist (Victor)
/bmad:cis:agents:presentation-master     # Presentation Master (Caravaggio)
/bmad:cis:agents:storyteller             # Storyteller (Sophia)
/bmad:bmb:agents:agent-builder       # Agent Builder (Bond)
/bmad:bmb:agents:workflow-builder    # Workflow Builder (Wendy)
/bmad:bmb:agents:module-builder      # Module Builder (Morgan)
/bmad:core:agents:bmad-master        # BMad Master
```

### Workflow Commands (BMM)

```
/bmad:bmm:workflows:create-product-brief     # Phase 1: Analysis
/bmad:bmm:workflows:research                 # Phase 1: Analysis
/bmad:bmm:workflows:prd                      # Phase 2: Planning
/bmad:bmm:workflows:create-ux-design         # Phase 2: Planning
/bmad:bmm:workflows:create-architecture      # Phase 3: Solutioning
/bmad:bmm:workflows:create-epics-and-stories # Phase 3: Solutioning
/bmad:bmm:workflows:check-implementation-readiness  # Phase 3
/bmad:bmm:workflows:create-story             # Phase 4: Implementation
/bmad:bmm:workflows:dev-story                # Phase 4: Implementation
/bmad:bmm:workflows:code-review              # Phase 4: Implementation
/bmad:bmm:workflows:ship                     # Phase 4: Implementation (DevOps)
/bmad:bmm:workflows:commit                   # DevOps
/bmad:bmm:workflows:branch-cleanup           # DevOps
/bmad:bmm:workflows:sprint-planning          # Sprint Management
/bmad:bmm:workflows:sprint-status            # Sprint Management
/bmad:bmm:workflows:epic-consistency-check   # Sprint Management
/bmad:bmm:workflows:correct-course           # Sprint Management
/bmad:bmm:workflows:retrospective            # Sprint Management
/bmad:bmm:workflows:quick-dev                # Quick Flow
/bmad:bmm:workflows:quick-spec               # Quick Flow
/bmad:bmm:workflows:pr-review                # Custodian
/bmad:bmm:workflows:document-project         # Project
/bmad:bmm:workflows:generate-project-context # Project
/bmad:bmm:workflows:workflow-init            # Project
/bmad:bmm:workflows:workflow-status          # Project
/bmad:bmm:workflows:testarch-atdd            # Testing
/bmad:bmm:workflows:testarch-automate        # Testing
/bmad:bmm:workflows:testarch-ci              # Testing
/bmad:bmm:workflows:testarch-framework       # Testing
/bmad:bmm:workflows:testarch-nfr             # Testing
/bmad:bmm:workflows:testarch-test-design     # Testing
/bmad:bmm:workflows:testarch-test-review     # Testing
/bmad:bmm:workflows:testarch-trace           # Testing
/bmad:bmm:workflows:create-excalidraw-diagram    # Diagrams
/bmad:bmm:workflows:create-excalidraw-dataflow   # Diagrams
/bmad:bmm:workflows:create-excalidraw-flowchart  # Diagrams
/bmad:bmm:workflows:create-excalidraw-wireframe  # Diagrams
```

### Workflow Commands (CIS, Core, BMB)

```
/bmad:cis:workflows:design-thinking      # Creative Innovation
/bmad:cis:workflows:innovation-strategy  # Creative Innovation
/bmad:cis:workflows:problem-solving      # Creative Innovation
/bmad:cis:workflows:storytelling         # Creative Innovation
/bmad:core:workflows:brainstorming       # Core
/bmad:core:workflows:party-mode          # Core
/bmad:core:workflows:feature-orchestrator # Core
/bmad:bmb:workflows:agent               # Builder
/bmad:bmb:workflows:module              # Builder
/bmad:bmb:workflows:workflow            # Builder
```

### Task Commands

```
/bmad:core:tasks:index-docs   # Index documents in a directory
/bmad:core:tasks:shard-doc    # Split large documents into sections
```

---

## Settings File

`.claude/settings.local.json` configures Claude Code's behavior for your project:

```json
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  },
  "permissions": {
    "allow": [
      "Bash(*)",
      "Read(//**)"
    ]
  },
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/post-commit-context.sh"
          }
        ]
      }
    ]
  }
}
```

### Fields

| Field | Purpose |
|-------|---------|
| `env.CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` | Enables experimental agent teams feature |
| `permissions.allow` | Pre-approves Bash and Read tool usage to avoid permission prompts |
| `hooks.PostToolUse` | Registers the post-commit context regeneration hook |

### Template

The setup script generates `settings.local.json` from `templates/settings.local.json.template`. You can modify either file to add custom environment variables or permissions.

---

## Post-Commit Hook

The post-commit hook at `hooks/post-commit-context.sh` (copied to `.claude/hooks/` during setup) automatically regenerates context files after every successful git commit.

### How It Works

1. Claude Code fires a `PostToolUse` event after every Bash tool call
2. The hook reads JSON from stdin describing what command was executed
3. If the command was `git commit` and it succeeded, the hook runs `scripts/context/generate_all.py`
4. The hook outputs JSON with `additionalContext` that gets injected into the conversation
5. Claude Code sees the message: "Context files regenerated in _bmad-output/context/..."

### Zero Overhead

The hook exits immediately (exit 0, no output) for any non-commit Bash command. There is no performance impact on normal tool usage (ls, npm, pytest, etc.).

### Debugging

Test the hook manually:
```bash
echo '{"tool_input":{"command":"git commit -m test"},"tool_response":{"stdout":"[main abc] test"}}' \
  | CLAUDE_PROJECT_DIR="$(pwd)" .claude/hooks/post-commit-context.sh
```

Enable verbose mode in Claude Code (Ctrl+O) to see hook output in the transcript.

---

## Agent Teams

Agent teams are an experimental feature that allows multiple BMAD agents to work in parallel.

### Enabling

Set the environment variable in `.claude/settings.local.json`:
```json
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  }
}
```

### Available Teams

Teams are defined in `_bmad/_config/manifest.yaml`:

| Team | Members | Best For |
|------|---------|----------|
| **fullstack** | analyst, architect, pm, sm, ux-designer | Planning, architectural decisions |
| **implementation** | dev, tea, tech-writer | Parallel development, test coverage |
| **creative** | brainstorming-coach, storyteller, creative-problem-solver, design-thinking-coach, innovation-strategist, presentation-master | Innovation, creative problem solving |

### Invocation

Teams can be invoked through:
- **Party Mode**: Oracle menu [PM] -- agents discuss a topic together
- **Workflow tags**: `invoke-team` in workflow instructions
- **Direct**: Ask the Oracle to assemble a team for a specific task

### Token Budget

Agent teams use approximately 2.5x more tokens than single-agent sessions. The `token_budget_multiplier` in config.yaml controls this threshold.

---

## MCP Servers

Claude Code supports MCP (Model Context Protocol) servers for extended capabilities.

### Playwright (Browser Testing)

Enables browser interaction for visual testing, screenshot comparison, and web automation:
- Navigate to URLs
- Take screenshots
- Click elements
- Fill forms
- Evaluate JavaScript

### Context7 (Library Documentation)

Provides up-to-date documentation for any library or framework:
- Resolve library IDs
- Query documentation with specific questions
- Get code examples

### Configuration

MCP servers are configured in Claude Code's MCP settings (separate from BMAD). See Claude Code documentation for MCP server setup.

---

## Typical Session Flow

1. Start Claude Code in your project directory
2. Claude reads CLAUDE.md automatically
3. Claude invokes the Oracle (or you type `/bmad:bmm:agents:oracle`)
4. Oracle loads config, reads sprint status, presents project brief
5. You select a menu item or give a directive
6. Oracle executes the appropriate workflow
7. On git commit, the post-commit hook regenerates context files
8. Continue working with fresh context

---

## Troubleshooting

### Oracle does not activate automatically

- Verify `CLAUDE.md` exists in the project root
- Check that it contains the Oracle activation protocol
- Try invoking manually: `/bmad:bmm:agents:oracle`

### Slash commands not appearing

- Verify `claude-commands/` directory exists with `.md` files
- Claude Code reads from `.claude/commands/` -- the setup script should symlink or copy
- Check that the command files reference the correct agent/workflow paths

### Post-commit hook not firing

- Check `.claude/settings.local.json` has the hooks configuration
- Verify `hooks/post-commit-context.sh` exists and is executable
- Verify `scripts/context/generate_all.py` exists
- Test manually using the debug command above

### Context files are stale

- Run `python scripts/context/generate_all.py --check` to verify
- Run `python scripts/context/generate_all.py` to regenerate manually
- Check that the hook is registered and firing on commits

### Agent teams not working

- Verify `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` is set in settings
- This is an experimental feature -- behavior may vary
- Check `_bmad/_config/manifest.yaml` for team definitions
