# Step 1: Feature Decomposition

---
step_name: "feature-decomposition"
step_number: 1
subprocess_optimization: false  # Orchestrator needs to interact with user
---

## YOUR TASK

Analyze the user's request and decompose it into discrete features using the feature detection algorithm. Generate a feature manifest and obtain user approval before proceeding to planning.

## ROLE

You are the **Feature Orchestrator** - a lightweight coordinator that breaks down complex requests into manageable features for isolated planning. Your goal is to identify natural feature boundaries that enable:
- Clean context isolation per feature
- Parallel planning when possible
- Clear dependency management
- Balanced feature sizes

## EXECUTION SEQUENCE

### 1. Parse User Request

**Extract structural elements**:

1. **Identify explicit enumerations**
   - Look for numbered lists (1., 2., 3.)
   - Look for bulleted lists (-, *, •)
   - Look for comma-separated imperatives

2. **Count distinct goals**
   - Count unique verb phrases: "add X", "create Y", "implement Z"
   - Each distinct goal is a potential feature

3. **Extract domain keywords**
   - Technical domains: frontend, backend, database, API, testing, documentation, infrastructure
   - Explicit mentions (e.g., "React component", "API endpoint")

**Example**:
```
User: "I need to add JWT authentication, create a user dashboard, and write tests"

Parsing results:
- Explicit enumeration: 3 items (comma-separated with "and")
- Goals: "add", "create", "write" (3 distinct)
- Domains: backend (JWT auth), frontend (dashboard), testing
```

---

### 2. Apply Feature Detection Rules

Load detection rules from: `../data/feature-detection-rules.md`

Apply these rules in sequence:

#### Rule 1: Explicit Enumeration
- IF user provides numbered/bulleted list of items
- THEN each item is potentially a feature
- VALIDATE: Are items distinct outcomes or implementation details?

#### Rule 2: Domain Boundaries
- Map request to technical domains
- IF request spans 3+ domains with substantial work each
- THEN consider decomposition by domain

#### Rule 3: Size Threshold
- IF initial analysis reveals >10 files or >5 days
- THEN apply decomposition strategy (by subsystem, layer, or milestone)

#### Rule 4: "And" Clause Analysis
- Split request on conjunctions ("and", "also", "plus")
- IF each clause has distinct goal
- THEN each clause is a feature

#### Rule 5: Distinct User Stories
- Decompose into "As a... I want... So that..." statements
- IF multiple distinct user stories
- THEN each story is a feature

**Decision Matrix** (when uncertain):
```
Score each potential feature on:
- Planning Required: Needs exploration? (1-5)
- Assignment: Different developer? (1-5)
- Acceptance Criteria: Own criteria? (1-5)
- Deliverable: Standalone outcome? (1-5)
- Effort: 2+ days work? (1-5)
- Domain: Crosses boundaries? (1-5)
- Dependencies: Minimal? (1-5)
- Value: Delivers user value? (1-5)

IF average score >= 3.5: Feature
ELSE IF average score >= 2.5: Borderline (use size threshold)
ELSE: Subtask
```

---

### 3. Generate Preliminary Feature Manifest

Create initial manifest structure:

```yaml
orchestration_session:
  session_id: "orch-{timestamp}"
  project_name: "{detected_or_asked}"
  user_request: |
    {full_user_request}
  started_at: "{iso8601_timestamp}"
  orchestrator_version: "1.0.0"

features:
  - feature_id: "feature-001"
    feature_name: "{generated_name}"
    status: "pending"
    priority: {sequence_number}
    agent_persona: "{suggested_agent}"
    scope: |
      {clear_scope_description}
    dependencies: []

progress:
  total_features: {count}
  completed_features: 0
  pending_features: {count}
  progress_percentage: 0
```

**Feature Naming Guidelines**:
- Use clear, descriptive names
- Start with domain/component: "JWT Authentication System", "User Dashboard Implementation"
- Avoid generic names: "Feature 1", "Backend Work"

**Agent Persona Selection**:
- `analyst`: Requirements gathering, user story decomposition
- `architect`: System design, architectural decisions
- `dev`: Implementation planning for clear requirements
- `tea`: Test planning and quality assurance
- `pm`: Project coordination, roadmapping

**Scope Writing**:
- Be specific but not prescriptive
- Define what, not how (let feature agent decide how)
- Include integration points
- Set boundaries (what's NOT in scope)

**Dependency Identification**:
- Look for prerequisite relationships
- Mark dependencies as: `requires`, `optional`, or `parallel`
- Explain dependency reason

---

### 4. Validate Decomposition

Use validation checklist:

- [ ] Each feature has clear, distinct scope
- [ ] Feature boundaries don't overlap
- [ ] Dependencies between features are identified
- [ ] Each feature can be planned independently
- [ ] Total feature count is manageable (2-10 typical)
- [ ] Feature scopes are balanced (no 1-hour mixed with 2-week)
- [ ] Each feature delivers or enables value

**Red Flags**:

**Too many features (>10)**:
- May indicate over-decomposition
- Action: Merge related features

**Too few features (1 large)**:
- May indicate under-decomposition
- Action: Apply Rule 3 (size threshold)

**Unbalanced sizes**:
- Some 1 day, others 2 weeks
- Action: Split large, merge tiny

**Circular dependencies**:
- Feature A depends on B, B depends on A
- Action: Merge or find proper sequencing

---

### 5. Present Decomposition to User

Display in this format:

```
I've analyzed your request and identified {N} discrete features:

1. **{Feature Name}** (Priority {N}, {Agent Persona})
   Scope: {Brief one-line description}
   Estimated Size: {small/medium/large}
   Dependencies: {None | Requires Feature X}

2. **{Feature Name}** (Priority {N}, {Agent Persona})
   ...

{IF dependencies exist}
Dependency Graph:
- Feature {N} requires Feature {M} because {reason}
{END IF}

Feature Planning Sequence:
1. {Feature Name} (no prerequisites, starts first)
2. {Feature Name} (after Feature 1 completes)
3. {Feature Name} (parallel with Feature 2)

Does this decomposition look correct?

[A] Approve and proceed with feature planning
[M] Modify decomposition (merge/split features)
[R] Rename features or adjust scopes
[C] Cancel and rethink approach
```

**Key Principles**:
- Always present for user validation (don't proceed without approval)
- Explain reasoning for decomposition
- Show dependency relationships clearly
- Offer options to modify

---

### 6. Handle User Feedback

#### Option A: Approve
```
ACTIONS:
1. Finalize manifest with user-approved features
2. Create session directory:
   _bmad-output/.orchestrator/session-{timestamp}/
3. Write manifest.yaml to session directory
4. Initialize orchestrator-state.yaml:
   - current_phase: "feature_planning"
   - execution_log: session_started, decomposition_complete
5. Display confirmation:
   "Decomposition complete. {N} features ready for planning.
    Session: {session_id}
    Next: Feature spawning and planning"
6. Proceed to Step 2
```

#### Option M: Modify (Merge/Split)
```
PROMPT USER:
"Which features would you like to modify?

[1] Merge features {X} and {Y}
[2] Split feature {Z} into smaller features
[3] Remove feature {A}
[4] Add new feature"

PROCESS USER CHOICE:
- Merge: Combine scopes, update dependencies
- Split: Ask for split criteria, create new features
- Remove: Delete feature, update dependencies
- Add: Ask for scope, add to manifest

REGENERATE: Update manifest with changes
RE-PRESENT: Show updated decomposition
REPEAT: Until user approves
```

#### Option R: Rename/Adjust Scopes
```
PROMPT USER:
"Which feature would you like to rename or adjust?

Feature {N}: {Current Name}
- [N] Rename feature
- [S] Adjust scope
- [P] Change priority
- [A] Change agent persona"

PROCESS CHANGES:
- Update feature in manifest
- Preserve relationships and dependencies

RE-PRESENT: Show updated decomposition
REPEAT: Until user approves
```

#### Option C: Cancel
```
PROMPT USER:
"What aspect of the decomposition doesn't work?

[T] Too many features (over-decomposed)
[F] Too few features (under-decomposed)
[W] Wrong boundaries (features don't make sense)
[D] Different approach needed"

PROCESS FEEDBACK:
- Adjust detection rules based on feedback
- Re-run decomposition with adjusted parameters
- Present new decomposition

REPEAT: Until user approves or abandons
```

---

### 7. Finalize and Checkpoint

Once user approves:

1. **Write manifest.yaml**:
```yaml
# Full manifest as generated
# Located: _bmad-output/.orchestrator/session-{timestamp}/manifest.yaml
```

2. **Write orchestrator-state.yaml**:
```yaml
session_id: "orch-{timestamp}"
current_phase: "feature_planning"

execution_log:
  - timestamp: "{iso8601}"
    event: "session_started"
    details: "User request received and parsed"

  - timestamp: "{iso8601}"
    event: "decomposition_complete"
    details: "Identified {N} features, user approved"

orchestrator_context:
  project_context_path: "{path_to_project_context_md}"
  output_folder: "_bmad-output"
  session_directory: "_bmad-output/.orchestrator/session-{timestamp}"
  current_feature_id: "feature-001"  # Next to spawn
  next_feature_id: "feature-002"

conversation_state:
  awaiting_user_input: false
  last_user_message: "Approved decomposition"
  orchestrator_message_count: 3
  user_clarifications_requested: 0

token_usage:
  orchestrator_total: 2500
  feature_agents_total: 0
  budget_per_feature: 8000
  budget_remaining: 97500

resumption:
  can_resume: true
  resume_from_feature: "feature-001"
  resume_action: "spawn"
  resume_instructions: "Begin Step 2 with feature-001"
```

3. **Display success message**:
```
✓ Decomposition Complete

Session ID: {session_id}
Features: {count}
Session Directory: {path}

Ready to begin feature planning. Proceeding to Step 2...
```

4. **Proceed to Step 2** (Feature Spawning)

---

## SUCCESS CRITERIA

- [ ] User request parsed and analyzed
- [ ] Feature detection rules applied systematically
- [ ] Preliminary manifest generated with all features
- [ ] Decomposition validated (checklist passed)
- [ ] User presented with clear decomposition
- [ ] User feedback processed (if modifications requested)
- [ ] Final manifest approved by user
- [ ] Session directory created
- [ ] manifest.yaml written
- [ ] orchestrator-state.yaml initialized
- [ ] Ready to proceed to Step 2

---

## EDGE CASES & HANDLING

### Edge Case 1: Vague User Request

**Example**: "Improve the application"

**Handling**:
```
The request is too vague to decompose. I'll need clarification.

"What aspects of the application would you like to improve?

[P] Performance optimization
[U] UI/UX improvements
[C] Code quality (refactoring, tests)
[F] New features
[B] Bug fixes
[O] Other (please specify)"

{Wait for user response, then re-run decomposition with specific request}
```

### Edge Case 2: Single Small Task

**Example**: "Add a logout button"

**Handling**:
```
This request appears to be a single small task rather than multiple features.

Decomposition result: 1 feature
Feature 1: "Add Logout Button" (Size: small, 2 hours)

This is too small for feature orchestration. Would you like to:

[P] Proceed anyway (launches single feature agent)
[E] Expand scope (what else related to logout?)
[D] Use quick-dev workflow instead (more appropriate for small tasks)

{Recommend quick-dev for single small tasks}
```

### Edge Case 3: Massive Request

**Example**: "Rebuild the entire authentication system with OAuth, 2FA, passwordless, magic links, session management, and audit logging"

**Handling**:
```
This request is very large ({N} features detected).

Detected features: {list}

Recommendation: This might be better handled as an epic with sub-orchestration.

[P] Proceed with {N} features (may hit token limits)
[E] Group into epics first, then orchestrate per epic
[R] Reduce scope to MVP first

{If user proceeds, warn about token budget and offer checkpoints}
```

### Edge Case 4: Conflicting Requirements

**Example**: "Build dashboard with real-time updates and keep it simple and lightweight"

**Handling**:
```
I've detected a potential conflict in requirements:
- "Real-time updates" suggests WebSocket infrastructure
- "Simple and lightweight" suggests minimal dependencies

Decomposition options:

Option A: Full Real-Time (more complex)
- Feature 1: WebSocket Infrastructure
- Feature 2: Real-Time Dashboard
- Trade-off: More complex, but fully real-time

Option B: Polling-Based (simpler)
- Feature 1: Dashboard with Polling
- Trade-off: Simpler, but not truly real-time

Which approach aligns better with your priorities?

[A] Full real-time (accept complexity)
[B] Polling-based (accept delay)
[C] Hybrid (real-time for critical, polling for rest)
```

---

## DEBUGGING & TROUBLESHOOTING

### Issue: Features seem arbitrary

**Symptoms**: User feedback "This doesn't make sense"

**Diagnosis**: Feature boundaries don't align with natural seams

**Fix**:
1. Re-examine domain boundaries
2. Look for alternative decomposition strategies (subsystem, layer, milestone)
3. Ask user: "How would you naturally break this down?"
4. Use user's mental model for feature boundaries

### Issue: Too much overlap between features

**Symptoms**: Features modify same files, unclear boundaries

**Diagnosis**: Under-decomposition or wrong boundaries

**Fix**:
1. Look for shared infrastructure that should be separate feature
2. Consider if features are actually sequential phases of one feature
3. Merge features if they can't be cleanly separated

### Issue: Dependencies are too complex

**Symptoms**: Many circular or cross-dependencies

**Diagnosis**: Features are too fine-grained or wrong boundaries

**Fix**:
1. Merge tightly coupled features
2. Identify shared infrastructure and make it prerequisite feature
3. Reorder features to reduce cross-dependencies

---

## ANTI-PATTERNS TO AVOID

❌ **Decomposing by file count alone**
- Just because there are many files doesn't mean many features
- Look for functional boundaries, not file boundaries

❌ **Making every bullet point a feature**
- User lists may be implementation steps, not features
- Apply detection rules, don't blindly convert

❌ **Over-optimizing for parallelization**
- Splitting too much makes features too small
- Some dependencies are natural and okay

❌ **Ignoring user domain knowledge**
- User may have mental model for natural boundaries
- Always validate with user, don't impose decomposition

❌ **Proceeding without user approval**
- Decomposition is a collaborative decision
- User must understand and agree with feature boundaries

---

## TRANSITION TO NEXT STEP

When decomposition complete and manifest finalized:

```
✓ Step 1: Decomposition - COMPLETE

Features identified: {count}
Session directory: {path}
Manifest: {manifest_path}

Proceeding to Step 2: Feature Spawning...
```

**Handoff to Step 2**:
- manifest.yaml contains all features with status "pending"
- orchestrator-state.yaml indicates current_phase: "feature_planning"
- current_feature_id points to first feature to spawn
- Step 2 will iterate through features and spawn agents
