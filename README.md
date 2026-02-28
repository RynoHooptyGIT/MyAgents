# BMAD Method v6

**Build, Manage, Architect, Deploy** -- An AI-assisted software development methodology that brings structure, discipline, and specialist expertise to every phase of your project lifecycle.

BMAD v6 provides **34 specialist agents**, **70+ workflows**, and an **Oracle orchestrator** that together guide your project from initial concept through production deployment. It works with your existing AI coding tools -- Claude Code, Cursor, or GitHub Copilot -- to enforce lifecycle discipline, maintain sprint state, and ensure consistent quality.

## What BMAD Does

Instead of relying on ad-hoc AI prompting, BMAD provides a structured methodology where:

- An **Oracle agent (Athena)** activates at the start of every session, reads your sprint state, and enforces the full implementation lifecycle
- **Specialist agents** (architect, security auditor, test architect, UX designer, etc.) provide domain expertise on demand
- **Structured workflows** guide every activity from product brief creation through code review and shipping
- A **sprint-status.yaml** file serves as the single source of truth for all project state
- **Context generation** keeps AI agents informed about your codebase structure, API surface, and database schema

## Four Modules

BMAD is organized into four modules that work together:

| Module | Name | Purpose |
|--------|------|---------|
| `core` | Core Platform | Workflow execution engine, brainstorming, party mode, shared tasks and resources |
| `bmm` | BMAD Main Method | 22 agents + 45+ workflows covering the full software development lifecycle |
| `bmb` | Builders | 3 agents + 3 workflows for creating custom agents, workflows, and modules |
| `cis` | Creative Innovation Suite | 6 agents + 4 workflows for brainstorming, design thinking, and storytelling |

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

Every session begins with the Oracle reading `sprint-status.yaml`, presenting a project brief with current state and recommendations, and displaying a command menu. The Oracle translates high-level directives ("implement story 7-3") into the correct workflow sequence and executes it.

## Quick Start

```bash
# 1. Clone the template into your project
git clone https://github.com/your-org/bmad-method-v6.git
cd bmad-method-v6

# 2. Run the interactive setup script
bash scripts/setup.sh

# 3. Configure context generation for your tech stack
#    Edit scripts/context/context-config.yaml

# 4. Start a session -- the Oracle activates automatically
#    In Claude Code: /bmad:bmm:agents:oracle
#    In Cursor: Oracle loads via alwaysApply .mdc rule
#    In Copilot: Ask the AI to load _bmad/bmm/agents/oracle.md
```

The setup script prompts for your project name, user name, git branch conventions, GitHub repository, and which AI tool you use. It configures everything automatically.

## Supported AI Tools

| Tool | Support Level | Key Integration |
|------|--------------|-----------------|
| **Claude Code** | Full | 81 slash commands, PostToolUse hooks, agent teams, settings.local.json |
| **Cursor** | Good | .cursor/rules/ with .mdc files, alwaysApply Oracle activation |
| **GitHub Copilot** | Partial | copilot-instructions.md, manual agent invocation |

See [docs/TOOL-COMPATIBILITY.md](docs/TOOL-COMPATIBILITY.md) for a detailed feature matrix.

## Key Concepts

**Agents** are persona-driven specialists. Each has a name, communication style, domain expertise, and an activation protocol. The Oracle orchestrates them. See [docs/AGENT-CATALOG.md](docs/AGENT-CATALOG.md).

**Workflows** are structured step-by-step processes. They load configuration from YAML files, resolve variables, execute instructions in order, and produce output artifacts. See [docs/WORKFLOW-CATALOG.md](docs/WORKFLOW-CATALOG.md).

**Sprint Status** (`sprint-status.yaml`) tracks every epic and story through the lifecycle. The Oracle reads it before every decision and updates it after every status change.

**Context Files** (`_bmad-output/context/`) are auto-generated summaries of your codebase -- module index, API endpoints, database schema, code patterns, and sprint digest. A post-commit hook keeps them fresh.

## Documentation

| Document | Description |
|----------|-------------|
| [Quick Start Guide](docs/QUICKSTART.md) | Step-by-step new project setup |
| [Architecture](docs/ARCHITECTURE.md) | How BMAD works internally |
| [Agent Catalog](docs/AGENT-CATALOG.md) | All 34 agents with descriptions |
| [Workflow Catalog](docs/WORKFLOW-CATALOG.md) | All 70+ workflows by phase |
| [Tool Compatibility](docs/TOOL-COMPATIBILITY.md) | Feature matrix for Claude Code, Cursor, Copilot |
| [Customization](docs/CUSTOMIZATION.md) | Adding agents, workflows, and project rules |
| [Claude Code Guide](ide-guides/claude-code.md) | Full Claude Code integration setup |
| [Cursor Guide](ide-guides/cursor.md) | Cursor IDE adaptation |
| [Copilot Guide](ide-guides/copilot.md) | GitHub Copilot adaptation |

## Repository Structure

```
bmad-method-v6/
  _bmad/                    # BMAD system files
    _config/                # Manifests, team configs, agent customization
    _memory/                # Session memory (auto-managed)
    core/                   # Workflow engine, brainstorming, shared tasks
    bmm/                    # Main methodology (agents, workflows, data)
    bmb/                    # Builder tools (agent, workflow, module creation)
    cis/                    # Creative innovation suite
  claude-commands/          # 81 slash commands for Claude Code
  hooks/                    # Post-commit context regeneration hook
  templates/                # Configuration templates (CLAUDE.md, settings, cursor rules)
  scripts/                  # Setup and context generation scripts
  docs/                     # Documentation
  ide-guides/               # IDE-specific setup guides
```

## Version

BMAD Method v6.0.0-alpha.23
