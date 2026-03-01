# BMAD v6 -- GitHub Copilot Setup Guide

GitHub Copilot provides partial BMAD support. It can use all BMAD agent personas, workflows, and context files, but lacks slash commands, hooks, and agent teams. This guide covers how to adapt BMAD for the best Copilot experience.

## Overview

| Feature | Status |
|---------|--------|
| Oracle auto-activation | Partial (via copilot-instructions.md) |
| Slash commands | Not available |
| Post-commit hooks | Not available |
| Agent teams | Not available |
| Context file usage | Full |
| Workflow engine | Fair (complex workflows need guidance) |
| Agent personas | Good |
| Sprint tracking | Full |
| File references | @workspace |
| MCP tools | Not available |

---

## Step 1: Create copilot-instructions.md

Create `.github/copilot-instructions.md` in your project root. Copilot reads this file at the start of every chat session.

```markdown
# Project AI Instructions

## MANDATORY: Oracle Agent -- Always Active

This project uses the BMAD Methodology (v6) with an Oracle agent (Athena) as the
always-on orchestrator. The Oracle MUST be activated at the start of EVERY session.

### Session Start Protocol

1. Load and follow the full activation protocol in `team/agents/oracle.md`
2. Read project config from `team/config.yaml`
3. Read sprint state from `output/implementation-artifacts/sprint-status.yaml`
4. Read context files from `output/context/` (module-index.md, sprint-digest.md, etc.)
5. Present a project brief with current epic, in-flight stories, and recommendation
6. Display the Oracle's numbered menu and wait for user input

### Implementation Lifecycle (Mandatory -- No Shortcuts)

1. **Create Story (CS)** -- Story file must exist before development
2. **Dev Story (DS)** -- Implement the story (tasks, code, tests)
3. **Code Review (CR)** -- Adversarial review (3-10 findings, fix them)
4. **Ship (SH)** -- Commit, push, create PR

Never skip steps. Never start coding without a story file. Always run code review
before shipping.

### Agent Context System

Pre-generated context files in `output/context/`:
- `module-index.md` -- Feature map of frontend modules + backend services
- `sprint-digest.md` -- Sprint summary (use instead of parsing full YAML)
- `api-index.md` -- All API endpoints by router
- `schema-digest.md` -- Database schema from models
- `patterns.md` -- Canonical code patterns to follow

Also load `output/project-context.md` if it exists -- critical rules for implementation.

### Context Regeneration

After every git commit, manually run:
```
python scripts/context/generate_all.py
```

## Critical Technical Rules

<!-- Add your project-specific rules here -->
```

---

## Step 2: Invoking the Oracle

Since Copilot has no slash commands, invoke the Oracle by asking:

```
Please load the agent file at team/agents/oracle.md and follow its complete
activation protocol. Read team/config.yaml for project settings, then read
output/implementation-artifacts/sprint-status.yaml for sprint state.
Present the project brief and menu.
```

The Oracle will:
1. Adopt the Athena persona
2. Load your project configuration
3. Parse sprint status
4. Present a brief and menu
5. Wait for your selection

### Oracle Menu Commands

Once the Oracle is active, you can use these commands:

| Command | What It Does |
|---------|-------------|
| CS | Create a story file from an epic |
| DS | Implement a story (dev-story workflow) |
| CR | Run adversarial code review |
| SH | Ship (commit, push, PR) |
| SP | Sprint planning |
| SS | Sprint status summary |
| PB | Project brief |
| NA | Determine and execute next action |
| RA | Route to a specialist agent |
| CH | Chat with Athena about anything |

---

## Step 3: Invoking Other Agents

To invoke any agent, ask Copilot to load its file:

```
Please load the agent from team/agents/architect.md and follow its activation protocol.
```

```
Please load the agent from team/agents/security-auditor.md and follow its activation protocol.
```

```
Please load the agent from team/agents/creative-thinking-coach.md and follow its activation protocol.
```

### Agent File Locations

| Agent | File Path |
|-------|-----------|
| Oracle (Athena) | `team/agents/oracle.md` |
| Architect (Winston) | `team/agents/architect.md` |
| Developer (Amelia) | `team/agents/dev.md` |
| Test Architect (Murat) | `team/agents/tea.md` |
| Security Auditor (Shield) | `team/agents/security-auditor.md` |
| DevOps (Forge) | `team/agents/devops.md` |
| Custodian (Sentinel) | `team/agents/custodian.md` |
| UX Designer (Sally) | `team/agents/ux-designer.md` |
| Product Manager (John) | `team/agents/pm.md` |
| Analyst (Mary) | `team/agents/analyst.md` |
| Data Architect (Oracle) | `team/agents/data-architect.md` |
| API Contract (Pact) | `team/agents/api-contract.md` |
| Quick Flow (Barry) | `team/agents/quick-flow-solo-dev.md` |
| Creative Thinking (Carson) | `team/agents/creative-thinking-coach.md` |
| Design & Strategy (Maya) | `team/agents/design-strategy-coach.md` |
| Storyteller & Presenter (Sophia) | `team/agents/storyteller-presenter.md` |
| Agent Builder (Bond) | `team/agents/agent-builder.md` |

---

## Step 4: Executing Workflows

For workflows, ask Copilot to load both the workflow engine and the specific workflow:

```
Please execute the workflow at team/workflows/implementation/code-review/workflow.yaml
using the workflow engine defined in team/engine/workflow.xml.
Follow all steps exactly as specified.
```

### Common Workflow Paths

| Workflow | Path |
|----------|------|
| Create Story | `team/workflows/implementation/create-story/workflow.yaml` |
| Dev Story | `team/workflows/implementation/dev-story/workflow.yaml` |
| Code Review | `team/workflows/implementation/code-review/workflow.yaml` |
| Ship | `team/workflows/devops/ship/workflow.yaml` |
| Sprint Planning | `team/workflows/implementation/sprint-planning/workflow.yaml` |
| PRD | `team/workflows/planning/prd/workflow.md` |
| Architecture | `team/workflows/solutioning/create-architecture/workflow.md` |

### Limitations

Complex multi-step workflows with many file reads, template outputs, and variable resolution may require more manual guidance with Copilot than with Claude Code. If the AI loses track of workflow state:

1. Remind it which step it was on
2. Point it to the specific instruction file for that step
3. Provide the relevant context files it needs

---

## Step 5: Context File Management

### Using Context Files

Context files in `output/context/` work the same across all tools. Reference them in your prompts:

```
Read output/context/module-index.md for the project's feature map.
```

```
Check output/context/sprint-digest.md for current sprint status.
```

Use `@workspace` to reference project files when needed.

### Manual Regeneration

Since Copilot has no hooks, regenerate context manually after commits:

```bash
# Full regeneration
python scripts/context/generate_all.py

# Sprint-only regeneration (faster)
python scripts/context/generate_all.py --sprint

# Check if files are stale
python scripts/context/generate_all.py --check
```

Consider adding a git alias for convenience:
```bash
git config alias.ctx '!python scripts/context/generate_all.py'
```

Then after committing:
```bash
git commit -m "feat: implement feature X"
git ctx
```

---

## Step 6: Sprint Tracking

Sprint tracking via `sprint-status.yaml` works fully with Copilot. The Oracle reads and updates it, and all story status transitions follow the same rules.

### Manual Status Checks

If you need to check sprint state without the Oracle:

```
Read output/implementation-artifacts/sprint-status.yaml and summarize:
- Count stories by status (backlog, ready-for-dev, in-progress, review, done)
- Identify the current active epic
- Recommend the next action
```

---

## Tips for Best Results

1. **Always start with the Oracle.** Even without auto-activation, explicitly loading oracle.md sets the right context for the entire session.

2. **Reference files explicitly.** Copilot works best when you point it to specific files rather than expecting it to find them.

3. **Use @workspace for broad context.** When the AI needs to understand the project structure, use @workspace to give it access.

4. **Break complex workflows into steps.** Instead of asking Copilot to run an entire multi-step workflow, guide it through one step at a time.

5. **Regenerate context regularly.** Without hooks, context files can become stale. Run the generator after significant code changes.

6. **Paste relevant context.** If Copilot is not following project patterns, paste the relevant section of project-context.md into the chat.

7. **Remind about lifecycle gates.** Copilot may not enforce lifecycle gates as strictly as Claude Code. Remind it: "Before coding, verify a story file exists."

---

## What Works Without Any Setup

Even without the copilot-instructions.md file, you can use BMAD by manually loading agent files and workflow configurations. The methodology is encoded in the files themselves -- any AI that can read markdown and follow instructions can use it.

The setup described above simply automates what you would otherwise do manually: load the Oracle, read config, read sprint status, and follow the lifecycle.
