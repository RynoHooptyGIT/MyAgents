# My Dev Team — Tool Compatibility

My Dev Team is designed to work with multiple AI coding tools. This document provides a detailed feature matrix and explains how each tool integrates.

## Feature Matrix

| Feature | Claude Code | Cursor | GitHub Copilot |
|---------|:-----------:|:------:|:--------------:|
| Oracle auto-activation | Full (CLAUDE.md) | Full (.mdc rules) | Partial (copilot-instructions.md) |
| Slash commands (81) | Full (.claude/commands/) | None | None |
| Post-commit hooks | Full (PostToolUse) | None | None |
| Agent teams | Experimental | None | None |
| Context file usage | Full | Full | Full |
| Workflow engine | Full | Good | Fair |
| Agent personas | Full | Good | Good |
| Sprint tracking | Full | Full | Full |
| File references | @ prefix in commands | @ in chat | @workspace |
| MCP tools | Native | Some | None |
| Settings/permissions | Full (.claude/settings.local.json) | Partial (.cursor/settings.json) | None |
| YOLO mode | Full | Full | Full |
| Party mode | Full | Good | Fair |
| Multi-file editing | Full | Full | Good |
| Template output saving | Full | Good | Fair |

### What the Ratings Mean

- **Full**: Feature works natively with built-in integration
- **Good**: Feature works well but requires manual setup or has minor limitations
- **Fair**: Feature works but with significant limitations or workarounds
- **Partial**: Feature partially works; some capabilities missing
- **None**: Feature not available for this tool

---

## Claude Code (Full Support)

Claude Code has the deepest integration with native support for every feature.

### Oracle Auto-Activation

`CLAUDE.md` is automatically loaded at the start of every Claude Code session. It contains the Oracle activation protocol, which instructs Claude to invoke the Oracle agent before any other work. This is seamless -- the user does not need to do anything.

### Slash Commands (81 Total)

76 slash commands are installed in the `claude-commands/` directory (which maps to `.claude/commands/` in the project). These provide direct access to every agent and workflow:

```
/team:oracle          # Invoke the Oracle
/team:dev-story    # Run dev-story workflow
/team:code-review  # Run code review
/team:ship         # Ship (commit, push, PR)
/team:creative-thinking-coach  # Invoke creative thinking
/team:agent-builder   # Build a custom agent
```

Commands are organized by module: `bmm/agents/`, `bmm/workflows/`, `bmb/agents/`, `bmb/workflows/`, `cis/agents/`, `cis/workflows/`, `core/agents/`, `core/workflows/`, `core/tasks/`.

### Post-Commit Hooks

A PostToolUse hook is registered in `.claude/settings.local.json` that fires after every Bash tool call. When it detects a successful `git commit`, it runs `scripts/context/generate_all.py` to regenerate all 5 context files. The result is injected into the conversation as `additionalContext`, so Claude immediately knows the context files are fresh.

Hook registration:
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

### Agent Teams

Enable with the environment variable:
```json
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  }
}
```

Agent teams allow multiple agents to work in parallel on different aspects of a task. Teams are defined in `team/manifest.yaml`. Workflows can invoke teams via `invoke-team` tags. Party mode enables group discussions between agents.

### Settings and Permissions

`.claude/settings.local.json` configures:
- **Environment variables**: `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS`
- **Permissions**: `Bash(*)`, `Read(//**)` for full file and shell access
- **Hooks**: PostToolUse for context regeneration

### MCP Tools

Claude Code supports MCP (Model Context Protocol) tools natively. Workflows can leverage:
- **Playwright** for browser testing and visual verification
- **Context7** for up-to-date library documentation
- Any custom MCP servers defined in the project

See the [Claude Code IDE Guide](../ide-guides/claude-code.md) for full setup details.

---

## Cursor (Good Support)

Cursor provides good support through its `.cursor/rules/` system with `.mdc` files.

### Oracle Auto-Activation

Create `.cursor/rules/000-bmad-oracle.mdc` with `alwaysApply: true`:

```markdown
---
alwaysApply: true
---

# Oracle Activation Protocol

At the start of every conversation, load and follow the activation protocol in `team/agents/oracle.md`.
Load `team/config.yaml` for project settings.
Read `output/implementation-artifacts/sprint-status.yaml` for sprint state.
Read context files from `output/context/` for codebase knowledge.
```

This ensures the Oracle activates in every Cursor chat session.

### No Slash Commands

Cursor does not support custom slash commands. Instead, invoke agents and workflows by asking the AI:

```
Load the agent from @team/agents/architect.md and follow its activation protocol.
```

```
Execute the workflow at @team/workflows/implementation/code-review/workflow.yaml
using the workflow engine at @team/engine/workflow.xml.
```

The `@` prefix references files in Cursor's chat interface.

### No Post-Commit Hooks

Cursor does not support hooks. Run context regeneration manually after commits:

```bash
python scripts/context/generate_all.py
```

### Additional .mdc Rules

Create these additional rule files for lifecycle enforcement:

- `.cursor/rules/001-bmad-lifecycle.mdc` -- Implementation lifecycle rules
- `.cursor/rules/002-bmad-context.mdc` -- Context system configuration

See the [Cursor IDE Guide](../ide-guides/cursor.md) for full setup details.

---

## GitHub Copilot (Partial Support)

GitHub Copilot provides basic support through its instructions file.

### Oracle Auto-Activation

Create `.github/copilot-instructions.md` with the Oracle activation protocol. Copilot reads this file at session start, but enforcement is less reliable than Claude Code or Cursor -- Copilot may not always follow the full activation protocol without prompting.

### No Slash Commands

Copilot does not support custom slash commands. Invoke agents manually:

```
Please load the agent file at team/agents/oracle.md and follow its complete activation protocol.
Read team/config.yaml for project settings.
Then read output/implementation-artifacts/sprint-status.yaml for sprint state.
```

### No Post-Commit Hooks

Copilot does not support hooks. Run context regeneration manually:

```bash
python scripts/context/generate_all.py
```

### No Agent Teams

Agent teams are not available in Copilot. All work is single-agent.

### File References

Use `@workspace` to reference project files in Copilot chat. This provides access to the project structure but is less precise than Claude Code's `@` file references.

### Workflow Engine Limitations

Copilot can execute workflows, but complex multi-step workflows with many file reads, template outputs, and variable resolution may require more manual guidance. The AI may not follow all workflow.xml instructions as precisely as Claude Code.

See the [Copilot IDE Guide](../ide-guides/copilot.md) for full setup details.

---

## Generic AI Tools

For AI coding tools not listed above (Windsurf, Aider, Continue, etc.), the system can still be used with manual setup:

### Project Instructions File

Most AI coding tools support a project instructions file. Create one with:
1. Oracle activation protocol (load oracle.md, read config, read sprint status)
2. Lifecycle rules (create-story, dev-story, code-review, ship)
3. References to context files in `output/context/`
4. Project-specific technical rules

### Manual Agent Invocation

Ask the AI to:
1. Read the agent file (e.g., `team/agents/oracle.md`)
2. Follow its activation steps
3. Present its menu
4. Execute selected workflows

### Manual Context Management

Run context generation scripts manually:
```bash
python scripts/context/generate_all.py        # Full regeneration
python scripts/context/generate_all.py --sprint  # Sprint only
python scripts/context/generate_all.py --check   # Freshness check
```

### What Always Works

Regardless of tool, these features work everywhere:
- Agent persona files (readable by any AI)
- Workflow YAML configurations (parseable by any AI)
- Sprint-status.yaml tracking
- Context files in `output/context/`
- Template files and output artifacts
- The workflow execution logic in `workflow.xml`

The differences are primarily in automation (hooks, commands) and enforcement (auto-activation, gates). The methodology itself is tool-agnostic.
