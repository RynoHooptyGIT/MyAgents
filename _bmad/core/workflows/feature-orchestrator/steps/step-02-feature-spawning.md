# Step 2: Feature Spawning & Orchestration

---
step_name: "feature-spawning"
step_number: 2
subprocess_optimization: true  # Uses Subprocess Pattern 2: per-feature subprocess
---

## YOUR TASK

Spawn feature planning agents sequentially, one per feature. Each agent explores the codebase within its feature scope, designs an implementation approach, and returns a structured plan via YAML handoff file. Process each handoff and handle splits, blocks, or completion appropriately.

## ROLE

You are the **Feature Orchestrator** in **execution mode**. Your responsibilities:
- Spawn subprocess agents with isolated contexts
- Monitor agent progress  
- Process handoff files when agents complete
- Handle feature splits (scope too large)
- Handle blocks (prerequisite work needed)
- Maintain lightweight orchestrator context
- Update state files after each feature

**CRITICAL**: You coordinate but never implement. All planning happens in subprocesses.

## SUBPROCESS PATTERN

**Pattern Used**: Subprocess Optimization Pattern 2 (per-feature subprocess for deep analysis)

**DO NOT BE LAZY** - For EACH feature in manifest:

1. Launch subprocess that:
   - Loads feature context packet
   - Explores codebase for ONLY that feature scope
   - Designs implementation approach
   - Returns structured plan to handoff file

2. Subprocess returns:
   - Handoff YAML with plan details
   - Status (completed/requires_split/blocked)
   - Files to modify/create
   - Dependencies and risks

3. Orchestrator processes handoff:
   - IF requires_split: Update manifest, create new features
   - IF blocked: Mark blocked, sequence appropriately
   - IF completed: Aggregate plan, proceed to next

**Golden Rule**: Subprocess returns structured plan (YAML), not full file contents or code. Keeps orchestrator context lightweight.

---

## EXECUTION SEQUENCE

### 1. Load Manifest

```yaml
LOAD: {session_dir}/manifest.yaml

EXTRACT:
  - features list
  - current progress
  - dependencies

FILTER: features WHERE status == "pending"

SORT BY: priority (ascending)

RESULT: Ordered list of pending features
```

---

### 2. Feature Loop (Sequential Processing)

FOR EACH pending feature in priority order:

#### 2.1 Prepare Context Packet

```yaml
CONTEXT_PACKET:
  feature_id: "{feature_id}"
  feature_name: "{feature_name}"
  feature_scope: |
    {multiline_scope_from_manifest}

  constraints:
    - integration_points: []        # From manifest or previous features
    - patterns_to_follow: []        # From project-context.md
    - boundaries: |                 # What's NOT in scope
        Stay within feature scope.
        If scope expands, set requires_split: true.

  project_context_path: "{absolute_path_to_project_context_md}"

  dependencies:
    prerequisite_features: []       # Features this depends on
    completed_features: []          # Features already planned

  handoff_file_path: "{session_dir}/feature-{id}-handoff.yaml"

  token_budget: {per_feature_allocation}  # Default: 8000

  instructions: |
    You are a feature planning agent for: {feature_name}

    YOUR MISSION:
    - Explore codebase ONLY within feature scope
    - Use Read, Grep, Glob, Bash (read-only) tools
    - Design implementation approach
    - Identify files to modify/create
    - Document risks and dependencies
    - Estimate complexity and effort
    - Write structured plan to handoff file

    HANDOFF PROTOCOL:
    Write your plan to: {handoff_file_path}
    Use schema from: _bmad/core/workflows/feature-orchestrator/templates/feature-handoff-template.yaml

    CRITICAL RULES:
    1. Stay within feature scope - if scope too large, set requires_split: true
    2. If you discover prerequisite work, set status: blocked
    3. DO NOT edit files - planning only
    4. Return structured YAML plan, not full file contents
    5. Budget: {token_budget} tokens

    DELIVERABLE:
    A complete handoff YAML file with:
    - status: completed | requires_split | blocked
    - planning_summary (if completed)
    - split_rationale (if requires_split)
    - blocked_by (if blocked)
```

#### 2.2 Spawn Subprocess

**Subprocess Invocation**:

```bash
# Note: This is conceptual - actual subprocess spawning uses Task tool

# Spawn subprocess with:
- Agent persona: {agent_persona}  # From manifest
- Prompt: {context_packet.instructions}
- Tools: Read, Grep, Glob, Bash (read-only)
- Timeout: 10 minutes
- Output: Write to {handoff_file_path}
```

**Task Tool Usage**:
```
Use Task tool with subagent_type="Plan"

Prompt includes:
- Feature scope
- Constraints and boundaries
- Project context path (agent reads it)
- Handoff file path
- Instructions to write YAML plan
```

**Update Manifest**:
```yaml
UPDATE manifest.yaml:
  features[current].status: "in_progress"
  features[current].spawned_at: "{timestamp}"
```

**Update State**:
```yaml
APPEND TO orchestrator-state.yaml execution_log:
  - timestamp: "{timestamp}"
    event: "feature_spawned"
    feature_id: "{feature_id}"
    agent_persona: "{agent_persona}"
    context_packet_size: {tokens}
```

**Display Progress**:
```
🚀 Spawning Feature Agent

Feature: {feature_name} ({feature_id})
Agent: {agent_persona}
Scope: {one_line_scope}
Progress: {completed}/{total} features

Agent is exploring codebase and designing implementation...
(This may take 3-8 minutes)
```

#### 2.3 Wait for Subprocess Completion

**Monitoring**:
```
WAIT FOR: {handoff_file_path} to exist

TIMEOUT: 10 minutes

WARNINGS:
  - At 5 minutes: "Feature agent still working..."
  - At 7 minutes: "Feature agent approaching timeout..."
  - At 10 minutes: TIMEOUT - handle error

CHECK EVERY: 10 seconds for handoff file
```

**Completion Detection**:
```
IF handoff file exists:
  Subprocess complete - proceed to processing

IF timeout reached AND no handoff:
  Subprocess failed or hung - handle error

IF subprocess exit code != 0:
  Subprocess crashed - handle error
```

#### 2.4 Process Handoff File

**Load Handoff**:
```yaml
READ: {handoff_file_path}

VALIDATE YAML:
  - Parse as valid YAML
  - Check required fields based on status
  - Validate enums (complexity, severity, etc.)

IF validation fails:
  Handle error: invalid handoff file
```

**Process Based on Status**:

---

##### Status: "completed" ✓

```yaml
ACTIONS:
1. Extract plan summary:
   - approach
   - files_to_modify
   - files_to_create
   - dependencies
   - risks
   - estimated_complexity

2. Update manifest:
   UPDATE features[current]:
     status: "completed"
     completed_at: "{timestamp}"

3. Aggregate to orchestrator context:
   # Store lightweight metadata, not full plan
   completed_features_summary:
     - feature_id: "{feature_id}"
       files_to_modify_count: {count}
       files_to_create_count: {count}
       effort_days: {days}
       handoff_file: "{path}"

4. Update progress:
   UPDATE manifest.progress:
     completed_features: {increment}
     progress_percentage: {recalculate}

5. Update state:
   APPEND TO orchestrator-state.yaml:
     - timestamp: "{timestamp}"
       event: "feature_completed"
       feature_id: "{feature_id}"
       handoff_received: true
       files_to_modify: {count}
       files_to_create: {count}
       estimated_effort_days: {days}

   UPDATE token_usage:
     feature_agents_total: {add_tokens_from_handoff}

6. Display summary:
   ✓ Feature Complete: {feature_name}

   Approach: {one_line_approach}
   Files to modify: {count}
   Files to create: {count}
   Effort: {days} days
   Risks: {high_risk_count} high, {medium_risk_count} medium

   Progress: {completed}/{total} features ({percentage}%)

7. Continue to next feature
```

---

##### Status: "requires_split" 🔀

```yaml
ACTIONS:
1. Extract split information:
   - split_rationale
   - proposed_features (list)
   - partial_plan (work done so far)

2. Validate proposed split:
   FOR EACH proposed_feature:
     - Check feature name is clear
     - Check scope is well-defined
     - Check estimated_effort is reasonable
     - Check dependencies make sense

3. Update manifest - mark original as split:
   UPDATE features[current]:
     status: "split"
     split_into: [list of new feature IDs]
     split_reason: "{rationale}"

4. Add new features to manifest:
   FOR EACH proposed_feature:
     NEW FEATURE:
       feature_id: "feature-{next_id}"
       feature_name: "{proposed_name}"
       status: "pending"
       priority: {calculate_priority}
       agent_persona: "{suggested_or_inherited}"
       scope: "{proposed_scope}"
       dependencies:
         - IF prerequisite: Add dependency
       spawned_at: null
       handoff_file: "feature-{next_id}-handoff.yaml"
       split_from: "{original_feature_id}"

5. Re-calculate progress:
   UPDATE manifest.progress:
     total_features: {add_new_features_count}
     split_features: {increment}
     # completed and pending adjust accordingly

6. Update state:
   APPEND TO orchestrator-state.yaml:
     - timestamp: "{timestamp}"
       event: "feature_split"
       original_feature_id: "{feature_id}"
       split_into: [new feature IDs]
       split_rationale: "{rationale}"
       new_features_added: {count}

7. Display split notification:
   🔀 Feature Split Detected

   Original: {original_feature_name}
   Reason: {split_rationale}

   New features created:
   {FOR EACH new_feature}
     - {feature_name} ({effort_days} days)
   {END FOR}

   Updated plan: {total_features} features total

8. Re-sort features by priority

9. Continue with next pending feature
   (may be one of the newly created features if higher priority)
```

---

##### Status: "blocked" 🚧

```yaml
ACTIONS:
1. Extract blocking information:
   - blocked_by (list of issues)
   - proposed_prerequisite_feature
   - current_feature_plan_if_unblocked

2. Analyze blocking issue:
   FOR EACH blocking_issue:
     - type: prerequisite_work | architecture_decision | external_dependency
     - severity: critical | high | medium

3. Present to user:
   🚧 Feature Blocked

   Feature: {feature_name}
   Blocked by: {blocking_issue_description}

   Proposed solution: {proposed_prerequisite}

   Options:
   [A] Accept - Create prerequisite feature and re-sequence
   [R] Reject - Mark current feature blocked, continue to next
   [M] Manual - Manually define prerequisite
   [D] Details - View full handoff file

4. Process user choice:

   IF Accept:
     a. Create prerequisite feature in manifest:
        NEW FEATURE:
          feature_id: "feature-{next_id}"
          feature_name: "{proposed_prerequisite_name}"
          status: "pending"
          priority: {current_feature_priority - 1}  # Higher priority
          scope: "{proposed_prerequisite_scope}"

     b. Update current feature:
        UPDATE features[current]:
          status: "blocked"
          blocked_by: [prerequisite feature ID]

     c. Add dependency:
        UPDATE features[current].dependencies:
          ADD: feature_id: "{prerequisite_id}", type: "requires"

     d. Re-sort features (prerequisite now before current)

     e. Continue with prerequisite feature next

   IF Reject:
     a. Update current feature:
        UPDATE features[current]:
          status: "blocked"
          blocked_reason: "{user_rejected_prerequisite}"

     b. Mark as needing manual resolution

     c. Continue to next pending feature

   IF Manual:
     a. Prompt user for prerequisite details
     b. Create prerequisite feature from user input
     c. Same as Accept path

5. Update state:
   APPEND TO orchestrator-state.yaml:
     - timestamp: "{timestamp}"
       event: "feature_blocked"
       feature_id: "{feature_id}"
       blocking_issue: "{issue}"
       resolution: "{user_choice}"

6. Display status:
   ✓ Blocking issue processed

   {IF prerequisite created}
   Prerequisite feature created: {prerequisite_name}
   Will plan this feature next
   {ELSE}
   Feature marked as blocked, continuing with others
   {END IF}

   Progress: {completed}/{total - blocked} plannable features

7. Continue loop
```

---

#### 2.5 Update Current Feature Pointer

```yaml
AFTER PROCESSING HANDOFF:

UPDATE orchestrator-state.yaml:
  current_feature_id: "{next_pending_feature_id}"
  next_feature_id: "{feature_after_next}"
```

---

#### 2.6 Check Loop Completion

```yaml
CHECK: Are there pending features remaining?

IF yes:
  - Display progress
  - Continue to next feature (goto 2.1)

IF no:
  - All features processed
  - Check if any blocked features remain
  - Display completion summary
  - Proceed to Step 3 (Consolidation)
```

---

### 3. Progress Display (Throughout Loop)

Display progress after each feature:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Feature Planning Progress
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Completed: {completed_count}/{total_count} ({percentage}%)

✓ {completed_feature_1} ({effort_days} days)
✓ {completed_feature_2} ({effort_days} days)
⏳ {current_feature} (in progress...)
⬜ {pending_feature_1}
⬜ {pending_feature_2}

Token Usage: {used}/{budget} ({percentage}%)
Time Elapsed: {minutes} minutes
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

### 4. Final Status Summary

When all features processed:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Feature Planning Complete!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Total Features: {total}
✓ Completed: {completed}
🔀 Split: {split}
🚧 Blocked: {blocked}
❌ Failed: {failed}

Total Effort: {sum_effort_days} days
Total Files: {sum_files} to modify/create
Token Usage: {used}/{budget}
Duration: {minutes} minutes

{IF blocked > 0}
⚠️ Warning: {blocked} features remain blocked
{END IF}

Proceeding to consolidation...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## ERROR HANDLING

### Error 1: Feature Agent Timeout

```yaml
SCENARIO: Agent exceeds 10 minutes

DETECTION: No handoff file after timeout

ACTIONS:
1. Send interrupt signal (if possible)

2. Check for partial handoff file

3. IF partial exists:
   - Load what agent completed
   - Mark as requires_split
   - Process as split scenario

4. IF no handoff:
   - Mark feature as "failed"
   - Prompt user:
       Feature {name} timed out (>10 minutes)

       [R] Retry with same scope
       [S] Split manually into smaller scopes
       [M] Provide manual plan
       [C] Skip this feature

5. Update manifest and state based on user choice

6. Continue to next feature
```

### Error 2: Invalid Handoff File

```yaml
SCENARIO: YAML parse fails or schema invalid

DETECTION: YAML parsing error or missing required fields

ACTIONS:
1. Log parse error

2. Attempt to read partial content

3. Prompt user:
   Feature {name} returned invalid handoff

   Error: {parse_error}

   [R] Retry feature (respawn agent)
   [F] Fix handoff manually (opens editor)
   [P] Proceed with partial data
   [S] Skip feature

4. Process based on user choice

5. IF multiple invalid handoffs:
   - May indicate template issue
   - Warn user to check template
```

### Error 3: Subprocess Crash

```yaml
SCENARIO: Subprocess exits with error code != 0

DETECTION: Exit code monitoring

ACTIONS:
1. Capture subprocess error output

2. Log to orchestrator-state.yaml

3. Prompt user:
   Feature {name} subprocess crashed

   Error: {error_message}
   Exit code: {code}

   [R] Retry
   [S] Skip
   [D] Debug (show logs)

4. Handle based on user choice

5. Continue to next feature
```

---

## SUCCESS CRITERIA

- [ ] All features in manifest processed (status != "pending")
- [ ] Each feature has handoff file
- [ ] Splits handled (new features added to manifest)
- [ ] Blocks handled (prerequisites created or features marked blocked)
- [ ] manifest.yaml updated with all status changes
- [ ] orchestrator-state.yaml execution_log complete
- [ ] Progress tracking accurate
- [ ] Token usage tracked
- [ ] Ready to proceed to Step 3 (Consolidation)

---

## TRANSITION TO STEP 3

When feature spawning complete:

```
✓ Step 2: Feature Spawning - COMPLETE

Features planned: {completed}/{total}
{IF blocked > 0}
  Blocked features: {blocked} (require manual resolution)
{END IF}

Handoff files: {session_dir}/feature-*-handoff.yaml
Manifest: {manifest_path}
State: {state_path}

Proceeding to Step 3: Consolidation...
```

**Handoff to Step 3**:
- All completed features have handoff files
- manifest.yaml shows completed status
- orchestrator-state.yaml has full execution log
- Step 3 will load all handoffs and aggregate into consolidated plan
