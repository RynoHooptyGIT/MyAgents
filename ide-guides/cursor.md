# BMAD v6 -- Cursor IDE Setup Guide

Cursor provides good BMAD support through its `.cursor/rules/` system with `.mdc` files. This guide covers how to set up and use BMAD effectively in Cursor.

## Overview

| Feature | Status |
|---------|--------|
| Oracle auto-activation | Full (alwaysApply .mdc rule) |
| Slash commands | Not available |
| Post-commit hooks | Not available |
| Agent teams | Not available |
| Context file usage | Full |
| Workflow engine | Good |
| Agent personas | Good |
| Sprint tracking | Full |
| File references | @ prefix in chat |
| MCP tools | Some (depends on Cursor version) |

---

## Step 1: Create the Rules Directory

```bash
mkdir -p .cursor/rules
```

Cursor automatically reads all `.mdc` files from `.cursor/rules/` and applies them based on their configuration.

---

## Step 2: Oracle Activation Rule (Always Active)

Create `.cursor/rules/000-bmad-oracle.mdc`:

```markdown
---
alwaysApply: true
---

# BMAD Oracle Activation Protocol

## MANDATORY: Every Session

This project uses the BMAD Methodology (v6). The Oracle agent (Athena) MUST be activated
at the start of EVERY conversation.

### Activation Steps

1. Load the Oracle agent from `_bmad/bmm/agents/oracle.md` and follow its complete activation protocol
2. Load project config from `_bmad/bmm/config.yaml` -- store project_name, user_name, output paths
3. Load sprint digest from `_bmad-output/context/sprint-digest.md` for quick sprint overview
4. Load full sprint state from `_bmad-output/implementation-artifacts/sprint-status.yaml`
5. Load project context from `_bmad-output/project-context.md` if it exists
6. Load module index from `_bmad-output/context/module-index.md` if it exists
7. Parse sprint data: count stories by status, identify active epic, find in-progress/review stories
8. Present a PROJECT BRIEF with: current epic, in-flight stories, recommendation
9. Display the Oracle's numbered menu and WAIT for user input
10. On user selection, execute the corresponding workflow or action

### Implementation Lifecycle (Enforced by Oracle)

1. **Create Story (CS)** -- Story file must exist before development begins
2. **Dev Story (DS)** -- Implement the story following tasks and acceptance criteria
3. **Code Review (CR)** -- Adversarial review that finds 3-10 issues and fixes them
4. **Ship (SH)** -- Commit, push, and create pull request

Never skip steps. The Oracle enforces gates at each transition.
```

The `alwaysApply: true` frontmatter ensures this rule is loaded in every Cursor chat session, providing the same auto-activation behavior as CLAUDE.md in Claude Code.

---

## Step 3: Lifecycle Enforcement Rule

Create `.cursor/rules/001-bmad-lifecycle.mdc`:

```markdown
---
alwaysApply: true
---

# BMAD Implementation Lifecycle Rules

## Lifecycle Gates

Before executing any implementation workflow, verify these pre-conditions:

- **Before Dev Story**: A story file MUST exist in `_bmad-output/implementation-artifacts/stories/`
  for the target story. If missing, run Create Story (CS) first.
- **Before Code Review**: Story status MUST be `in-progress` or `review` in sprint-status.yaml.
  If not, run Dev Story (DS) first.
- **Before Ship**: Story status MUST be `done` in sprint-status.yaml (code review passed).
  If not, run Code Review (CR) first.

## Sprint Status Updates

Update `_bmad-output/implementation-artifacts/sprint-status.yaml` when story status changes:
- Create Story: Set to `ready-for-dev`
- Dev Story start: Set to `in-progress`
- Code Review start: Set to `review`
- Code Review pass: Set to `done`

## Workflow Engine

All BMAD workflows are executed through the workflow engine at `_bmad/core/tasks/workflow.xml`.
When executing a workflow:
1. Load workflow.yaml from the specified path
2. Load config from config_source (usually `_bmad/bmm/config.yaml`)
3. Resolve all variables: {project-root}, {installed_path}, {config_source}:field
4. Read instruction files completely (never use offset/limit)
5. Execute ALL steps IN EXACT ORDER
6. Save outputs after every template-output tag
```

---

## Step 4: Context System Rule

Create `.cursor/rules/002-bmad-context.mdc`:

```markdown
---
alwaysApply: true
---

# BMAD Agent Context System

## Pre-Generated Context Files

Use these files instead of scanning the full codebase:

- `_bmad-output/context/module-index.md` -- Feature map of frontend modules + backend services
- `_bmad-output/context/sprint-digest.md` -- Pre-computed sprint summary
- `_bmad-output/context/api-index.md` -- All API endpoints by router
- `_bmad-output/context/schema-digest.md` -- Database schema from models
- `_bmad-output/context/patterns.md` -- Canonical code patterns to follow

Also: `_bmad-output/project-context.md` -- Critical implementation rules (if it exists).

## Regeneration

Context files are NOT auto-regenerated in Cursor. After git commits, manually run:

```
python scripts/context/generate_all.py
```

Check freshness: `python scripts/context/generate_all.py --check`
```

---

## Step 5: Project-Specific Rules (Optional)

Create `.cursor/rules/003-project-rules.mdc` with your project's technical rules:

```markdown
---
alwaysApply: true
---

# Project Technical Rules

<!-- Customize these for your project -->

- **TypeScript**: Strict mode, no any types
- **React**: Functional components only, React Query 5 object syntax
- **State**: Zustand 4.5+ with skipHydration for persisted stores
- **Backend**: FastAPI + SQLAlchemy 2.0 async patterns
- **Database**: PostgreSQL RLS -- use set_config(), never SET app.variable
- **Tests**: Vitest + RTL (frontend), pytest (backend), co-located test files
- **CSS**: MUI v6, dark theme base (#08090a)
```

---

## Invoking Agents

Since Cursor has no slash commands, invoke agents using `@` file references in chat:

### Using @ References

```
Load @_bmad/bmm/agents/oracle.md and follow its activation protocol.
```

```
Load @_bmad/bmm/agents/architect.md and follow its activation protocol.
```

```
Load @_bmad/bmm/agents/security-auditor.md and follow its activation protocol.
```

The `@` prefix in Cursor chat tells the AI to read the referenced file and include it in context.

### Agent Quick Reference

| Agent | @ Reference |
|-------|-------------|
| Oracle (Athena) | `@_bmad/bmm/agents/oracle.md` |
| Architect (Winston) | `@_bmad/bmm/agents/architect.md` |
| Developer (Amelia) | `@_bmad/bmm/agents/dev.md` |
| Test Architect (Murat) | `@_bmad/bmm/agents/tea.md` |
| Security (Shield) | `@_bmad/bmm/agents/security-auditor.md` |
| DevOps (Forge) | `@_bmad/bmm/agents/devops.md` |
| Custodian (Sentinel) | `@_bmad/bmm/agents/custodian.md` |
| Navigator (Navi) | `@_bmad/bmm/agents/navigator.md` |
| UX Designer (Sally) | `@_bmad/bmm/agents/ux-designer.md` |
| Product Manager (John) | `@_bmad/bmm/agents/pm.md` |
| Data Architect (Oracle) | `@_bmad/bmm/agents/data-architect.md` |
| Brainstorming (Carson) | `@_bmad/cis/agents/brainstorming-coach.md` |
| Agent Builder (Bond) | `@_bmad/bmb/agents/agent-builder.md` |

---

## Executing Workflows

To execute a workflow, reference both the workflow engine and the specific workflow:

```
Execute @_bmad/bmm/workflows/4-implementation/code-review/workflow.yaml
using the engine at @_bmad/core/tasks/workflow.xml.
```

### Common Workflows

| Workflow | @ References |
|----------|-------------|
| Create Story | `@_bmad/bmm/workflows/4-implementation/create-story/workflow.yaml` |
| Dev Story | `@_bmad/bmm/workflows/4-implementation/dev-story/workflow.yaml` |
| Code Review | `@_bmad/bmm/workflows/4-implementation/code-review/workflow.yaml` |
| Ship | `@_bmad/bmm/workflows/devops/ship/workflow.yaml` |
| Sprint Planning | `@_bmad/bmm/workflows/4-implementation/sprint-planning/workflow.yaml` |
| PRD | `@_bmad/bmm/workflows/2-plan-workflows/prd/workflow.md` |
| Architecture | `@_bmad/bmm/workflows/3-solutioning/create-architecture/workflow.md` |
| Quick Dev | `@_bmad/bmm/workflows/bmad-quick-flow/quick-dev/workflow.md` |

### Workflow Engine Reference

Always include the workflow engine when executing workflows:

```
@_bmad/core/tasks/workflow.xml
```

This tells the AI how to parse workflow.yaml, resolve variables, and execute steps.

---

## Context File Management

### Manual Regeneration

Cursor does not support hooks, so regenerate context manually:

```bash
# Full regeneration (all 5 context files)
python scripts/context/generate_all.py

# Sprint-only (faster, for status changes)
python scripts/context/generate_all.py --sprint

# Check freshness without regenerating
python scripts/context/generate_all.py --check
```

### Git Hook Alternative

You can set up a standard git post-commit hook to auto-regenerate:

```bash
# Create .git/hooks/post-commit
cat > .git/hooks/post-commit << 'EOF'
#!/bin/bash
python scripts/context/generate_all.py 2>/dev/null &
EOF
chmod +x .git/hooks/post-commit
```

This runs the generator in the background after every git commit, regardless of what tool made the commit. Note: this is a standard git hook, not a Cursor-specific feature, and it runs in the background to avoid slowing down commits.

---

## Sprint Tracking

Sprint tracking works fully in Cursor. The Oracle reads `sprint-status.yaml` and all story status transitions follow the same lifecycle rules.

### Direct Status Check

```
Read @_bmad-output/implementation-artifacts/sprint-status.yaml and summarize the current sprint state.
```

Or use the sprint digest for a quick overview:

```
Read @_bmad-output/context/sprint-digest.md for the current sprint summary.
```

---

## Tips for Best Results

1. **The alwaysApply rules are critical.** Without them, Cursor will not activate the Oracle or enforce lifecycle gates. Verify all three .mdc files are in `.cursor/rules/`.

2. **Use @ references liberally.** When the AI needs context from a specific file, reference it directly with `@path/to/file`. This is Cursor's equivalent of Claude Code's file references.

3. **Keep conversations focused.** Cursor's chat context can be shorter than Claude Code's. For complex workflows, break them into separate conversations.

4. **Regenerate context after significant changes.** Without hooks, it is your responsibility to keep context files fresh. Run the generator after major commits.

5. **Reference instruction files directly.** For complex workflows, you can point the AI to specific step files:
   ```
   Execute step 3 from @_bmad/bmm/workflows/4-implementation/code-review/instructions.xml
   ```

6. **Use Composer for multi-file edits.** Cursor's Composer mode is well-suited for BMAD's dev-story workflow, which often touches multiple files across the codebase.

---

## Differences from Claude Code

| Aspect | Claude Code | Cursor |
|--------|------------|--------|
| Oracle activation | CLAUDE.md (automatic) | .mdc rule with alwaysApply (automatic) |
| Agent invocation | `/bmad:bmm:agents:oracle` | `Load @_bmad/bmm/agents/oracle.md` |
| Workflow execution | Slash command | `Execute @path/to/workflow.yaml using @workflow.xml` |
| Context regeneration | Automatic (post-commit hook) | Manual (`python scripts/context/generate_all.py`) |
| Agent teams | Experimental (env var) | Not available |
| File references | @ in commands | @ in chat |
| Settings/permissions | settings.local.json | Cursor settings |
| MCP tools | Full support | Varies by version |

Despite these differences, the core BMAD methodology works the same. The Oracle orchestrates, workflows execute in order, lifecycle gates are enforced, and sprint-status.yaml is the single source of truth.
