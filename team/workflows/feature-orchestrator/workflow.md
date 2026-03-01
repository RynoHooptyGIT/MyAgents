# Feature Orchestrator Workflow

---
name: feature-orchestrator
description: Decomposes complex requests into features, spawns isolated planning agents, aggregates results
workflow_type: orchestration
orchestration_mode: sequential_subprocess
version: "1.0.0"
bmad_module: core
---

## OVERVIEW

**Purpose**: Prevent context overflow in large planning tasks by decomposing requests into discrete features and orchestrating isolated planning agents per feature.

**Problem Solved**: When user requests are complex (multiple features, large scope), a single agent's context can overflow, leading to timeouts, incomplete analysis, or poor quality plans. This workflow solves this by:
1. Decomposing requests into natural feature boundaries
2. Spawning isolated agents per feature (clean context)
3. Aggregating feature plans into consolidated deliverable
4. Maintaining lightweight orchestrator context throughout

**When to Use**:
- User request involves multiple distinct features (3+)
- Request spans multiple domains (frontend + backend + testing)
- Estimated scope exceeds 5 days of work
- User explicitly requests feature-based breakdown
- Previous planning attempts hit context limits

**When NOT to Use**:
- Single small feature (use quick-dev or dev-story)
- Simple bug fixes or enhancements
- Tasks that don't require planning phase

---

## ARCHITECTURE

**Pattern**: Sequential Subprocess Coordination

```
User Request
    ↓
┌─────────────────────────────────────────┐
│   ORCHESTRATOR (Lightweight)            │
│                                         │
│  [Step 1] Decomposition                │
│     ↓                                   │
│  [Step 2] Feature Spawning ←───┐       │
│     │                           │       │
│     ├─→ Spawn Agent 1 ──→ Plan 1       │
│     ├─→ Spawn Agent 2 ──→ Plan 2       │
│     ├─→ Spawn Agent 3 ──→ Plan 3       │
│     └────────────────────┘              │
│     ↓                                   │
│  [Step 3] Consolidation                │
│     ↓                                   │
│  [Step 4] Next Actions                 │
└─────────────────────────────────────────┘
    ↓
Consolidated Plan + Feature Plans
    ↓
Implementation Workflow (dev-story/agent-teams)
```

**Key Principles**:
1. **Lightweight Orchestrator**: Only coordinates, never implements
2. **Isolated Contexts**: Each feature agent gets clean context
3. **Structured Handoffs**: Agents return YAML plans, not full content
4. **Sequential Processing**: One feature at a time maintains orchestrator focus
5. **Resumable**: Session state persisted, can resume after interruption

---

## INITIALIZATION

### Startup Sequence

```yaml
WORKFLOW_START:

  1. Check for Incomplete Sessions:
     SEARCH: output/.orchestrator/session-*/
     FILTER: WHERE orchestrator-state.yaml.current_phase != "complete"

     IF incomplete session found:
       PROMPT USER: "Resume existing session or start new?"

       [R] Resume - Load session state, continue from last feature
       [N] New - Archive old session, start fresh
       [V] View - Show session details
       [D] Delete - Remove old session, start fresh

       IF Resume:
         LOAD: session state
         DETERMINE: Resume point (see Resumption Logic)
         CONTINUE: From resume point

       IF New/Delete:
         ARCHIVE/DELETE: Old session
         CONTINUE: With new session initialization

  2. Create New Session:
     timestamp = current ISO 8601 timestamp
     session_id = "orch-{timestamp}"
     session_dir = "output/.orchestrator/session-{timestamp}"

     CREATE: session_dir/

     INITIALIZE: Empty manifest (will be created in Step 1)
     INITIALIZE: orchestrator-state.yaml with startup values

  3. Load Configuration:
     READ: team/config.yaml (if exists)
     EXTRACT:
       - user_name
       - output_folder
       - communication_language
       - token_budget (default: 100000)

  4. Display Welcome:
     Welcome to Feature Orchestrator

     This workflow helps manage complex requests by:
     - Breaking them into discrete features
     - Planning each feature in isolation
     - Aggregating into a consolidated plan

     Session ID: {session_id}

     Ready to analyze your request...

  5. Proceed to Step 1 (Decomposition)
```

---

## WORKFLOW EXECUTION

### Step 1: Feature Decomposition

**File**: `./steps/step-01-decomposition.md`

**Purpose**: Analyze user request and decompose into discrete features

**Process**:
1. Parse user request (identify enumerations, domains, goals)
2. Apply feature detection rules (5 rules + scoring matrix)
3. Generate preliminary feature manifest
4. Validate decomposition (checklist)
5. Present to user for approval
6. Handle feedback (merge/split/rename)
7. Finalize manifest.yaml
8. Initialize orchestrator-state.yaml

**Outputs**:
- `manifest.yaml` - Feature list with scopes, priorities, dependencies
- `orchestrator-state.yaml` - Initial state with session info

**Success Criteria**:
- User-approved feature decomposition
- Clear feature boundaries
- Dependencies identified
- Manifest written to session directory

**Transition**: Proceed to Step 2 (Feature Spawning)

---

### Step 2: Feature Spawning & Orchestration

**File**: `./steps/step-02-feature-spawning.md`

**Purpose**: Spawn isolated planning agents per feature, process handoffs

**Process**:
1. Load manifest, filter pending features
2. FOR EACH feature (in priority order):
   a. Prepare context packet (scope, constraints, handoff path)
   b. Spawn subprocess agent (Task tool, Plan subagent)
   c. Agent explores codebase, designs approach
   d. Agent writes handoff YAML file
   e. Wait for handoff file (max 10 minutes)
   f. Process handoff based on status:
      - completed: Aggregate, continue to next
      - requires_split: Update manifest with new features
      - blocked: Handle blocking issue (create prerequisite or mark blocked)
   g. Update manifest and state
   h. Display progress
3. Repeat until all features processed

**Outputs**:
- `feature-{id}-handoff.yaml` - Structured plan per feature
- Updated `manifest.yaml` - Status changes, splits, blocks
- Updated `orchestrator-state.yaml` - Execution log, token usage

**Success Criteria**:
- All features have status != "pending"
- Each feature has handoff file
- Manifest tracks all status changes
- Ready for consolidation

**Transition**: Proceed to Step 3 (Consolidation)

---

### Step 3: Plan Consolidation

**File**: `./steps/step-03-consolidation.md`

**Purpose**: Aggregate feature plans into consolidated implementation plan

**Process**:
1. Load all feature handoff files
2. Analyze cross-feature dependencies
3. Sequence implementation order (topological sort)
4. Calculate totals (effort, files, risks, dependencies)
5. Generate consolidated-plan.md from template
6. Validate plan (completeness, accuracy)
7. Display summary

**Outputs**:
- `consolidated-plan.md` - Complete implementation plan
- Updated `orchestrator-state.yaml` - Consolidation complete

**Success Criteria**:
- All completed features included in plan
- Valid implementation sequence
- Totals calculated correctly
- Document is readable and actionable

**Transition**: Proceed to Step 4 (Next Actions)

---

### Step 4: Next Actions & Handoff

**File**: `./steps/step-04-next-actions.md`

**Purpose**: Recommend next workflow and facilitate handoff to implementation

**Process**:
1. Analyze consolidated plan
2. Recommend implementation approach:
   - agent-teams (parallel) if features independent
   - dev-story (sequential) if dependencies or solo dev
   - nested orchestration if features are epic-sized
3. Present options to user
4. Handle user choice:
   - Implement now: Spawn recommended workflow
   - Choose different: Show all options
   - Review plan: Display/open plan
   - Export: Archive and exit
   - Manual: Provide plan, user implements
5. Archive session
6. Display completion message

**Outputs**:
- Archived session in `output/.orchestrator/archived/`
- `session-summary.md` - Session recap
- Handoff to implementation workflow (if selected)

**Success Criteria**:
- User has clear next steps
- Session archived
- Implementation workflow spawned (if requested)
- Workflow complete

---

## RESUMPTION LOGIC

If session interrupted and user resumes:

```yaml
RESUMPTION_SEQUENCE:

  1. Load Session State:
     READ: session-{timestamp}/orchestrator-state.yaml
     READ: session-{timestamp}/manifest.yaml

  2. Determine Resume Point:
     current_phase = orchestrator_state.current_phase
     current_feature_id = orchestrator_state.current_feature_id

     CASE current_phase:

       "decomposition":
         # Step 1 incomplete
         ACTION: Restart Step 1 with original user request
         REASON: Decomposition is quick, safe to restart

       "feature_planning":
         # Step 2 in progress
         feature_status = manifest.features[current_feature_id].status

         IF feature_status == "in_progress":
           handoff_exists = CHECK FILE feature-{id}-handoff.yaml

           IF handoff exists:
             # Agent completed, orchestrator didn't process yet
             ACTION: Process handoff, continue to next feature
           ELSE:
             # Agent interrupted
             ACTION: Re-spawn agent for same feature

         IF feature_status == "pending":
           # Feature not started
           ACTION: Spawn agent for this feature

         IF feature_status == "completed":
           # Feature done, move to next
           ACTION: Spawn next pending feature

       "consolidation":
         # Step 3 incomplete
         ACTION: Restart Step 3 (quick, reads handoff files)

       "complete":
         # Session already complete
         INFORM: "Session already complete, see archived artifacts"
         OFFER: "Start new session?"

  3. Resume Execution:
     Continue workflow from determined resume point

  4. Log Resumption:
     APPEND orchestrator-state.yaml:
       - event: "session_resumed"
         resume_from: {resume_point}
         timestamp: {timestamp}
```

**Resumption Guarantees**:
- Completed features never re-executed (reads existing handoff)
- In-progress features re-spawned if no handoff (planning is idempotent)
- State preserved across resumptions
- User can inspect state before resuming

---

## TOKEN BUDGET MANAGEMENT

**Default Allocation** (for 100,000 token budget):

```yaml
TOKEN_ALLOCATION:
  orchestrator: 20,000                    # Coordination overhead
    - decomposition: 5,000
    - spawning_coordination: 10,000
    - consolidation: 5,000

  feature_agents: 60,000                  # Feature planning
    - per_feature: 8,000                  # ~7-8 features
    - scales with feature count

  reserve: 20,000                         # Splits, retries, errors
    - unexpected_splits: 10,000
    - user_interactions: 5,000
    - error_recovery: 5,000
```

**Budget Tracking**:
- Monitored in orchestrator-state.yaml
- Warnings at 80% usage
- Adjust per_feature_budget dynamically if variance high
- Request budget increase if needed

**Budget Optimization**:
- Lightweight context packets (references, not full content)
- Structured handoffs (plans, not code)
- Sequential processing (prevents parallel bloat)
- Subprocess isolation (each agent gets clean context)

---

## ERROR HANDLING

### Common Errors

**Feature Agent Timeout** (> 10 minutes):
- Check for partial handoff
- Prompt user: Retry / Split / Manual / Skip
- Continue to next feature

**Invalid Handoff File** (malformed YAML):
- Attempt to salvage partial content
- Prompt user: Retry / Fix manually / Proceed partial / Skip
- Log error

**Subprocess Crash** (exit code != 0):
- Capture error output
- Log to state file
- Prompt user: Retry / Skip / Debug
- Continue to next feature

**Feature Split** (scope too large):
- Extract proposed features
- Update manifest with new features
- Re-sort by priority
- Continue with next feature

**Feature Blocked** (prerequisite needed):
- Extract blocking issue
- Prompt user: Accept prerequisite / Reject / Manual
- Create prerequisite feature if accepted
- Continue (may spawn prerequisite next)

---

## CONFIGURATION

### Optional Configuration File

**Location**: `team/workflows/feature-orchestrator/config.yaml`

```yaml
# Feature Orchestrator Configuration (optional)

token_budget:
  total: 100000
  orchestrator: 20000
  per_feature: 8000
  reserve: 20000

timeouts:
  feature_agent_timeout_minutes: 10
  feature_agent_warning_minutes: 7

session_management:
  archive_after_completion: true
  compress_archives: false
  keep_active_sessions: 3
  auto_resume_on_startup: false  # Prompt instead

feature_detection:
  default_agent_persona: "architect"
  min_features_for_orchestration: 2
  max_features_before_warning: 10

output:
  session_directory: "output/.orchestrator"
  archive_directory: "output/.orchestrator/archived"
  verbose_progress: true
```

---

## DIRECTORY STRUCTURE

```
team/workflows/feature-orchestrator/
├── workflow.md                          # This file (entry point)
├── config.yaml                          # Optional configuration
├── steps/
│   ├── step-01-decomposition.md         # Feature detection & manifest
│   ├── step-02-feature-spawning.md      # Core orchestration logic
│   ├── step-03-consolidation.md         # Plan aggregation
│   └── step-04-next-actions.md          # Workflow handoff
├── data/
│   ├── feature-detection-rules.md       # Detection algorithm reference
│   └── orchestration-patterns.md        # State schemas, resumption
└── templates/
    ├── feature-handoff-template.yaml    # Agent return contract
    └── consolidated-plan-template.md    # Final deliverable format
```

---

## OUTPUT ARTIFACTS

### Per Session

**Active Session** (`output/.orchestrator/session-{timestamp}/`):
- `manifest.yaml` - Feature list, status, dependencies
- `orchestrator-state.yaml` - Execution log, token usage, resumption data
- `feature-{id}-handoff.yaml` - Plan per feature (1 per feature)
- `consolidated-plan.md` - Final aggregated plan

**Archived Session** (`output/.orchestrator/archived/session-{timestamp}/`):
- All files from active session
- `session-summary.md` - Session recap

---

## INTEGRATION WITH BMAD WORKFLOWS

### Upstream (What Triggers Orchestrator)

- **User direct invocation**: When user has complex request
- **quick-dev workflow**: If quick-dev detects scope too large
- **sprint-planning workflow**: To plan epics with multiple stories

### Downstream (What Orchestrator Spawns)

- **dev-story workflow**: Sequential implementation per feature
- **agent-teams workflow**: Parallel implementation with team
- **Nested orchestrator**: If features are epic-sized themselves

### Handoff Protocol

**To dev-story**:
```
INPUT: feature-{id}-handoff.yaml
WORKFLOW: dev-story creates story file from feature plan
SEQUENCE: One feature at a time
```

**To agent-teams**:
```
INPUT: consolidated-plan.md
WORKFLOW: Agent team implements all features in parallel
TEAM: Dev + Tea + Tech-Writer
```

---

## USAGE EXAMPLES

### Example 1: Simple Multi-Feature Request

**User**: "Add JWT auth, create dashboard, write tests"

**Orchestrator Actions**:
1. Decomposition: 3 features detected (auth, dashboard, tests)
2. Spawning: 3 agents spawned sequentially
3. Consolidation: Plans aggregated, 3 phases identified
4. Next Actions: Recommends dev-story (dependencies require sequence)

**Output**: Consolidated plan with 3 features, ~10 days effort

---

### Example 2: Large Request with Splits

**User**: "Rebuild authentication system with OAuth, 2FA, passwordless login, magic links, and audit logging"

**Orchestrator Actions**:
1. Decomposition: 5 features initially
2. Spawning:
   - Feature 1 (OAuth): Agent reports requires_split → becomes 2 features
   - Feature 2 (2FA): Completed
   - Feature 3 (Passwordless): Completed
   - Feature 4 (Magic Links): Completed
   - Feature 5 (Audit Logging): Blocked (needs database schema changes first)
3. Orchestrator creates prerequisite feature for database
4. Consolidation: 7 features total (after split + prerequisite)
5. Next Actions: Recommends agent-teams (many features, some parallel)

**Output**: Consolidated plan with 7 features, ~20 days effort

---

## SUCCESS METRICS

Track these metrics for continuous improvement:

- **Feature Detection Accuracy**: How often decomposition needs revision?
- **Agent Success Rate**: % agents completing without timeout/error
- **Split Frequency**: How often features require splitting?
- **Block Frequency**: How often features are blocked?
- **Token Efficiency**: Average tokens per feature
- **Time Efficiency**: Average time per feature
- **User Satisfaction**: Do users approve decomposition first try?

---

## TROUBLESHOOTING

### Issue: Decomposition doesn't make sense to user

**Solution**:
- Review feature detection rules
- Ask user for their mental model
- Use user's domain knowledge for boundaries

### Issue: Many features timing out

**Solution**:
- Increase per_feature timeout
- Check if features are too large (should split earlier)
- Review project-context.md complexity

### Issue: Frequent splits during planning

**Solution**:
- Apply Rule 3 (size threshold) more aggressively in decomposition
- Initial features may be too large

### Issue: Complex circular dependencies

**Solution**:
- Merge tightly coupled features
- Identify shared infrastructure as separate feature
- Reorder features to linearize dependencies

---

## VERSION HISTORY

**v1.0.0** (2026-02-08):
- Initial release
- Subprocess optimization pattern implementation
- Feature detection algorithm (5 rules)
- Resumable orchestration
- Structured YAML handoffs
- Consolidated plan generation

---

## WORKFLOW EXIT

```
✓ Feature Orchestrator Workflow Complete

Session: {session_id}
Duration: {duration_minutes} minutes
Features Planned: {completed_count}

Deliverables:
- Consolidated Plan: {plan_path}
- Feature Plans: {session_dir}/feature-*-handoff.yaml
- Session Archive: {archive_path}

{IF next_workflow}
Proceeding to: {next_workflow_name}
{ELSE}
Thank you for using Feature Orchestrator!
{END IF}
```

---

**End of Workflow Definition**
