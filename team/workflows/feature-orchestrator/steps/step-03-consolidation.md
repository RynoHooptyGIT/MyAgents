# Step 3: Plan Consolidation

---
step_name: "plan-consolidation"
step_number: 3
subprocess_optimization: false  # Orchestrator aggregates directly
---

## YOUR TASK

Aggregate all feature plans from handoff files into a single consolidated implementation plan. Identify cross-feature dependencies, sequence implementation order, calculate totals, and generate the final deliverable document.

## ROLE

You are the **Feature Orchestrator** in **aggregation mode**. Your responsibilities:
- Load all feature handoff files
- Aggregate plans without inflating context
- Identify cross-feature considerations
- Sequence features for implementation
- Calculate effort and complexity totals
- Generate consolidated-plan.md
- Maintain orchestrator context lightweight

---

## EXECUTION SEQUENCE

### 1. Load All Handoff Files

```yaml
READ: manifest.yaml

EXTRACT: All features with status "completed"

FOR EACH completed feature:
  handoff_path = session_dir + feature.handoff_file
  READ: handoff_path
  STORE: In aggregation structure (lightweight)

AGGREGATION_STRUCTURE:
  features:
    - feature_id
      feature_name
      effort_days
      files_to_modify_count
      files_to_create_count
      dependencies (internal + external)
      risks
      handoff_file_path  # Reference, don't copy full content
```

**Golden Rule**: Store references and metadata, not full handoff contents. This keeps orchestrator context lightweight even with 10+ features.

---

### 2. Analyze Cross-Feature Dependencies

```yaml
FOR EACH feature:
  FOR EACH other_feature:
    CHECK:
      - Do they modify the same files?
      - Do they have overlapping dependencies?
      - Does one's approach affect the other?
      - Are there shared architectural decisions?

IDENTIFY:
  - File conflicts (same file modified by multiple features)
  - Dependency conflicts (circular or incompatible)
  - Architectural conflicts (contradictory decisions)
  - Integration points (where features connect)

RECORD:
  cross_feature_considerations:
    - consideration_title
      affected_features: [list]
      description
      recommendation
```

---

### 3. Sequence Implementation Order

```yaml
BUILD DEPENDENCY GRAPH:
  nodes = features
  edges = dependencies

TOPOLOGICAL SORT:
  # Features with no dependencies first
  # Features depending on others after prerequisites

IDENTIFY PHASES:
  Phase 1: No dependencies (can start immediately)
  Phase 2: Depends only on Phase 1
  Phase 3: Depends on Phase 2 (or Phase 1 + Phase 2)
  ...

FOR EACH phase:
  - List features in phase
  - Calculate phase duration (max effort in phase if parallel, sum if sequential)
  - Identify phase prerequisites
  - Define phase deliverables

OUTPUT:
  implementation_sequence:
    phases:
      - phase_number
        phase_name
        duration_days
        features: [list]
        prerequisites: [list]
        deliverables: [list]
```

---

### 4. Calculate Totals

```yaml
EFFORT_TOTALS:
  total_days = SUM(feature.effort_days)
  backend_hours = SUM(feature.backend_hours)
  frontend_hours = SUM(feature.frontend_hours)
  testing_hours = SUM(feature.testing_hours)
  documentation_hours = SUM(feature.documentation_hours)
  total_hours = SUM(all_hours)

FILE_TOTALS:
  files_to_modify = UNIQUE(SUM(feature.files_to_modify))
  files_to_create = SUM(feature.files_to_create)
  # Check for conflicts (same file in multiple features)

DEPENDENCY_TOTALS:
  npm_packages = UNIQUE(SUM(feature.external_dependencies))
  config_changes = SUM(feature.configuration_changes)
  database_migrations = SUM(feature.database_migrations)

RISK_TOTALS:
  critical_risks = COUNT(risks WHERE severity == "critical")
  high_risks = COUNT(risks WHERE severity == "high")
  medium_risks = COUNT(risks WHERE severity == "medium")

TOKEN_TOTALS:
  orchestrator_tokens = orchestrator_state.token_usage.orchestrator_total
  feature_agents_tokens = orchestrator_state.token_usage.feature_agents_total
  total_tokens = orchestrator_tokens + feature_agents_tokens
  avg_per_feature = feature_agents_tokens / completed_features_count
```

---

### 5. Generate Consolidated Plan Document

```yaml
USE TEMPLATE: ../templates/consolidated-plan-template.md

POPULATE:
  - Executive summary (request, features, totals)
  - Feature breakdown (FOR EACH completed feature)
  - Implementation sequence (phases)
  - Cross-feature considerations
  - File manifest
  - Risk register
  - Architectural decisions
  - External dependencies
  - Configuration requirements
  - Database migrations
  - Testing strategy
  - Effort breakdown
  - Token usage report
  - Next steps
  - Session metadata
  - Appendix (agent findings)

WRITE TO: session_dir/consolidated-plan.md
```

**Template Population Strategy**:
- Read template
- Replace {placeholder} variables
- FOR EACH loops for repeating sections
- Conditional sections (IF/ELSE) based on data
- Keep formatting clean and scannable

---

### 6. Validate Consolidated Plan

```yaml
VALIDATION CHECKLIST:
  - [ ] All completed features included
  - [ ] Implementation sequence is valid (no circular deps)
  - [ ] Totals are accurate (spot check)
  - [ ] File conflicts identified and addressed
  - [ ] Risk register includes all high+ risks
  - [ ] External dependencies listed
  - [ ] Next steps are actionable
  - [ ] Document is readable (not raw data dump)

IF validation fails:
  - Fix issues
  - Regenerate document
```

---

### 7. Display Summary

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Consolidated Plan Generated
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Plan: {session_dir}/consolidated-plan.md

Summary:
- Features: {completed_count}
- Total Effort: {total_days} days
- Files: {files_count} to modify/create
- Phases: {phase_count}
- Risks: {critical} critical, {high} high

Implementation Sequence:
  Phase 1: {feature_names} ({days} days)
  Phase 2: {feature_names} ({days} days)
  ...

{IF blocked_features > 0}
⚠️ Note: {blocked_features} blocked features not included
{END IF}

Ready to proceed to implementation planning...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

### 8. Update State

```yaml
UPDATE orchestrator-state.yaml:
  current_phase: "consolidation"

  APPEND execution_log:
    - timestamp: "{timestamp}"
      event: "consolidation_started"

    - timestamp: "{timestamp}"
      event: "consolidated_plan_generated"
      output_file: "consolidated-plan.md"
      features_included: {count}
      total_effort_days: {days}
```

---

## CONSOLIDATION STRATEGIES

### Strategy 1: File Conflict Resolution

```yaml
IF multiple features modify same file:

  CONFLICT_RESOLUTION:
    Option A: Sequential (default)
      - Feature 1 modifies file
      - Feature 2 modifies file after Feature 1
      - Document in implementation sequence

    Option B: Merge modifications
      - Combine changes from both features
      - Create single modification plan
      - May require re-planning

    Option C: Split file
      - If file is too large
      - Refactor into multiple files
      - Each feature modifies different file

  RECOMMENDATION: Use Option A (sequential) unless conflicts are severe
```

### Strategy 2: Dependency Ordering

```yaml
DEPENDENCY RULES:

  1. Prerequisites before dependents
     IF Feature B requires Feature A:
       Sequence: A → B

  2. Infrastructure before features
     IF Feature is infrastructure/foundation:
       Place in Phase 1

  3. Testing after implementation
     IF Feature is test suite:
       Place in final phase

  4. Parallel when independent
     IF Features have no shared dependencies:
       Same phase (can be parallel)
```

### Strategy 3: Effort Balancing

```yaml
WHEN SEQUENCING:

  Goal: Balance phase sizes for steady progress

  IF Phase has 1 large + 3 small features:
    - Large feature may delay phase
    - Consider: Split large feature

  IF Phase has many small features:
    - May be too fragmented
    - Consider: Group related small features

  IDEAL: Each phase 3-5 days of work (single feature or 2-3 small)
```

---

## CONSOLIDATION OUTPUT FORMAT

### Consolidated Plan Structure

```markdown
# Consolidated Implementation Plan

## Executive Summary
- Original request
- Features identified
- Total effort
- File counts
- Implementation sequence

## Feature Breakdown
FOR EACH feature:
  - Scope
  - Approach
  - Files
  - Dependencies
  - Risks

## Implementation Sequence
FOR EACH phase:
  - Features in phase
  - Duration
  - Prerequisites
  - Deliverables

## Cross-Feature Considerations
- Integration points
- Shared concerns
- Recommendations

## File Manifest
- All files to modify
- All files to create
- Conflicts noted

## Risk Register
- Critical risks
- High risks
- Mitigations

## [Additional sections...]
```

---

## SUCCESS CRITERIA

- [ ] All completed feature handoffs loaded
- [ ] Cross-feature dependencies analyzed
- [ ] Implementation sequence determined (valid topological order)
- [ ] Totals calculated (effort, files, dependencies, risks)
- [ ] consolidated-plan.md generated
- [ ] Document validated (readable, accurate, complete)
- [ ] orchestrator-state.yaml updated
- [ ] Ready to proceed to Step 4 (Next Actions)

---

## TRANSITION TO STEP 4

```
✓ Step 3: Consolidation - COMPLETE

Consolidated Plan: {path}

Features: {count}
Effort: {days} days
Phases: {count}

Proceeding to Step 4: Next Actions...
```

**Handoff to Step 4**:
- consolidated-plan.md contains complete plan
- orchestrator-state.yaml updated
- Step 4 will recommend next workflow and offer to spawn implementation
