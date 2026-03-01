# My Dev Team

**27 specialist AI agents**, **70+ workflows**, and an **Oracle orchestrator** that together guide your project from initial concept through production deployment. Works with Claude Code, Cursor, or GitHub Copilot to enforce lifecycle discipline, maintain sprint state, and ensure consistent quality.

## What It Does

Instead of relying on ad-hoc AI prompting, this methodology provides a structured system where:

- An **Oracle agent (Athena)** activates at the start of every session, reads your sprint state, and enforces the full implementation lifecycle
- **Specialist agents** (architect, security auditor, test architect, UX designer, etc.) provide domain expertise on demand
- **Structured workflows** guide every activity from product brief creation through code review and shipping
- A **sprint-status.yaml** file serves as the single source of truth for all project state
- **Context generation** keeps AI agents informed about your codebase structure, API surface, and database schema

## The Oracle Lifecycle

The Oracle enforces a strict implementation lifecycle with gates at every transition:

```
Create Story (CS)  -->  Dev Story (DS)  -->  Code Review (CR)  -->  Ship (SH)
     |                       |                      |                    |
  Story file            Story status           Story status         Story status
  must exist            set to                 must be              must be
  before dev            in-progress            in-progress          done before
  can begin             before review          before shipping      PR creation
```

Every session begins with the Oracle reading `sprint-status.yaml`, presenting a project brief with current state and recommendations, and displaying a command menu.

## Quick Start

```bash
# 1. Clone the template into your project
git clone https://github.com/your-org/my-dev-team.git
cd my-dev-team

# 2. Run the interactive setup script
bash scripts/setup.sh

# 3. Configure context generation for your tech stack
#    Edit scripts/context/context-config.yaml

# 4. Start a session -- the Oracle activates automatically
#    In Claude Code: /team:oracle
#    In Cursor: Oracle loads via alwaysApply .mdc rule
#    In Copilot: Ask the AI to load team/agents/oracle.md
```

## Supported AI Tools

| Tool | Support Level | Key Integration |
|------|--------------|-----------------|
| **Claude Code** | Full | 76 slash commands, PostToolUse hooks, agent teams, settings.local.json |
| **Cursor** | Good | .cursor/rules/ with .mdc files, alwaysApply Oracle activation |
| **GitHub Copilot** | Partial | copilot-instructions.md, manual agent invocation |

See [docs/TOOL-COMPATIBILITY.md](docs/TOOL-COMPATIBILITY.md) for a detailed feature matrix.

## Key Concepts

**Agents** are persona-driven specialists. Each has a name, communication style, domain expertise, and an activation protocol. The Oracle orchestrates them. See [docs/AGENT-CATALOG.md](docs/AGENT-CATALOG.md).

**Workflows** are structured step-by-step processes. They load configuration from YAML files, resolve variables, execute instructions in order, and produce output artifacts. See [docs/WORKFLOW-CATALOG.md](docs/WORKFLOW-CATALOG.md).

**Sprint Status** (`sprint-status.yaml`) tracks every epic and story through the lifecycle. The Oracle reads it before every decision and updates it after every status change.

**Context Files** (`output/context/`) are auto-generated summaries of your codebase -- module index, API endpoints, database schema, code patterns, and sprint digest. A post-commit hook keeps them fresh.

## Documentation

| Document | Description |
|----------|-------------|
| [Quick Start Guide](docs/QUICKSTART.md) | Step-by-step new project setup |
| [Architecture](docs/ARCHITECTURE.md) | How the system works internally |
| [Agent Catalog](docs/AGENT-CATALOG.md) | All 27 agents with descriptions |
| [Workflow Catalog](docs/WORKFLOW-CATALOG.md) | All 70+ workflows by phase |
| [Tool Compatibility](docs/TOOL-COMPATIBILITY.md) | Feature matrix for Claude Code, Cursor, Copilot |
| [Customization](docs/CUSTOMIZATION.md) | Adding agents, workflows, and project rules |
| [Claude Code Guide](ide-guides/claude-code.md) | Full Claude Code integration setup |
| [Cursor Guide](ide-guides/cursor.md) | Cursor IDE adaptation |
| [Copilot Guide](ide-guides/copilot.md) | GitHub Copilot adaptation |

## Repository Structure

```
my-dev-team/
  team/                     # Agent team system
    config.yaml             # Unified configuration
    manifest.yaml           # Team definitions
    agent-manifest.csv      # Agent registry
    agents/                 # All 27 agents (flat)
    workflows/              # All workflows by category
    engine/                 # Workflow execution engine (workflow.xml)
    resources/              # Shared resources (excalidraw helpers)
    data/                   # Project data and knowledge bases
    teams/                  # Team composition files
  claude-commands/team/     # 76 slash commands for Claude Code
  output/                   # Generated artifacts and context
  hooks/                    # Post-commit context regeneration hook
  templates/                # Configuration templates
  scripts/                  # Setup and context generation scripts
  docs/                     # Documentation
  ide-guides/               # IDE-specific setup guides
```
