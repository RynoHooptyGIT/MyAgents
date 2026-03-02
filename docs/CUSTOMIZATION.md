# My Dev Team — Customization Guide

The system is designed to be extended and customized for your specific project needs. This guide covers adding custom agents, workflows, and modules, customizing existing components, configuring teams, and managing context generation.

---

## Adding Custom Agents

### Using the Agent Builder (Recommended)

The easiest way to create a compliant agent is through the Agent Builder workflow:

**Claude Code:**
```
/team:agent-builder
```

**Other tools:**
```
Load the agent from team/agents/agent-builder.md and follow its activation protocol.
```

Bond (the Agent Builder) guides you through an 8-step process:

1. **Brainstorm** -- Define what the agent should do and why
2. **Discovery** -- Explore the domain and identify capabilities
3. **Type and Metadata** -- Choose agent type (simple, expert, or module)
4. **Persona** -- Define name, role, identity, communication style, and principles
5. **Commands and Menu** -- Design the agent's menu items and handlers
6. **Activation** -- Define the activation protocol (config loading, data reading)
7. **Build** -- Generate the agent file
8. **Celebrate** -- Review and finalize

The builder produces a compliant agent file with proper structure, activation protocol, persona, menu, and handlers.

### Manual Agent Creation

Create a new `.md` file in the appropriate module's `agents/` directory:

```
team/agents/my-agent.md      # For project-specific agents
team/agents/my-agent.md      # For creative/innovation agents
```

Follow this structure:

```markdown
---
name: "my-agent"
description: "Short description of the agent"
---

You must fully embody this agent's persona and follow all activation instructions exactly as specified.

<agent id="my-agent" name="PersonaName" title="Agent Title" icon="...">
  <activation critical="MANDATORY">
    <step n="1">Load persona from this current agent file</step>
    <step n="2">Load and read {project-root}/team/config.yaml
      Store fields as session variables: {user_name}, {project_name}
    </step>
    <step n="3">Remember: user's name is {user_name}</step>
    <step n="4">Present greeting and display menu</step>
    <step n="5">WAIT for user input</step>
  </activation>

  <persona>
    <role>What this agent does</role>
    <identity>Background, expertise, personality</identity>
    <communication_style>How the agent communicates</communication_style>
    <principles>
      - Core principle 1
      - Core principle 2
    </principles>
  </persona>

  <menu>
    <item cmd="1 or keyword" workflow="{project-root}/team/workflows/path/workflow.yaml">[1] Menu Item</item>
    <item cmd="2 or keyword" action="#my-prompt">[2] Another Item</item>
    <item cmd="DA or exit">[DA] Dismiss Agent</item>
  </menu>

  <prompts>
    <prompt id="my-prompt">
      Instructions for this action...
    </prompt>
  </prompts>
</agent>
```

### Registering the Agent

After creating the agent file, add it to `team/agent-manifest.csv`:

```csv
"my-agent","PersonaName","Agent Title","...icon...","Role description","Identity description","Communication style","Principles","bmm","team/agents/my-agent.md","team-name"
```

### Creating a Slash Command (Claude Code)

Create a corresponding command file in `claude-commands/`:

```
claude-commands/bmm/agents/my-agent.md
```

Content:
```markdown
Load and fully activate the agent: $ARGUMENTS

@team/agents/my-agent.md
```

---

## Adding Custom Workflows

### Using the Workflow Builder (Recommended)

**Claude Code:**
```
/team:workflow
```

**Other tools:**
```
Load the agent from team/agents/workflow-builder.md and follow its activation protocol.
```

Wendy (the Workflow Builder) guides you through creating a structured workflow with proper YAML configuration, instruction steps, templates, and validation.

### Manual Workflow Creation

Create a new directory in the appropriate workflow group:

```
team/workflows/my-category/my-workflow/
  workflow.yaml       # Configuration (required)
  instructions.md     # Step-by-step instructions (required)
  template.md         # Output template (optional, for document workflows)
  checklist.md        # Validation checklist (optional)
```

**workflow.yaml** structure:

```yaml
name: "my-workflow"
description: "What this workflow does"
version: "1.0.0"

# Module configuration source
config_source: "{project-root}/team/config.yaml"

# Instructions file
instructions: "{installed_path}/instructions.md"

# Output template (omit for action-only workflows)
template: "{installed_path}/template.md"
default_output_file: "{config_source}:output_folder/my-output-{{date}}.md"

# Input file patterns (optional - for discover_inputs protocol)
input_file_patterns:
  prd:
    whole: "{config_source}:output_folder/*prd*.md"
    sharded: "{config_source}:output_folder/*prd*/*.md"
    load_strategy: "FULL_LOAD"
```

**instructions.md** structure:

```markdown
# My Workflow Instructions

## Step 1: Initialize

<action>Load all required context</action>
<invoke-protocol name="discover_inputs" />

## Step 2: Analysis

<action>Analyze the loaded content</action>
<template-output section="analysis">
Generate the analysis based on loaded inputs.
</template-output>

## Step 3: Complete

<action>Summarize findings and save output</action>
```

### Registering the Workflow

Add to `team/workflow-manifest.csv`:

```csv
"my-workflow","What this workflow does","bmm","team/workflows/my-category/my-workflow/workflow.yaml"
```

### Creating a Slash Command (Claude Code)

Create `claude-commands/bmm/workflows/my-workflow.md`:

```markdown
Execute this workflow: $ARGUMENTS

@team/engine/workflow.xml
@team/workflows/my-category/my-workflow/workflow.yaml
```

---

## Customizing Existing Agents

Each BMM agent has a customization sidecar file in `team/agents/`:

```
team/agents/bmm-dev.customize.yaml
team/agents/bmm-architect.customize.yaml
...
```

These YAML files allow you to override agent behavior without modifying the core agent file. Available customizations include:

- **Additional principles**: Add project-specific principles to the agent's core principles
- **Menu overrides**: Add or modify menu items
- **Communication style adjustments**: Modify how the agent communicates
- **Domain knowledge**: Add project-specific domain knowledge

Example `bmm-dev.customize.yaml`:

```yaml
# Additional principles for the Developer agent
additional_principles:
  - "Always use TypeScript strict mode"
  - "Follow the repository's established patterns in project-context.md"
  - "Write co-located test files (Component.test.tsx next to Component.tsx)"

# Additional menu items
additional_menu_items:
  - cmd: "PC"
    label: "[PC] Pattern Check - Verify code follows project patterns"
    action: "#pattern-check"

# Additional prompts
additional_prompts:
  pattern-check: |
    Load project-context.md and verify the current implementation
    follows all established patterns. Report any violations.
```

---

## Configuring Teams

Teams are defined in `team/manifest.yaml` under the `teams` section:

```yaml
teams:
  my-custom-team:
    name: "My Custom Team"
    members:
      - dev
      - architect
      - security-auditor
    best_for:
      - "Security-focused feature development"
      - "Architecture reviews with security perspective"
```

### Team Member Names

Use the agent's `name` field (from agent-manifest.csv) as the member identifier:

| Name | Agent |
|------|-------|
| `analyst` | Mary (Business Analyst) |
| `architect` | Winston (Architect) |
| `dev` | Amelia (Developer) |
| `pm` | John (Product Manager) |
| `oracle` | Athena (Project Oracle) |
| `tea` | Murat (Test Architect) |
| `tech-writer` | Paige (Tech Writer) |
| `ux-designer` | Sally (UX Designer) |
| `quick-flow-solo-dev` | Barry (Quick Flow Solo Dev) |
| `custodian` | Sentinel (Custodian) |
| `security-auditor` | Shield (Security) |
| `devops` | Forge (DevOps) |
| `api-contract` | Pact (API Contract) |
| `data-architect` | Oracle (Data Architect) |
| `agentic-expert` | Nexus (Agentic Expert) |
| `ml-expert` | Neuron (ML Expert) |
| `nist-rmf-expert` | Atlas (NIST RMF) |
| `healthcare-expert` | Dr. Vita (Healthcare) |
| `government-expert` | Senator (Government) |
| `financial-expert` | Sterling (Financial) |
| `creative-thinking-coach` | Carson (Creative Thinking) |
| `design-strategy-coach` | Maya (Design & Strategy) |
| `storyteller-presenter` | Sophia (Storyteller & Presenter) |

### Team Configuration Options

```yaml
teams:
  enabled: true              # Enable/disable team features globally
  default_mode: "auto"       # "auto", "in-process", or "tmux"
  auto_spawn_threshold: 3    # Auto-suggest teams for 3+ parallel tasks
  preferred_teams:
    - fullstack              # Default team selection order
    - implementation
  token_budget_multiplier: 2.5  # Teams use ~2.5x more tokens
```

---

## Context Generation Configuration

The context generation system scans your codebase and produces summary files that AI agents use for navigation and decision-making.

### Configuration File

Edit `scripts/context/context-config.yaml` to define scan paths for your technology stack:

```yaml
# Frontend configuration
frontend:
  root: "packages/frontend/src"
  features_glob: "features/*/index.ts"
  components_glob: "components/**/*.tsx"
  hooks_glob: "hooks/**/*.ts"
  stores_glob: "stores/**/*.ts"

# Backend configuration
backend:
  root: "backend"
  routers_glob: "routers/*.py"
  models_glob: "models/*.py"
  services_glob: "services/*.py"
  migrations_glob: "alembic/versions/*.py"

# Output configuration
output:
  directory: "output/context"
  files:
    - module_index     # Feature map
    - api_index        # API endpoints
    - schema_digest    # Database schema
    - patterns         # Code patterns
    - sprint_digest    # Sprint summary
```

### Adding Custom Generators

You can add custom context generators by creating new Python scripts in `scripts/context/` and registering them in `context-config.yaml`. Custom generators should:

1. Scan specified paths using glob patterns
2. Extract structured information
3. Write a markdown summary file to `output/context/`
4. Be fast enough to run on every commit (under 5 seconds ideally)

### Manual Regeneration

```bash
# Regenerate all context files
python scripts/context/generate_all.py

# Regenerate only sprint digest
python scripts/context/generate_all.py --sprint

# Check if context files are stale (no regeneration)
python scripts/context/generate_all.py --check
```

---

## Project-Specific Technical Rules

The most impactful customization is adding your project's technical rules to the AI instructions file. These rules are enforced by every agent during implementation and code review.

### CLAUDE.md (Claude Code)

Add to the `## Critical Technical Rules` section:

```markdown
## Critical Technical Rules

- **Pydantic v2.6+** -- Never use v1 patterns (class Config, validator, root_validator)
- **SQLAlchemy 2.0** -- async patterns only, never legacy 1.x sync patterns
- **PostgreSQL RLS** -- Use SELECT set_config(), never SET app.variable
- **MUI v6** -- Use @mui/material imports, dark theme base (#08090a)
- **React Query 5** -- Object syntax: useQuery({ queryKey, queryFn })
- **Tests** -- Vitest + RTL (frontend), pytest (backend); co-located test files
```

### project-context.md

For more comprehensive rules, generate a `project-context.md` file:

```
/team:generate-project-context
```

This workflow scans your codebase and produces a concise file with critical rules and patterns optimized for LLM context efficiency. It is loaded by the Oracle at session start and referenced by the Developer agent during implementation.

---

## Adding to the Oracle's Routing Table

To add custom agents to the Oracle's routing table, edit the `route-to-agent` prompt in `team/agents/oracle.md`:

```xml
<prompt id="route-to-agent">
  ...existing routing table...
  | My custom domain | CustomAgent (MyAgent) | /team:my-agent |
</prompt>
```

This allows the Oracle to route users to your custom agent when they ask about that domain.

---

## Creating Custom Modules

For large-scale customization, create an entirely new module using the Module Builder:

**Claude Code:**
```
/team:module-builder
```

Morgan (the Module Builder) guides you through creating a complete module with:
- `config.yaml` -- Module configuration
- `agents/` -- Module-specific agents
- `workflows/` -- Module-specific workflows
- `teams/` -- Team configurations
- `README.md` -- Module documentation
- Installer script for integration with the core system

After creation, register the module in `team/manifest.yaml`:

```yaml
modules:
  - core
  - bmb
  - bmm
  - cis
  - my-module   # Your custom module
```

---

## Best Practices

1. **Prefer customization sidecar files** over editing core agent files. This makes upgrades easier.
2. **Use the builders** (Bond, Wendy, Morgan) for creating new components. They ensure system compliance.
3. **Register everything** in the manifest CSV files. Unregistered agents and workflows may not be discoverable.
4. **Create slash commands** for Claude Code users. They significantly improve the workflow.
5. **Test custom agents** by invoking them and running through their full menu before using in production.
6. **Keep context generators fast**. They run on every commit -- slow generators will degrade the development experience.
7. **Document your customizations** in a project-specific section of CLAUDE.md or your IDE instructions file.
