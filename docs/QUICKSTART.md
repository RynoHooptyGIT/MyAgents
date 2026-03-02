# My Dev Team — Quick Start Guide

This guide walks you through setting up My Dev Team for a new project, from installation through your first development sprint.

## Prerequisites

- Git
- Python 3.8+ (for context generation scripts)
- An AI coding tool: Claude Code, Cursor, or GitHub Copilot
- `jq` (used by post-commit hooks; optional but recommended)

## Step 1: Clone or Copy Into Your Project

**Option A: Clone as template (new project)**

```bash
git clone https://github.com/your-org/my-dev-team.git my-project
cd my-project
```

**Option B: Copy into an existing project**

Copy the following directories and files into your project root:

```
team/               # Agent team system (agents, workflows, config)
claude-commands/    # Slash commands (Claude Code only)
hooks/              # Post-commit hook
scripts/            # Setup and context generation
templates/          # Configuration templates
```

## Step 2: Run the Setup Script

```bash
bash scripts/setup.sh
```

The setup script walks you through an interactive configuration process:

| Prompt | What It Does | Example |
|--------|-------------|---------|
| **Project name** | Sets `{project_name}` used throughout agents and workflows | `my-saas-app` |
| **User name** | Sets `{user_name}` for personalized agent greetings | `Sarah` |
| **Base branch** | Git branch for feature branches (PRs target this) | `develop` |
| **Production branch** | Branch that represents production | `main` |
| **GitHub owner/repo** | Enables GitHub issue sync (optional) | `acme/my-saas-app` |
| **AI tool** | Configures IDE-specific files (CLAUDE.md, .mdc rules, etc.) | `claude-code` |

The setup script generates:

- `team/config.yaml` from `templates/config.yaml.template`
- `.claude/settings.local.json` from `templates/settings.local.json.template` (Claude Code)
- `.cursor/rules/` from `templates/cursor-rules/` (Cursor)
- `.github/copilot-instructions.md` (GitHub Copilot)
- `CLAUDE.md` with Oracle activation protocol (Claude Code)

## Step 3: Configure Context Generation

If your project has an existing codebase, configure the context generation system to scan your tech stack.

Edit `scripts/context/context-config.yaml`:

```yaml
# Define scan paths for your project
scan_paths:
  frontend:
    root: "packages/frontend/src"       # Adjust to your frontend path
    features_glob: "features/*/index.ts"
  backend:
    root: "backend"                      # Adjust to your backend path
    routers_glob: "routers/*.py"
    models_glob: "models/*.py"

# Define which context files to generate
generators:
  module_index: true     # Feature map of frontend modules + backend services
  api_index: true        # All API endpoints by router
  schema_digest: true    # Database schema from models
  patterns: true         # Canonical code patterns
  sprint_digest: true    # Sprint status summary
```

Then run the generator manually to create initial context files:

```bash
python scripts/context/generate_all.py
```

This creates files in `output/context/`:

| File | Contents |
|------|----------|
| `module-index.md` | Feature map of all frontend modules and backend services |
| `api-index.md` | Every API endpoint organized by router |
| `schema-digest.md` | Database tables extracted from model definitions |
| `patterns.md` | Canonical code patterns extracted from the codebase |
| `sprint-digest.md` | Pre-computed sprint summary from sprint-status.yaml |

## Step 4: Add Project-Specific Technical Rules

Open `CLAUDE.md` (or your IDE's equivalent instructions file) and add your project's technical rules to the Technical Rules section:

```markdown
## Critical Technical Rules

- **Framework**: React 18 with TypeScript strict mode
- **State Management**: Zustand 4.5+ with skipHydration for persisted stores
- **API Client**: React Query 5 with object syntax for useQuery
- **Backend**: Python FastAPI with SQLAlchemy 2.0 async patterns
- **Database**: PostgreSQL with Row Level Security -- use set_config(), never SET
- **CSS**: MUI v6 with dark theme base (#08090a)
- **Tests**: Vitest + React Testing Library (frontend), pytest (backend)
```

These rules are injected into every AI session and enforced by agents during code review.

## Step 5: Initialize Your Sprint

Start a session with the Oracle agent:

**Claude Code:**
```
/team:oracle
```

**Cursor:** The Oracle activates automatically via the `000-bmad-oracle.mdc` rule with `alwaysApply: true`.

**Copilot:** Ask the AI:
> Load the agent from `team/agents/oracle.md` and follow its activation protocol.

The Oracle will:
1. Load `config.yaml` and read your project settings
2. Check for `sprint-status.yaml` (will note it does not exist yet)
3. Present a project brief
4. Display its command menu

Select **[SP] Sprint Planning** to create your initial `sprint-status.yaml`. The sprint planning workflow will:
- Look for epic files in `output/planning-artifacts/`
- Extract all epics and stories into a tracking structure
- Create `output/implementation-artifacts/sprint-status.yaml`

If you do not have epic files yet, work through the planning phases first:
1. **Create Product Brief** -- `/team:create-product-brief`
2. **Create PRD** -- `/team:prd`
3. **Create Architecture** -- `/team:create-architecture`
4. **Create Epics and Stories** -- `/team:create-epics-and-stories`
5. **Sprint Planning** -- Oracle menu [SP]

## Step 6: Create Your First Story and Start Developing

With the Oracle active and sprint initialized:

1. **Create Story [CS]** -- Generates a detailed story file from an epic, with tasks, subtasks, and acceptance criteria
2. **Dev Story [DS]** -- Implements the story by executing each task, writing tests, and updating the story file
3. **Code Review [CR]** -- Performs an adversarial review that finds 3-10 specific issues and fixes them
4. **Ship [SH]** -- Commits changes, pushes to remote, and creates a pull request

The Oracle enforces this lifecycle automatically. If you try to run code review before implementing, or ship before reviewing, the Oracle will refuse and redirect you to the correct step.

## What Happens Each Session

Every new session follows the same pattern:

1. Oracle activates (automatically or via slash command)
2. Oracle reads `config.yaml` and `sprint-status.yaml`
3. Oracle loads context files from `output/context/`
4. Oracle presents a project brief with current state and recommendation
5. Oracle displays the command menu and waits for your direction
6. You choose what to work on; Oracle determines and executes the correct workflow

## Verifying Your Setup

After setup, verify everything is configured correctly:

```bash
# Check that config was generated
cat team/config.yaml

# Check that context files exist (if you have a codebase)
ls output/context/

# Check context freshness
python scripts/context/generate_all.py --check

# Verify slash commands are available (Claude Code)
ls claude-commands/team/oracle.md
```

## Next Steps

- Read the [Architecture Guide](ARCHITECTURE.md) to understand how the system works internally
- Browse the [Agent Catalog](AGENT-CATALOG.md) to see all available specialist agents
- Review the [Workflow Catalog](WORKFLOW-CATALOG.md) for the complete list of workflows
- See your IDE-specific guide: [Claude Code](../ide-guides/claude-code.md) | [Cursor](../ide-guides/cursor.md) | [Copilot](../ide-guides/copilot.md)
