# Feature Detection Rules

This document defines the algorithm for identifying discrete features within a user request. The orchestrator uses these rules to decompose complex requests into manageable feature scopes that can be planned by isolated agents.

## Core Principle

**Feature**: A discrete, self-contained unit of work that:
- Has its own planning scope (requires exploration/discovery)
- Touches a distinct domain or subsystem
- Could be parallelized with other features (minimal dependencies)
- Produces a deliverable plan/specification
- Typically represents 2+ days of implementation work

**Subtask**: A component of feature implementation:
- Part of feature execution
- Single logical unit within feature context
- Depends on feature scope
- Typically represents 2-8 hours of work

---

## Detection Algorithm

### Phase 1: Initial Parse

Extract structural elements from user request:

1. **Identify explicit enumerations**
   - Numbered lists (1., 2., 3.)
   - Bulleted lists (-, *, •)
   - Comma-separated items in imperative sentences

2. **Count distinct goals/outcomes**
   - Look for multiple verb phrases: "add X", "create Y", "implement Z"
   - Each distinct goal is a potential feature

3. **Extract domain keywords**
   - Technical domains: frontend, backend, database, API, testing, documentation, infrastructure, deployment
   - Look for these explicitly or implicitly (e.g., "React component" → frontend)

### Phase 2: Apply Detection Rules

Apply these rules in order. A request may trigger multiple rules.

#### Rule 1: Explicit Enumeration

```yaml
TRIGGER:
  User provides numbered or bulleted list of items

LOGIC:
  FOR EACH item in list:
    IF item describes distinct outcome:
      → Potential feature
    ELSE IF item describes implementation detail:
      → Subtask of parent feature

EXAMPLES:
  Input: "I need to: 1. Add authentication, 2. Create dashboard, 3. Write tests"
  Output: 3 features detected

  Input: "Add auth system with: 1. login endpoint, 2. logout endpoint, 3. token validation"
  Output: 1 feature (auth system) with 3 subtasks
```

**Decision Criteria**:
- If list items can be done by different developers independently → Features
- If list items are steps within single implementation → Subtasks

#### Rule 2: Domain Boundaries

```yaml
DOMAINS:
  - frontend (UI, components, pages, client-side logic)
  - backend (API, services, business logic, server-side)
  - database (schema, migrations, queries, data modeling)
  - infrastructure (deployment, hosting, CI/CD, monitoring)
  - testing (unit tests, integration tests, E2E tests)
  - documentation (README, API docs, architecture docs)

TRIGGER:
  Request spans 3+ distinct domains

LOGIC:
  Map request to domains
  Count domains crossed
  IF domains >= 3:
    Consider decomposition by domain

  FOR EACH domain:
    IF domain has substantial work (5+ files or 1+ day effort):
      → Feature per domain

EXAMPLES:
  Input: "Add user profile feature"
  Domains: frontend (profile page), backend (profile API), database (user fields)
  Output: Could be 1 feature or 3 features depending on size

  Input: "Build complete authentication system with UI, API, and tests"
  Domains: frontend (login form), backend (auth service), testing (test suite)
  Output: 3 features (crosses domains with substantial work in each)
```

**Decision Criteria**:
- 3+ domains with substantial work → Decompose by domain
- 2 domains with one being minimal → Single feature
- Single domain → Single feature

#### Rule 3: Size Threshold

```yaml
TRIGGER:
  Initial exploration reveals request is larger than expected

SIZE_INDICATORS:
  - 10+ files to modify/create
  - 3+ subsystems affected
  - Multiple architectural layers touched
  - Estimated effort > 5 days
  - Multiple distinct acceptance criteria

LOGIC:
  IF initial analysis reveals any size indicator:
    Apply decomposition strategy:

    OPTION A: By subsystem
      Identify subsystems involved
      Create feature per subsystem

    OPTION B: By layer
      Separate infrastructure, business logic, presentation
      Create feature per layer

    OPTION C: By milestone
      Identify MVP vs enhancements
      Create features representing incremental value

EXAMPLES:
  Input: "Refactor the authentication system"
  Analysis: Affects 15 files across auth service, middleware, routes, frontend components
  Output: 3 features - "Backend Auth Refactor", "Middleware Update", "Frontend Auth Integration"

  Input: "Add real-time notifications"
  Analysis: WebSocket infrastructure, backend events, frontend listener, database tables, testing
  Output: 4 features - "WebSocket Infrastructure", "Event System", "Notification UI", "Integration Tests"
```

**Decision Criteria**:
- If exploration reveals >5 days effort → Decompose
- If subsystems are independent → Decompose by subsystem
- If work is sequential → Consider phases/milestones instead

#### Rule 4: "And" Clause Analysis

```yaml
TRIGGER:
  Request contains conjunction words linking distinct goals

CONJUNCTIONS:
  - "and", "also", "plus", "additionally"
  - "as well as", "along with", "in addition to"
  - "then", "afterwards", "next"

LOGIC:
  Split request on conjunctions
  FOR EACH clause:
    IF clause has distinct goal with different outcome:
      → Feature
    ELSE IF clause adds constraint/detail to previous clause:
      → Subtask or constraint, not separate feature

EXAMPLES:
  Input: "Add authentication and create user dashboard"
  Output: 2 features (distinct goals with different outcomes)

  Input: "Add authentication using JWT and store tokens securely"
  Output: 1 feature (second clause is implementation detail of first)

  Input: "Build API endpoint and write comprehensive tests for it"
  Output: 2 features (API development + test suite are separable)
```

**Decision Criteria**:
- Conjunction links outcomes → Features
- Conjunction adds implementation detail → Subtask/constraint

#### Rule 5: Distinct User Stories

```yaml
TRIGGER:
  Request can be expressed as multiple "As a... I want... So that..." statements

LOGIC:
  Decompose request into user stories
  FOR EACH distinct user story:
    IF story has independent value:
      → Feature
    IF story is prerequisite for another:
      → Feature with dependency

EXAMPLES:
  Input: "Build user management system"
  User Stories:
    - "As an admin, I want to create users, so that I can manage access"
    - "As a user, I want to update my profile, so that my info is current"
    - "As an admin, I want to view audit logs, so that I can track changes"
  Output: 3 features (each delivers independent value)

  Input: "Add login functionality"
  User Stories:
    - "As a user, I want to log in with email/password, so that I can access the app"
  Output: 1 feature (single user story)
```

**Decision Criteria**:
- Multiple user stories with independent value → Features per story
- Single user story → Single feature
- User stories with dependencies → Features with dependency graph

---

## Feature vs. Subtask Decision Matrix

Use this matrix when uncertain whether something is a feature or subtask:

| Criteria | Feature | Subtask |
|----------|---------|---------|
| **Planning Required** | Needs exploration phase | Implementation straightforward |
| **Assignment** | Could go to different developer | Part of same developer's work |
| **Acceptance Criteria** | Has its own distinct criteria | Contributes to feature criteria |
| **Deliverable** | Produces standalone outcome | Part of larger deliverable |
| **Effort** | 2+ days work | 2-8 hours work |
| **Domain** | May cross domain boundaries | Within single domain |
| **Dependencies** | Minimal dependencies on other work | Depends on feature context |
| **Value** | Delivers user/stakeholder value | Technical implementation detail |

### Decision Algorithm

```
SCORE the potential feature on each criterion (1 = Subtask, 5 = Feature)

IF average score >= 3.5:
  → Feature
ELSE IF average score >= 2.5:
  → Borderline - use Rule 3 (size threshold) as tiebreaker
ELSE:
  → Subtask
```

---

## Handoff Detection (Mid-Flight Feature Splits)

During feature agent exploration, the agent may discover that scope is larger than expected. The agent should trigger a handoff back to the orchestrator in these scenarios:

### Trigger 1: Scope Expansion

```yaml
PATTERN:
  Agent discovers work is significantly larger than scoped

INDICATORS:
  - File count exceeds estimate by 2x
  - New subsystems discovered during exploration
  - Effort estimate increases from "medium" to "large"

AGENT_ACTION:
  1. Pause exploration
  2. Document what's been explored so far (partial plan)
  3. Set handoff status: requires_split: true
  4. Explain scope expansion in split_rationale
  5. Propose split (e.g., "Split into X and Y")

ORCHESTRATOR_ACTION:
  1. Read handoff file
  2. Update manifest with split features
  3. Use partial plan from original agent as context
  4. Spawn new agents for split features
```

### Trigger 2: Domain Crossing

```yaml
PATTERN:
  Agent realizes work crosses into unscoped domain

INDICATORS:
  - Frontend agent discovers backend changes needed
  - Backend agent discovers database migration required
  - Any agent discovers testing/infrastructure work not in scope

AGENT_ACTION:
  1. Complete planning for originally scoped domain
  2. Set handoff status: requires_split: true
  3. Document newly discovered domain work
  4. Propose: "Complete Feature X (current), create Feature Y (new domain)"

ORCHESTRATOR_ACTION:
  1. Accept current feature plan as-is
  2. Create new feature for cross-domain work
  3. Mark dependency (new feature may depend on current)
  4. Spawn new agent with appropriate persona for new domain
```

### Trigger 3: Dependency Discovery

```yaml
PATTERN:
  Agent finds prerequisite work not in original scope

INDICATORS:
  - "Before implementing X, we need to refactor Y"
  - "This requires Z infrastructure to be in place"
  - "Discovered technical debt that must be addressed first"

AGENT_ACTION:
  1. Document prerequisite work needed
  2. Set handoff status: blocked
  3. Specify blocking_reason and proposed prerequisite feature
  4. Provide plan for current feature assuming prerequisite complete

ORCHESTRATOR_ACTION:
  1. Create new feature for prerequisite work
  2. Add dependency: current feature depends_on prerequisite
  3. Re-sequence: prerequisite before current
  4. Spawn agent for prerequisite feature first
```

### Trigger 4: Architectural Decision Required

```yaml
PATTERN:
  Agent realizes architectural change needed that affects multiple features

INDICATORS:
  - "This requires refactoring core infrastructure"
  - "Should we use pattern X or pattern Y? (impacts other features)"
  - "This architectural decision affects features A, B, C"

AGENT_ACTION:
  1. Pause exploration
  2. Document architectural question/decision needed
  3. Set handoff status: requires_split: true
  4. Propose: "Create infrastructure feature for architecture work"

ORCHESTRATOR_ACTION:
  1. Create infrastructure/architecture feature
  2. Mark as prerequisite for current and related features
  3. May spawn architect persona agent for architecture feature
  4. Pause dependent features until architecture decided
```

---

## Decomposition Validation

After applying detection rules, validate the decomposition:

### Validation Checklist

- [ ] Each feature has clear, distinct scope
- [ ] Feature boundaries don't overlap
- [ ] Dependencies between features are identified
- [ ] Each feature can be planned independently
- [ ] Total feature count is manageable (2-10 features typical)
- [ ] Feature scopes are balanced (no 1-hour features mixed with 2-week features)
- [ ] Each feature delivers value or enables value

### Red Flags

**Too many features** (>10):
- May indicate over-decomposition
- Consider: Are some features actually subtasks?
- Action: Merge related features

**Too few features** (1 large feature):
- May indicate under-decomposition
- Consider: Does feature cross domains? Exceed 5 days effort?
- Action: Apply Rule 3 (size threshold)

**Unbalanced feature sizes**:
- Some features 1 day, others 2 weeks
- Consider: Should large feature be split?
- Action: Split large features, merge tiny features

**Circular dependencies**:
- Feature A depends on B, B depends on A
- Consider: Are these really one feature?
- Action: Merge or find proper sequencing

---

## Example Decompositions

### Example 1: Simple Request

**User Request**: "Add a logout button to the navigation bar"

**Analysis**:
- Rule 1: No enumeration
- Rule 2: Single domain (frontend)
- Rule 3: Size small (1 file, 1 hour)
- Rule 4: No conjunctions
- Rule 5: Single user story

**Result**: **1 feature** (too small to decompose)

---

### Example 2: Multi-Domain Request

**User Request**: "Build a user authentication system with login, signup, and password reset"

**Analysis**:
- Rule 1: Enumeration of 3 functions (login, signup, reset) - but all part of "authentication system"
- Rule 2: Multiple domains (frontend forms, backend API, database, email service, testing)
- Rule 3: Size large (15+ files, 7+ days)
- Rule 4: "with" indicates components of single system
- Rule 5: User story: "As a user, I want to authenticate..."

**Initial Assessment**: Could be 1 feature or multiple

**Apply Rule 3 (size threshold)**: 7+ days triggers decomposition

**Decomposition Strategy**: By layer + functionality

**Result**: **4 features**
1. "Authentication Backend Service" (API endpoints, token management, password hashing)
2. "Authentication Frontend UI" (login/signup/reset forms, auth state)
3. "Password Reset Email Service" (email templates, token generation, background jobs)
4. "Authentication Test Suite" (unit, integration, E2E tests)

**Dependencies**: Features 2 and 3 depend on Feature 1

---

### Example 3: Explicit Multi-Feature Request

**User Request**: "I need to add JWT authentication, create a user dashboard showing activity, and write comprehensive tests for both"

**Analysis**:
- Rule 1: Explicit enumeration with "and" conjunctions
- Rule 2: Multiple domains (backend auth, frontend dashboard, testing)
- Rule 4: "and" conjunctions link distinct goals
- Rule 5: Multiple user stories (auth, dashboard, quality assurance)

**Result**: **3 features**
1. "JWT Authentication System" (backend, prerequisite)
2. "User Activity Dashboard" (frontend, depends on F1)
3. "Comprehensive Test Suite" (testing, depends on F1 & F2)

**Dependencies**: Clear sequential dependencies

---

### Example 4: Ambiguous Request (Requires Clarification)

**User Request**: "Improve the application"

**Analysis**:
- Too vague to apply detection rules
- Could mean: performance, UI/UX, code quality, features, bugs

**Orchestrator Action**:
1. Ask user for clarification:
   - "What aspect would you like to improve? (performance, UI/UX, code quality, features)"
   - "Are there specific areas or goals for improvement?"

2. Once clarified, apply detection rules to specific request

**Lesson**: Detection algorithm requires sufficient specificity. Always clarify vague requests before decomposition.

---

## Integration with Orchestrator Workflow

The feature detection rules are invoked in **Step 1: Decomposition** of the orchestrator workflow.

**Workflow**:
1. Parse user request (Phase 1 of detection algorithm)
2. Apply detection rules (Phase 2)
3. Generate preliminary feature manifest
4. Validate decomposition (validation checklist)
5. Present to user for approval
6. Handle user feedback (merge/split features)
7. Finalize manifest
8. Proceed to Step 2 (Feature Spawning)

**User Interaction**:
- Always present decomposition to user before proceeding
- User can request merge (if over-decomposed)
- User can request split (if under-decomposed)
- User can rename features or clarify scopes
- User approval required before spawning agents
