# Feature Orchestrator Skill

---
skill_name: feature-orchestrator
description: Decompose complex requests into features and orchestrate isolated planning agents
category: orchestration
bmad_module: core
---

## WHEN TO USE

Invoke this skill when:
- User request involves 3+ distinct features
- Request spans multiple domains (frontend, backend, testing, etc.)
- Estimated scope exceeds 5 days of work
- User explicitly asks to "break down into features" or "orchestrate planning"
- Previous planning attempts hit context limits

## SKILL BEHAVIOR

This skill loads and executes the feature-orchestrator workflow:

**Workflow Path**: `_bmad/core/workflows/feature-orchestrator/workflow.md`

**Execution Steps**:
1. **Decomposition**: Analyze request, identify features, present for approval
2. **Feature Spawning**: Spawn subprocess agent per feature for isolated planning
3. **Consolidation**: Aggregate feature plans into consolidated implementation plan
4. **Next Actions**: Recommend implementation workflow (dev-story or agent-teams)

## INVOCATION

**Direct invocation**:
```
/feature-orchestrator
```

**Or implicit invocation** (Claude detects complex request):
```
User: "I need to add JWT authentication, create a user dashboard, and write comprehensive tests"
```

**Or with explicit workflow load**:
```
User: "Can you use the feature orchestrator to plan this: [complex request]"
```

## EXAMPLE SESSION

**Input**:
```
User: "Build a complete authentication system with OAuth, JWT, 2FA, and admin dashboard"
```

**What Happens**:
1. Orchestrator analyzes request
2. Detects 4 features: OAuth Integration, JWT Service, 2FA System, Admin Dashboard
3. Presents decomposition for your approval
4. Spawns 4 agents sequentially to plan each feature
5. Aggregates plans into consolidated-plan.md
6. Recommends implementation approach

**Output**:
- `_bmad-output/.orchestrator/session-{timestamp}/consolidated-plan.md`
- Individual feature plans in same directory
- Ready to implement via dev-story or agent-teams

## WORKFLOW REFERENCE

Full workflow: `_bmad/core/workflows/feature-orchestrator/workflow.md`
Documentation: `_bmad/core/workflows/feature-orchestrator/README.md`

## WORKFLOW EXECUTION

When this skill is invoked, Claude will:
1. Load the workflow.md file
2. Execute the 4-step orchestration process
3. Create session artifacts in `_bmad-output/.orchestrator/`
4. Return consolidated plan and recommend next steps