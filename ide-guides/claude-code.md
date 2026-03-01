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
3. Point to context files in `output/context/`
4. List project-specific technical rules

### Key Sections

**Oracle Activation Protocol** -- Tells Claude to:
- Always invoke the Oracle first: `/team:oracle`
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
/team:oracle              # Project Oracle (Athena)
/team:architect           # Architect (Winston)
/team:dev                 # Developer (Amelia)
/team:security-auditor    # Security Auditor (Shield)
/team:tea                 # Test Architect (Murat)
/team:custodian           # Custodian (Sentinel)
/team:devops              # DevOps (Forge)
/team:data-architect      # Data Architect (Oracle)
/team:pm                  # Product Manager (John)
/team:analyst             # Analyst (Mary)
/team:ux-designer         # UX Designer (Sally)
/team:tech-writer         # Tech Writer (Paige)
/team:quick-flow-solo-dev # Quick Flow Solo Dev (Barry)
/team:api-contract        # API Contract (Pact)
/team:agentic-expert      # Agentic Expert (Nexus)
/team:ml-expert           # ML Expert (Neuron)
/team:nist-rmf-expert     # NIST RMF Expert (Atlas)
/team:healthcare-expert   # Healthcare Expert (Dr. Vita)
/team:government-expert   # Government Expert (Senator)
/team:financial-expert    # Financial Expert (Sterling)
/team:creative-thinking-coach   # Creative Thinking Coach (Carson)
/team:design-strategy-coach     # Design & Strategy Coach (Maya)
/team:storyteller-presenter     # Storyteller & Presenter (Sophia)
/team:agent-builder       # Agent Builder (Bond)
/team:workflow-builder    # Workflow Builder (Wendy)
/team:module-builder      # Module Builder (Morgan)
/team:bmad-master        # BMad Master
```

### Workflow Commands (BMM)

```
/team:create-product-brief     # Phase 1: Analysis
/team:research                 # Phase 1: Analysis
/team:prd                      # Phase 2: Planning
/team:create-ux-design         # Phase 2: Planning
/team:create-architecture      # Phase 3: Solutioning
/team:create-epics-and-stories # Phase 3: Solutioning
/team:check-implementation-readiness  # Phase 3
/team:create-story             # Phase 4: Implementation
/team:dev-story                # Phase 4: Implementation
/team:code-review              # Phase 4: Implementation
/team:ship                     # Phase 4: Implementation (DevOps)
/team:commit                   # DevOps
/team:branch-cleanup           # DevOps
/team:sprint-planning          # Sprint Management
/team:sprint-status            # Sprint Management
/team:epic-consistency-check   # Sprint Management
/team:correct-course           # Sprint Management
/team:retrospective            # Sprint Management
/team:quick-dev                # Quick Flow
/team:quick-spec               # Quick Flow
/team:pr-review                # Custodian
/team:document-project         # Project
/team:generate-project-context # Project
/team:workflow-init            # Project
/team:workflow-status          # Project
/team:testarch-atdd            # Testing
/team:testarch-automate        # Testing
/team:testarch-ci              # Testing
/team:testarch-framework       # Testing
/team:testarch-nfr             # Testing
/team:testarch-test-design     # Testing
/team:testarch-test-review     # Testing
/team:testarch-trace           # Testing
/team:create-excalidraw-diagram    # Diagrams
/team:create-excalidraw-dataflow   # Diagrams
/team:create-excalidraw-flowchart  # Diagrams
/team:create-excalidraw-wireframe  # Diagrams
```

### Workflow Commands (CIS, Core, BMB)

```
/team:design-thinking      # Creative Innovation
/team:innovation-strategy  # Creative Innovation
/team:problem-solving      # Creative Innovation
/team:storytelling         # Creative Innovation
/team:brainstorming       # Core
/team:party-mode          # Core
/team:feature-orchestrator # Core
/team:agent               # Builder
/team:module              # Builder
/team:workflow            # Builder
```

### Task Commands

```
/team:index-docs   # Index documents in a directory
/team:shard-doc    # Split large documents into sections
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
5. Claude Code sees the message: "Context files regenerated in output/context/..."

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

Teams are defined in `team/manifest.yaml`:

| Team | Members | Best For |
|------|---------|----------|
| **fullstack** | analyst, architect, pm, ux-designer | Planning, architectural decisions |
| **implementation** | dev, tea, tech-writer | Parallel development, test coverage |
| **creative** | creative-thinking-coach, design-strategy-coach, storyteller-presenter | Innovation, creative problem solving |

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
3. Claude invokes the Oracle (or you type `/team:oracle`)
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
- Try invoking manually: `/team:oracle`

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
- Check `team/manifest.yaml` for team definitions
