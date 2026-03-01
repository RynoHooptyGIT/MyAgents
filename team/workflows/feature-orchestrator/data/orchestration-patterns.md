# Orchestration Patterns & State Management

This document defines the state management schemas, resumption protocols, and orchestration patterns for the feature orchestrator workflow.

## Core Orchestration Pattern

**Pattern Type**: Sequential Subprocess Coordination

**Architecture**:
```
Orchestrator (Lightweight Coordinator)
    ↓
[Analyze] → [Decompose] → [Spawn] → [Aggregate] → [Next]
                              ↓
                    Feature Agent (Subprocess)
                              ↓
                    [Explore] → [Plan] → [Return]
                              ↓
                    Handoff YAML File
```

**Key Principles**:
1. **Orchestrator stays lightweight** - Only coordination logic, no implementation
2. **Feature agents isolated** - Each subprocess gets clean context
3. **Structured handoffs** - Agents return plans via YAML, not full content
4. **Sequential spawning** - One feature at a time to maintain orchestrator focus
5. **State persistence** - Session resumable after each feature completes

---

## State File Schemas

### 1. Feature Manifest (`manifest.yaml`)

**Purpose**: Master list of all features with status tracking

**Location**: `output/.orchestrator/session-{timestamp}/manifest.yaml`

**Schema**:
```yaml
# Orchestration Session Manifest
# This file tracks all features and their planning status

orchestration_session:
  session_id: "orch-{timestamp}"            # Unique session identifier
  project_name: "Project Name"              # From user context or detected
  user_request: |                           # Original user request (multiline)
    Full user request text preserved here
    for reference throughout orchestration
  started_at: "2026-02-08T14:30:22Z"       # ISO 8601 timestamp
  orchestrator_version: "1.0.0"             # Workflow version for compatibility
  orchestrator_context_file: "orchestrator-state.yaml"

# List of all features identified during decomposition
features:
  # Example Feature 1
  - feature_id: "feature-001"               # Sequential ID: feature-001, feature-002, etc.
    feature_name: "JWT Authentication System"  # Human-readable name
    status: "completed"                      # pending | in_progress | completed | blocked | split
    priority: 1                              # Execution order (1 = highest)
    agent_persona: "architect"               # Suggested agent: analyst | architect | dev | tea | pm
    scope: |                                 # Clear feature scope (multiline)
      Implement JWT-based authentication system
      - Login and logout endpoints
      - Token generation and validation
      - Refresh token rotation
      Must integrate with existing user model
    dependencies: []                         # List of feature IDs this depends on
    spawned_at: "2026-02-08T14:30:25Z"      # When subprocess spawned
    completed_at: "2026-02-08T14:35:18Z"    # When handoff received
    handoff_file: "feature-001-handoff.yaml" # Handoff filename

  # Example Feature 2
  - feature_id: "feature-002"
    feature_name: "User Dashboard Implementation"
    status: "in_progress"
    priority: 2
    agent_persona: "dev"
    scope: |
      Create React dashboard with user statistics and activity feed
      - Display user profile information
      - Show recent activity timeline
      - Real-time updates for new activity
    dependencies:
      - feature_id: "feature-001"
        type: "requires"                    # requires | optional | parallel
        reason: "Dashboard needs auth endpoints for API calls"
    spawned_at: "2026-02-08T14:35:20Z"
    completed_at: null                      # Not yet complete
    handoff_file: "feature-002-handoff.yaml"

  # Example Feature 3 - Blocked
  - feature_id: "feature-003"
    feature_name: "Comprehensive Test Suite"
    status: "pending"
    priority: 3
    agent_persona: "tea"
    scope: |
      Write unit and integration tests for authentication and dashboard
      - Unit tests for auth service
      - Integration tests for API endpoints
      - E2E tests for user flows
      Target: 80% code coverage
    dependencies:
      - feature_id: "feature-001"
        type: "requires"
        reason: "Tests validate auth implementation"
      - feature_id: "feature-002"
        type: "requires"
        reason: "Tests validate dashboard implementation"
    spawned_at: null                        # Not yet spawned
    completed_at: null
    handoff_file: "feature-003-handoff.yaml"

# Example Feature - Split
  - feature_id: "feature-004"
    feature_name: "Original Large Feature"
    status: "split"
    split_into:
      - "feature-005"                       # This feature was split into these
      - "feature-006"
    split_reason: "Agent discovered scope too large during exploration"
    handoff_file: "feature-004-handoff.yaml"  # Contains partial plan before split

# Progress tracking
progress:
  total_features: 4                         # Total feature count (including splits)
  completed_features: 1
  in_progress_features: 1
  pending_features: 1
  blocked_features: 0
  split_features: 1
  progress_percentage: 25                   # completed / (total - split) * 100

# Metadata
metadata:
  orchestrator_version: "1.0.0"
  bmad_version: "6.0.0-alpha.23"            # BMAD system version
  created_at: "2026-02-08T14:30:22Z"
  last_updated: "2026-02-08T14:35:20Z"
```

**Manifest Lifecycle**:
1. Created during Step 1 (Decomposition) after user approval
2. Updated after each feature agent completes (status changes)
3. Updated when features split (new features added)
4. Updated when dependencies discovered (dependency list grows)
5. Read by Step 2 (Feature Spawning) to determine next feature
6. Final manifest archived with session when complete

---

### 2. Orchestrator State (`orchestrator-state.yaml`)

**Purpose**: Tracks orchestrator execution state for resumption

**Location**: `output/.orchestrator/session-{timestamp}/orchestrator-state.yaml`

**Schema**:
```yaml
# Orchestrator State File
# This file enables resumption if orchestration is interrupted

session_id: "orch-{timestamp}"
current_phase: "feature_planning"           # decomposition | feature_planning | consolidation | complete

# Execution log for debugging and resumption
execution_log:
  - timestamp: "2026-02-08T14:30:22Z"
    event: "session_started"
    details: "User request received and parsed"

  - timestamp: "2026-02-08T14:30:25Z"
    event: "decomposition_complete"
    details: "Identified 3 features, user approved"

  - timestamp: "2026-02-08T14:30:25Z"
    event: "feature_spawned"
    feature_id: "feature-001"
    agent_persona: "architect"
    context_packet_size: 2048               # Tokens in context packet

  - timestamp: "2026-02-08T14:35:18Z"
    event: "feature_completed"
    feature_id: "feature-001"
    handoff_received: true
    files_to_modify: 3
    files_to_create: 2
    estimated_effort_days: 3

  - timestamp: "2026-02-08T14:35:20Z"
    event: "feature_spawned"
    feature_id: "feature-002"
    agent_persona: "dev"
    context_packet_size: 2560

# Orchestrator context (lightweight - metadata only)
orchestrator_context:
  project_context_path: "/path/to/project-context.md"
  output_folder: "/path/to/output"
  session_directory: "/path/to/output/.orchestrator/session-{timestamp}"
  current_feature_id: "feature-002"         # Feature currently being processed
  next_feature_id: "feature-003"            # Next feature to spawn

# Conversation state
conversation_state:
  awaiting_user_input: false
  last_user_message: "Proceed with next feature"
  orchestrator_message_count: 5
  user_clarifications_requested: 1

# Token usage tracking
token_usage:
  orchestrator_total: 2500                  # Orchestrator's token usage
  feature_agents_total: 12000               # Sum of all feature agents
  budget_per_feature: 8000                  # Allocated per feature
  budget_remaining: 36000                   # Remaining in session
  features_processable: 4                   # Remaining budget / per_feature budget

# Resumption data
resumption:
  can_resume: true
  resume_from_feature: "feature-002"        # Resume with this feature
  resume_action: "check_handoff"            # check_handoff | respawn | continue
  resume_instructions: |
    Load manifest.yaml and check feature-002 status.
    If handoff file exists, process it and continue to feature-003.
    If handoff missing, respawn feature-002 subprocess.

# Error tracking
errors:
  - timestamp: "2026-02-08T14:32:10Z"
    feature_id: "feature-001"
    error_type: "timeout_warning"
    message: "Feature agent approaching 5-minute mark"
    resolved: true
    resolution: "Agent completed before timeout"

# Performance metrics
performance:
  average_feature_duration_seconds: 293     # Average time per feature
  fastest_feature_seconds: 180              # Fastest feature completion
  slowest_feature_seconds: 406              # Slowest feature completion
  total_session_duration_seconds: 600       # Total orchestration time so far
```

**State Lifecycle**:
1. Created at session start with initial state
2. Appended to execution_log after each significant event
3. Updated current_phase as workflow progresses
4. Updated token_usage after each feature
5. Read on resumption to determine restart point
6. Archived with session when complete

---

### 3. Feature Handoff File (`feature-{id}-handoff.yaml`)

**Purpose**: Feature agent returns structured plan to orchestrator

**Location**: `output/.orchestrator/session-{timestamp}/feature-{id}-handoff.yaml`

**Schema**: See [`feature-handoff-template.yaml`](../templates/feature-handoff-template.yaml) for complete schema

**Key Sections**:
- `status`: completed | requires_split | blocked
- `planning_summary`: Approach, files, dependencies, risks
- `estimated_complexity`: Size, effort, token usage
- `requires_split`: Boolean + rationale if needs decomposition
- `blocked_by`: List of blocking issues
- `next_steps`: Recommended actions

---

## Resumption Protocol

### Resumption Triggers

Orchestration session may be interrupted due to:
- User closes session
- Timeout or error
- System restart
- Manual pause

### Resumption Detection

On orchestrator workflow startup:

```yaml
STARTUP_SEQUENCE:

  1. Check for Existing Session:
    SEARCH: output/.orchestrator/session-*/
    FILTER: orchestrator-state.yaml WHERE current_phase != "complete"

  2. IF incomplete session found:
    LOAD: session-{timestamp}/orchestrator-state.yaml
    EXTRACT:
      - session_id
      - current_phase
      - current_feature_id
      - progress (completed/total features)
      - started_at (for time elapsed)

  3. Prompt User:
    "Found incomplete orchestration session from {date/time}:
     Session ID: {session_id}
     Progress: {completed_features}/{total_features} features complete
     Current feature: {feature_name}
     Time elapsed: {duration}

     Would you like to:
     [R] Resume this session
     [N] Start new session (archives old session)
     [V] View session details
     [D] Delete and start fresh"

  4. Handle User Choice:
    - R: Proceed to resumption logic
    - N: Archive old session, start new
    - V: Show manifest + state, then re-prompt
    - D: Delete old session, start new
```

### Resumption Logic

```yaml
RESUMPTION_SEQUENCE:

  1. Load Session State:
    READ: manifest.yaml
    READ: orchestrator-state.yaml
    READ: All existing handoff files

  2. Determine Resume Point:
    current_feature = orchestrator-state.current_feature_id
    feature_status = manifest.features[current_feature].status

    CASE feature_status:

      "in_progress":
        # Feature agent was spawned but may not have completed
        handoff_path = manifest.features[current_feature].handoff_file

        IF handoff file exists:
          # Agent completed, orchestrator didn't process yet
          ACTION: Process handoff file, update manifest, continue to next
          REASON: "Feature agent completed, continuing orchestration"

        ELSE:
          # Agent was interrupted or failed
          ACTION: Re-spawn same feature agent with same context
          REASON: "Feature agent interrupted, respawning to complete"

      "pending":
        # Feature not yet started
        ACTION: Spawn this feature agent
        REASON: "Resuming with next pending feature"

      "completed":
        # Current feature already done, move to next
        next_feature = Get next pending feature from manifest
        ACTION: Spawn next feature agent
        REASON: "Continuing with next feature in sequence"

      "blocked":
        # Feature waiting on dependency
        ACTION: Check if blocking feature completed
        IF blocking feature complete:
          Unblock current feature, spawn agent
        ELSE:
          Spawn blocking feature first

  3. Resume Execution:
    Continue with Step 2 (Feature Spawning) from determined resume point

  4. Update State:
    APPEND to execution_log:
      - timestamp
      - event: "session_resumed"
      - resume_from_feature
      - resume_reason
```

### Resumption Guarantees

**What is preserved**:
- All completed feature plans (handoff files intact)
- Feature manifest with status
- Token usage tracking
- Dependencies and priorities
- User's original request

**What is recomputed**:
- In-progress feature re-executed if no handoff file
- Orchestrator context rebuilt from state files
- Next feature determination based on current state

**Idempotency**:
- Re-processing completed feature: Skipped (reads existing handoff)
- Re-spawning in-progress feature: Safe (subprocess has no side effects)
- Re-spawning failed feature: Safe (planning is read-only)

---

## Error Handling Patterns

### Error Categories

#### 1. Feature Agent Timeout

```yaml
SCENARIO:
  Feature agent subprocess exceeds 10-minute execution time

DETECTION:
  Orchestrator monitors subprocess duration
  Warning at 7 minutes, timeout at 10 minutes

HANDLING:
  1. Send interrupt signal to subprocess
  2. Check if partial handoff file exists
  3. IF partial handoff exists:
      - Load what agent completed
      - Mark feature as "requires_split" (scope too large)
      - Update manifest with split
  4. IF no handoff:
      - Mark feature as "failed" in manifest
      - Prompt user:
          "[R] Retry with same scope
           [S] Split feature into smaller scopes
           [M] Provide manual plan for this feature
           [C] Skip this feature"
  5. Log error in orchestrator-state.yaml
  6. Continue to next feature or retry based on user choice
```

#### 2. Feature Agent Reports "Requires Split"

```yaml
SCENARIO:
  Feature agent discovers scope is too large during exploration

DETECTION:
  Agent writes handoff file with:
    status: "requires_split"
    requires_split: true
    split_rationale: "..."
    proposed_features: [...]

HANDLING:
  1. Read handoff file
  2. Extract split rationale and proposed features
  3. Validate proposed split (check feature detection rules)
  4. Update manifest:
      - Original feature status: "split"
      - Add new features with sequential IDs
      - Preserve any partial plan from original agent
  5. Adjust priorities (new features may be prerequisites)
  6. Update progress tracking
  7. Continue spawning with first new feature
  8. Log split in execution_log
```

#### 3. Feature Agent Reports "Blocked"

```yaml
SCENARIO:
  Feature agent discovers prerequisite work not in scope

DETECTION:
  Agent writes handoff file with:
    status: "blocked"
    blocked_by: "Description of blocking issue"
    proposed_prerequisite_feature: {...}
    current_feature_plan_if_unblocked: {...}

HANDLING:
  1. Read handoff file
  2. Extract blocking issue and proposed prerequisite
  3. Present to user:
      "Feature '{name}' is blocked by: {blocking_issue}

       Proposed solution: Create prerequisite feature '{proposed_name}'

       [A] Accept and create prerequisite
       [R] Reject and continue with blocked feature anyway
       [M] Manually define prerequisite"

  4. IF user accepts:
      - Create prerequisite feature in manifest
      - Mark current feature as "blocked"
      - Add dependency: current depends_on prerequisite
      - Re-sequence: prerequisite before current
      - Spawn prerequisite feature agent

  5. IF user rejects:
      - Mark current feature as "completed" with caveat
      - Note blocking issue in plan
      - Continue to next feature

  6. Log blocking issue in execution_log
```

#### 4. Subprocess Crash or Error

```yaml
SCENARIO:
  Feature agent subprocess crashes unexpectedly

DETECTION:
  Subprocess exit code != 0
  OR subprocess killed by system
  OR unexpected termination

HANDLING:
  1. Capture subprocess error output
  2. Log error in orchestrator-state.yaml:
      - error_type: "subprocess_crash"
      - feature_id
      - error_message
      - subprocess_exit_code

  3. Check for partial artifacts:
      - Partial handoff file
      - Log files from subprocess

  4. Prompt user:
      "Feature '{name}' subprocess crashed with error: {message}

       [R] Retry this feature
       [S] Skip this feature
       [M] Provide manual plan
       [D] Debug (show subprocess logs)"

  5. Based on user choice:
      - Retry: Re-spawn with same context
      - Skip: Mark "failed", continue to next
      - Manual: Accept user-provided plan, continue
      - Debug: Display logs, then re-prompt

  6. Update manifest status appropriately
  7. Continue orchestration
```

#### 5. Invalid Handoff File

```yaml
SCENARIO:
  Feature agent writes malformed YAML or incomplete handoff

DETECTION:
  YAML parsing fails
  OR required fields missing
  OR schema validation fails

HANDLING:
  1. Log parsing error
  2. Attempt to salvage readable content
  3. Prompt user:
      "Feature '{name}' returned invalid handoff file.
       Error: {parse_error}

       Partial content readable: {yes/no}

       [R] Retry feature (respawn agent)
       [F] Fix handoff file manually
       [P] Proceed with partial data
       [S] Skip feature"

  4. Based on user choice:
      - Retry: Re-spawn agent
      - Fix: Open handoff file in editor, wait for fix
      - Partial: Use what's readable, note incomplete
      - Skip: Mark failed, continue

  5. Update manifest
  6. Consider: If multiple invalid handoffs, may indicate template issue
```

---

## Token Budget Management

### Budget Allocation Strategy

```yaml
TOTAL_SESSION_BUDGET: 100000              # Example session budget

ALLOCATION:
  orchestrator_allocation: 20000          # 20% for orchestrator
    decomposition: 5000                   # Step 1
    spawning_overhead: 10000              # Step 2 coordination
    consolidation: 5000                   # Step 3

  feature_agents_allocation: 60000        # 60% for feature agents
    per_feature_budget: 8000              # Assuming ~7-8 features

  reserve_allocation: 20000               # 20% reserve
    unexpected_splits: 10000              # Feature splits during exploration
    user_interactions: 5000               # Clarifications, refinements
    error_recovery: 5000                  # Retries, debugging
```

### Budget Tracking

```yaml
TRACKING_LOGIC:

  On Orchestrator Action:
    - Estimate tokens for action (decomposition analysis, user prompt, etc.)
    - Subtract from orchestrator_allocation
    - Update orchestrator-state.yaml token_usage

  On Feature Agent Spawn:
    - Allocate per_feature_budget to agent
    - Subtract from feature_agents_allocation
    - Track in handoff file (agent reports actual usage)
    - Update orchestrator-state.yaml

  On Feature Agent Return:
    - Read actual token usage from handoff
    - Calculate variance (actual vs allocated)
    - Update feature_agents_allocation
    - If variance significant, adjust per_feature_budget for remaining features

  On Feature Split:
    - Allocate reserve budget to new features
    - Warn user if reserve depleting
    - May request budget increase if needed

  Budget Warnings:
    - Warn at 80% total budget consumed
    - Warn if reserve < 10% of original
    - Warn if features remain but per_feature_budget insufficient
```

### Budget Optimization

**Techniques to minimize token usage**:

1. **Lightweight Context Packets**
   - Send feature scope + project context path, not full project context
   - Agent reads project-context.md itself (doesn't inflate orchestrator context)

2. **Structured Handoffs**
   - Agents return plans (YAML), not full file contents
   - Orchestrator aggregates metadata, not raw data

3. **Sequential Processing**
   - One feature at a time prevents parallel context bloat
   - Previous feature's handoff is stored in file, not in-context

4. **Graceful Degradation**
   - If budget low, reduce per_feature_budget
   - Ask agents to produce more concise plans
   - Merge remaining small features

5. **Subprocess Isolation**
   - Each feature agent gets clean context
   - No accumulation of previous features' exploration in agent context

---

## Session Archive Structure

When orchestration completes:

```yaml
ARCHIVE_ACTION:
  1. Create archive directory:
     output/.orchestrator/archived/session-{timestamp}/

  2. Copy all session files:
     - manifest.yaml
     - orchestrator-state.yaml
     - All handoff files (feature-*-handoff.yaml)
     - consolidated-plan.md

  3. Create session-summary.md:
     - Original user request
     - Feature decomposition (count, names)
     - Total duration
     - Token usage breakdown
     - Key decisions or splits
     - Final consolidated plan path

  4. Optional: Compress archive for long-term storage
     tar -czf session-{timestamp}.tar.gz archived/session-{timestamp}/

  5. Clean active session directory:
     Keep only last 3 active sessions for space management
     OR user-configurable retention policy
```

---

## Performance Metrics & Monitoring

### Key Metrics

Track these metrics in `orchestrator-state.yaml` for optimization:

```yaml
performance_metrics:
  # Time metrics
  total_session_duration_seconds: 600
  decomposition_duration_seconds: 45
  feature_planning_duration_seconds: 480
  consolidation_duration_seconds: 75

  # Per-feature metrics
  average_feature_duration_seconds: 120
  fastest_feature_duration_seconds: 60
  slowest_feature_duration_seconds: 300

  # Token metrics
  total_tokens_used: 42000
  tokens_per_feature_avg: 6000
  orchestrator_tokens: 8000
  feature_agents_tokens: 34000

  # Decomposition quality
  features_identified: 5
  features_split_during_planning: 1
  features_merged: 0
  final_feature_count: 6

  # Success rates
  features_completed_first_try: 5
  features_requiring_retry: 0
  features_manually_planned: 0

  # User interactions
  clarification_questions_asked: 2
  user_modifications_to_decomposition: 1
```

### Monitoring Alerts

**Alert conditions**:
- Feature duration > 10 minutes: Timeout risk
- Token usage > 80%: Budget risk
- Multiple features requiring split: Under-decomposition pattern
- High retry rate: Template or subprocess issue

---

## Integration Patterns

### Pattern 1: Orchestrator → dev-story Workflow

```yaml
HANDOFF:
  FROM: feature-orchestrator (Step 4: Next Actions)
  TO: dev-story workflow

  TRANSFER:
    input_file: consolidated-plan.md
    features: Each feature becomes potential story
    sequence: Implementation order from consolidation

  WORKFLOW:
    1. Orchestrator generates consolidated-plan.md
    2. Asks user: "Ready to implement?"
    3. IF yes:
        - Spawn dev-story workflow
        - Pass feature-001 plan as input
        - dev-story creates story file
        - dev-story implements
    4. When feature-001 complete:
        - Orchestrator spawns dev-story for feature-002
        - Continues until all features implemented
```

### Pattern 2: Orchestrator → Agent Teams

```yaml
HANDOFF:
  FROM: feature-orchestrator (Step 4: Next Actions)
  TO: Agent Teams (parallel implementation)

  TRANSFER:
    input_file: consolidated-plan.md
    features: All features with clear boundaries
    team_structure: Dev + Tea + Tech-Writer

  WORKFLOW:
    1. Orchestrator generates consolidated-plan.md
    2. Asks user: "Implementation approach?"
    3. IF parallel:
        - Spawn Agent Team
        - Assign features to dev teammates
        - Dev implements features in parallel
        - Tea writes tests in parallel
        - Tech-writer documents in parallel
    4. Team completes all features concurrently
```

### Pattern 3: Orchestrator → Orchestrator (Nested)

```yaml
HANDOFF:
  FROM: parent orchestrator
  TO: child orchestrator (for epic-sized feature)

  TRANSFER:
    When feature agent reports "requires_split"
    AND split scope is still large (epic-sized)
    INSTEAD of simple split → Spawn nested orchestrator

  WORKFLOW:
    1. Parent orchestrator identifies epic-sized feature
    2. Creates nested session for that feature
    3. Spawns child orchestrator with feature scope as request
    4. Child orchestrator decomposes further
    5. Child completes, returns consolidated plan
    6. Parent treats child's plan as single feature handoff
    7. Parent continues with other features
```

---

## Reference: Related Patterns

- **Subprocess Optimization Pattern 2**: Per-file subprocess for deep analysis
  - Location: `team/workflows/builders/workflow/data/subprocess-optimization-patterns.md`
  - Reused: Per-feature subprocess with structured return

- **Party Mode Orchestration**: Sequential agent coordination
  - Location: `team/workflows/party-mode/`
  - Reused: Agent selection, sequential spawning, state tracking

- **Evaluation Orchestrator**: Phase-based execution
  - Location: `backend/app/services/evaluation_orchestrator_service.py`
  - Reused: Progress tracking, phase completion logic

- **Workflow Chaining**: Input/output contracts
  - Location: Various BMAD workflows
  - Reused: Handoff protocol between workflows

---

This document provides the complete state management and orchestration patterns needed to implement a resilient, resumable feature orchestrator that prevents context overflow through intelligent decomposition and subprocess isolation.
