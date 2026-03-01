# BMAD Agent Teams User Guide

## Overview

Agent teams allow multiple BMAD agents to work together in parallel as a coordinated team. Unlike subagents (which work sequentially and report back to the main agent), agent teams enable:

- **Parallel work**: Multiple agents working simultaneously on different aspects
- **Direct communication**: Teammates message each other directly without going through the lead
- **Shared task list**: Coordinated work tracking across all team members
- **Independent context**: Each teammate has their own context window

## When to Use Agent Teams

### Good Use Cases ✅

| Scenario | Why Agent Teams Excel |
|----------|----------------------|
| **Planning sessions** | Fullstack team explores requirements, architecture, UX, and project management in parallel |
| **Research from multiple perspectives** | Creative squad investigates innovation, storytelling, design thinking simultaneously |
| **Code review with different lenses** | Implementation team reviews security, performance, and test coverage independently |
| **Debugging with competing hypotheses** | Agents test different theories in parallel and converge on the answer faster |
| **Cross-layer coordination** | Frontend, backend, and tests each owned by different teammates |

### Bad Use Cases ❌

| Scenario | Why Subagents Are Better |
|----------|--------------------------|
| **Simple single-file changes** | Coordination overhead not worth it |
| **Sequential dependent tasks** | Work must happen in order |
| **Quick bug fixes** | Single agent is faster |
| **Same-file edits** | Risk of conflicts |

## Available Teams

### 1. Fullstack Team (Planning & Design)

**Members:** analyst, architect, pm, ux-designer
**Best for:** Planning, design, requirements, strategic alignment
**Lead Agent:** PM coordinates by default
**Typical Size:** 4 agents

**Example Usage:**
```
Create a fullstack team to design the new authentication system
```

**Expected Workflow:**
- PM coordinates overall effort
- Analyst gathers and documents requirements
- Architect designs system with security focus
- UX Designer reviews user impact
- Oracle orchestrates implementation workflow

### 2. Creative Squad (Innovation)

**Members:** creative-thinking-coach, design-strategy-coach, storyteller-presenter
**Best for:** Innovation, problem solving, creative exploration
**Lead Agent:** Design-strategy coach coordinates
**Typical Size:** 3 agents (all CIS agents)

**Example Usage:**
```
Spawn creative squad to brainstorm solutions for user retention
```

**Expected Workflow:**
- Design-strategy coach leads exploration and ensures user-centricity
- Creative-thinking coach facilitates ideation and analyzes constraints
- Storyteller-presenter crafts narratives and visualizes concepts

### 3. Implementation Team (Parallel Development)

**Members:** dev, tea (Test Architect), tech-writer
**Best for:** Parallel implementation, test coverage, documentation
**Lead Agent:** Dev or TEA coordinates
**Typical Size:** 3 agents

**Example Usage:**
```
Create implementation team to build features in parallel
```

**Expected Workflow:**
- Dev implements core functionality
- TEA creates comprehensive test coverage
- Tech Writer documents APIs and usage

## How to Use Agent Teams

### Starting a Team

**Basic Syntax:**
```
Create a [team-name] team to [task description]
```

**Examples:**
```
Create a fullstack team to plan the new payment processing feature

Spawn creative squad to innovate solutions for reducing churn

Create implementation team with dev, tea, and tech-writer to build the API
```

### Specifying Teammates and Models

You can customize team composition and models:

```
Create a team with 4 teammates to refactor these modules in parallel.
Use Sonnet for each teammate.

Spawn an architect teammate to refactor the authentication module.
Use Haiku for faster iteration.
```

### Requiring Plan Approval

For complex or risky tasks, require teammates to plan before implementing:

```
Spawn architect teammate to refactor auth module. Require plan approval.
```

When a teammate finishes planning:
1. Sends plan approval request to lead
2. Lead reviews and either approves or rejects with feedback
3. If rejected, teammate revises and resubmits
4. Once approved, teammate exits plan mode and begins implementation

### Messaging Teammates

**Direct message to specific teammate:**
```
Ask the analyst teammate to review the proposed architecture
```

**Broadcast to all teammates:**
```
Tell all teammates to provide status updates
```

### Using Delegate Mode

Delegate mode restricts the lead to coordination-only tools:
- Spawning teammates
- Messaging teammates
- Shutting down teammates
- Managing tasks

**Enable delegate mode:**
Press Shift+Tab after starting a team to cycle into delegate mode

**Why use it:** Prevents the lead from starting implementation itself instead of waiting for teammates

### Shutting Down

**Graceful shutdown:**
```
Ask the researcher teammate to shut down
```

**Clean up the team:**
```
Clean up the team
```

⚠️ **Important:** Always shut down all teammates before cleaning up. Always use the lead to clean up (not teammates).

## Display Modes

### In-Process Mode (Default)

- All teammates run inside main terminal
- Use **Shift+Up/Down** to select teammates
- Type to message selected teammate
- Press **Enter** to view teammate's session
- Press **Escape** to interrupt current turn
- Press **Ctrl+T** to toggle task list
- Works in any terminal

### Split Panes Mode

- Each teammate gets own pane
- See all output simultaneously
- Click pane to interact directly
- Requires `tmux` or iTerm2

**Configure in settings.local.json:**
```json
{
  "teammateMode": "in-process"  // or "tmux" or "auto"
}
```

- `"auto"` - Split panes if in tmux, otherwise in-process
- `"in-process"` - Main terminal only
- `"tmux"` - Force split panes

## Best Practices

### 1. Size Tasks Appropriately

- **Too small:** Coordination overhead exceeds benefit
- **Too large:** Teammates work too long without check-ins, increasing risk
- **Just right:** Self-contained units that produce clear deliverables

**Tip:** Have 5-6 tasks per teammate to keep everyone productive

### 2. Give Teammates Enough Context

Teammates don't inherit the lead's conversation history. Include task-specific details in spawn prompts:

```
Spawn a security reviewer teammate with the prompt: "Review the authentication
module at src/auth/ for security vulnerabilities. Focus on token handling,
session management, and input validation. The app uses JWT tokens stored in
httpOnly cookies. Report any issues with severity ratings."
```

### 3. Wait for Teammates to Finish

If the lead starts implementing instead of waiting:
```
Wait for your teammates to complete their tasks before proceeding
```

### 4. Avoid File Conflicts

Break work so each teammate owns different files. Two teammates editing the same file leads to overwrites.

### 5. Monitor and Steer

Check in on progress, redirect approaches that aren't working, synthesize findings as they come in.

### 6. Start with Research and Review

If you're new to agent teams, start with tasks that have clear boundaries and don't require writing code:
- Reviewing a PR
- Researching a library
- Investigating a bug

## Configuration

### Project-Level Configuration

In `team/config.yaml`:

```yaml
teams:
  enabled: true
  default_mode: "auto"  # "auto", "in-process", or "tmux"
  auto_spawn_threshold: 3  # Suggest teams for tasks with 3+ parallel components
  preferred_teams:
    - fullstack
    - implementation
  token_budget_multiplier: 2.5  # Teams use ~2.5x more tokens
```

### Claude Code Settings

In `.claude/settings.local.json`:

```json
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  }
}
```

## Troubleshooting

### Teammates Not Appearing

- In in-process mode, press **Shift+Down** to cycle through active teammates
- Check that task is complex enough to warrant a team
- Verify `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` is set to "1"
- For split panes, ensure tmux is installed: `which tmux`

### Too Many Permission Prompts

Pre-approve common operations in `settings.local.json` before spawning teammates:

```json
{
  "permissions": {
    "allow": [
      "Bash(git:*)",
      "Bash(npm:*)",
      "Bash(pytest:*)"
    ]
  }
}
```

### Teammates Stopping on Errors

- Check teammate output using Shift+Up/Down (in-process) or clicking pane (split mode)
- Give additional instructions directly to the teammate
- Or spawn a replacement teammate to continue the work

### Lead Shuts Down Before Work is Done

Tell the lead explicitly:
```
Keep working and wait for all teammates to finish their tasks
```

### Orphaned tmux Sessions

If a tmux session persists after team ends:

```bash
tmux ls
tmux kill-session -t <session-name>
```

## Token Costs

Agent teams use significantly more tokens than single sessions:
- Each teammate has own context window
- Communication adds overhead
- Token usage scales with number of active teammates

**Rule of thumb:** Agent teams use ~2.5x more tokens than single-agent approach

**Best for:** Tasks where parallelism adds real value (research, review, multi-perspective planning)
**Avoid for:** Routine tasks where single agent is sufficient

## Limitations

Current limitations to be aware of:

- **No session resumption with in-process teammates:** `/resume` and `/rewind` don't restore teammates
- **Task status can lag:** Teammates sometimes fail to mark tasks complete
- **Shutdown can be slow:** Teammates finish current request before shutting down
- **One team per session:** Clean up current team before starting new one
- **No nested teams:** Teammates cannot spawn their own teams
- **Lead is fixed:** Cannot promote a teammate to lead or transfer leadership
- **Permissions set at spawn:** All teammates start with lead's permission mode

## Integration with BMAD Workflows

### Party Mode Enhancement

Party mode now detects agent teams capability and offers to use them for complex discussions:

1. Checks if `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` is enabled
2. Assesses task complexity
3. Offers choice between agent teams (parallel) or standard party mode (sequential)
4. Routes to appropriate orchestration method

### Workflow XML Tags

BMAD workflows can use agent teams programmatically:

```xml
<!-- Spawn Agent Team -->
<invoke-team team-id="fullstack" task="Design authentication refactor">
  <teammates>
    <teammate agent="analyst" prompt="Analyze current auth requirements" />
    <teammate agent="architect" prompt="Design new architecture" />
  </teammates>
  <delegate-mode>true</delegate-mode>
  <require-plan-approval>true</require-plan-approval>
</invoke-team>

<!-- Message Teammate -->
<message-teammate to="analyst">
  Please review the proposed architecture and identify gaps
</message-teammate>

<!-- Broadcast to Team -->
<broadcast-team>
  All teammates: provide status updates
</broadcast-team>
```

## Examples

### Example 1: Planning a New Feature

**Scenario:** Design a new AI review feature

```
Create a fullstack team to plan a new AI review feature for healthcare vendors

Expected team: analyst, architect, pm, ux-designer

Workflow:
1. PM coordinates overall planning
2. Analyst researches healthcare compliance requirements
3. Architect designs scalable AI integration
4. UX Designer ensures HIPAA-compliant user flows
5. PM routes to Oracle for story creation

Result: Comprehensive plan with requirements, architecture, UX flows, and stories
```

### Example 2: Parallel Code Review

**Scenario:** Review PR #142 with different lenses

```
Create an agent team to review PR #142. Spawn three reviewers:
- One focused on security implications
- One checking performance impact
- One validating test coverage

Expected workflow:
1. Each reviewer examines PR independently
2. Security reviewer identifies auth vulnerabilities
3. Performance reviewer finds N+1 query issues
4. Test reviewer notes missing edge case coverage
5. Lead synthesizes findings into comprehensive review

Result: Multi-dimensional review catching issues single reviewer might miss
```

### Example 3: Innovation Workshop

```
Spawn creative squad to brainstorm innovative features for user retention

Expected team: All 3 CIS agents

Workflow:
1. Design-strategy coach frames the challenge and ensures user-centricity
2. Creative-thinking coach facilitates wild idea generation and analyzes constraints
3. Storyteller-presenter crafts compelling narratives and visualizes top concepts

Result: Diverse, creative solutions with user validation plans
```

## Next Steps

1. **Enable agent teams** in Claude Code settings
2. **Experiment** with simple research tasks first
3. **Measure** token usage vs single-agent approach
4. **Iterate** on team compositions based on experience
5. **Expand** with custom teams for specific project needs

---

**Need Help?**
- View agent teams in action: Try `/party-mode` with complex topic
- Check configuration: Review `team/manifest.yaml` teams section
- Agent assignments: See `team/agent-manifest.csv` team_assignment column

**Remember:** Agent teams excel at parallel exploration but add coordination overhead. Use them when the benefit of multiple perspectives working simultaneously outweighs the cost.
