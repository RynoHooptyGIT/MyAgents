# Step 4: Next Actions & Handoff

---
step_name: "next-actions"
step_number: 4
subprocess_optimization: false  # Orchestrator recommends and coordinates handoff
---

## YOUR TASK

Recommend the appropriate next workflow for implementation, offer to spawn implementation agents, and archive the orchestration session.

## ROLE

You are the **Feature Orchestrator** in **handoff mode**. Your responsibilities:
- Recommend next workflow based on features and context
- Offer to spawn implementation workflow
- Archive session state
- Provide clear next steps to user

---

## EXECUTION SEQUENCE

### 1. Analyze Consolidated Plan

```yaml
READ: consolidated-plan.md

EXTRACT:
  - Total features
  - Total effort (days)
  - Feature complexity distribution
  - Dependencies between features
  - File conflicts (if any)

ASSESS:
  - Can features be implemented in parallel? (check dependencies)
  - Are features balanced in size?
  - How many developers would be optimal?
  - Is there a natural sequence?
```

---

### 2. Recommend Implementation Approach

```yaml
RECOMMENDATION LOGIC:

IF total_features == 1:
  RECOMMEND: quick-dev or dev-story
  REASON: Single feature doesn't need orchestration

ELSE IF features_are_independent AND team_available:
  RECOMMEND: agent-teams (parallel implementation)
  REASON: Features can be built concurrently
  BENEFIT: Faster completion

ELSE IF features_have_dependencies OR solo_developer:
  RECOMMEND: dev-story (sequential implementation)
  REASON: Dependencies require sequence, or solo dev
  BENEFIT: Clear focus, incremental validation

ELSE IF features_are_large (>7 days each):
  RECOMMEND: Create epics, nested orchestration
  REASON: Features are epic-sized themselves
  BENEFIT: Further decomposition before implementation
```

---

### 3. Present Options to User

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Planning Complete - Ready to Implement
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Your consolidated plan is ready:
📄 {consolidated_plan_path}

Features: {count}
Total Effort: {days} days
Implementation Phases: {phase_count}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Recommended Approach: {recommendation}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{IF recommendation == "agent-teams"}
Agent Teams (Parallel Implementation)

Team Structure:
- Dev Lead: Coordinate implementation
- Dev 1: Feature {name} ({days} days)
- Dev 2: Feature {name} ({days} days)
- Tea: Write tests for all features
- Tech-Writer: Document features

Timeline: ~{parallel_days} days (vs {sequential_days} days sequential)

Advantages:
  ✓ Faster completion (parallel work)
  ✓ Specialization by feature
  ✓ Clear ownership

{ELSE IF recommendation == "dev-story"}
Dev-Story (Sequential Implementation)

Sequence:
1. Feature {name} ({days} days)
2. Feature {name} ({days} days) - after Feature 1
3. Feature {name} ({days} days) - after Feature 2
...

Timeline: ~{sequential_days} days

Advantages:
  ✓ Clear focus per feature
  ✓ Incremental validation
  ✓ Lower cognitive load
  ✓ Works for solo developer

{END IF}

What would you like to do?

[I] Implement Now - Start with recommended approach
[C] Choose Different Approach - See all options
[R] Review Plan First - Open consolidated plan
[E] Export and Exit - Save artifacts and exit
[M] Manual Implementation - I'll implement myself
```

---

### 4. Handle User Choice

#### Choice I: Implement Now

```yaml
IF recommendation == "agent-teams":
  ACTIONS:
    1. Display: "Spawning Agent Team..."

    2. Prepare team configuration:
       - Team size based on feature count
       - Assign features to team members
       - Define shared task list

    3. Spawn agent-teams workflow:
       INPUT: consolidated-plan.md
       FEATURES: All features with plans
       TEAM: Dev + Tea + Tech-Writer

    4. Monitor team execution (orchestrator hands off control)

    5. When team completes:
       - Archive orchestration session
       - Display completion summary

ELSE IF recommendation == "dev-story":
  ACTIONS:
    1. Display: "Starting sequential implementation..."

    2. FOR EACH feature in implementation sequence:
       a. Display: "Implementing Feature {name}..."

       b. Spawn dev-story workflow:
          INPUT: feature-{id}-handoff.yaml
          STORY: Create from feature plan

       c. dev-story implements feature

       d. When feature complete:
          - Update manifest: feature status = "implemented"
          - Progress: {completed}/{total} features

    3. When all features complete:
       - Archive orchestration session
       - Display completion summary
```

#### Choice C: Choose Different Approach

```yaml
DISPLAY ALL OPTIONS:

1. Sequential Implementation (dev-story)
   - One feature at a time
   - Timeline: {sequential_days} days
   - Best for: Solo dev, dependencies, learning

2. Parallel Implementation (agent-teams)
   - Multiple features concurrently
   - Timeline: {parallel_days} days
   - Best for: Team, independent features, speed

3. Manual Implementation
   - You implement using the plan
   - Orchestrator provides plan only
   - Best for: Learning, control, custom workflow

4. Create Epics (Nested Orchestration)
   - Break large features into sub-features
   - Timeline: Planning + implementation
   - Best for: Very large features (>7 days each)

5. Export Plan
   - Save plan, implement later
   - Timeline: Your choice
   - Best for: Review before starting

PROMPT: "Which approach would you like?"
[1-5 or cancel]

PROCESS: Based on user selection, proceed accordingly
```

#### Choice R: Review Plan First

```yaml
ACTIONS:
1. Display plan summary:
   - Features
   - Sequence
   - Effort
   - Key risks

2. Offer to open full plan:
   "Open consolidated-plan.md in editor? [Y/N]"

   IF yes:
     Open file in default markdown viewer/editor

3. Return to options menu
```

#### Choice E: Export and Exit

```yaml
ACTIONS:
1. Archive session (see Section 5)

2. Display export summary:
   Artifacts exported to: {session_dir}/

   Files:
   - consolidated-plan.md (implementation plan)
   - manifest.yaml (feature breakdown)
   - feature-*-handoff.yaml (detailed plans)
   - orchestrator-state.yaml (session state)

3. Provide next steps:
   To implement later:
   - Review: {consolidated_plan_path}
   - Use: dev-story or agent-teams workflow
   - Resume: Feature orchestrator can resume this session

4. Exit orchestrator workflow
```

#### Choice M: Manual Implementation

```yaml
ACTIONS:
1. Display guidance:
   Your consolidated plan provides:
   - Feature-by-feature breakdown
   - Files to modify/create
   - Implementation approach
   - Dependencies and risks

   Recommended implementation order:
   {FOR EACH phase}
     Phase {n}: {feature_names}
   {END FOR}

2. Provide artifacts:
   Plan: {consolidated_plan_path}
   Detailed plans: {session_dir}/feature-*-handoff.yaml

3. Archive session

4. Exit orchestrator
```

---

### 5. Archive Session

```yaml
ARCHIVE_ACTIONS:

1. Create archive directory:
   mkdir output/.orchestrator/archived/session-{timestamp}/

2. Copy session files:
   cp session-{timestamp}/* archived/session-{timestamp}/

   Files archived:
   - manifest.yaml
   - orchestrator-state.yaml
   - consolidated-plan.md
   - feature-*-handoff.yaml

3. Create session summary:
   FILE: archived/session-{timestamp}/session-summary.md

   CONTENT:
     # Orchestration Session Summary

     **Session ID**: {session_id}
     **Date**: {date}
     **Duration**: {minutes} minutes

     ## Original Request
     {user_request}

     ## Features Decomposed
     {count} features identified:
     {FOR EACH feature}
       - {feature_name} ({effort_days} days)
     {END FOR}

     ## Outcomes
     - Features planned: {completed}/{total}
     - Total effort: {days} days
     - Files: {count} to modify/create
     - Token usage: {total_tokens}

     ## Artifacts
     - Consolidated Plan: consolidated-plan.md
     - Feature Plans: feature-*-handoff.yaml
     - Manifest: manifest.yaml
     - State: orchestrator-state.yaml

     ## Next Steps
     {recommended_approach}

4. Update orchestrator-state.yaml:
   current_phase: "complete"
   archived_at: "{timestamp}"
   archived_to: "{archive_path}"

5. Optional: Compress archive
   tar -czf archived/session-{timestamp}.tar.gz archived/session-{timestamp}/

6. Clean active session (optional, configurable):
   # Keep last 3 active sessions
   # Delete older active sessions
```

---

### 6. Completion Message

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ Feature Orchestration Complete
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Session: {session_id}
Duration: {minutes} minutes
Features Planned: {count}

Deliverables:
📄 {consolidated_plan_path}
📁 {session_archive_path}

{IF implementing_now}
🚀 Starting implementation with {workflow_name}...
{ELSE}
Next: Review plan and choose implementation approach
{END IF}

Thank you for using Feature Orchestrator!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## SUCCESS CRITERIA

- [ ] Consolidated plan analyzed
- [ ] Recommendation determined based on features
- [ ] Options presented to user clearly
- [ ] User choice processed
- [ ] Session archived (if exiting)
- [ ] Implementation workflow spawned (if implementing)
- [ ] User has clear next steps
- [ ] Orchestration workflow complete

---

## WORKFLOW COMPLETION

```
✓ Step 4: Next Actions - COMPLETE
✓ Feature Orchestrator Workflow - COMPLETE

Session archived: {archive_path}
Plan delivered: {plan_path}

{IF implementing}
Handoff to: {next_workflow_name}
{ELSE}
Orchestration complete. Ready for implementation when you are.
{END IF}
```
