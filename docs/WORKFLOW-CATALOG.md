# My Dev Team — Workflow Catalog

All workflows organized by phase and domain. Each entry includes the workflow name, purpose, key inputs and outputs, and the slash command path for Claude Code invocation.

---

## Phase 1: Analysis

### create-product-brief

- **Purpose**: Create a comprehensive product brief through collaborative step-by-step discovery, working with the user as a creative business analyst peer.
- **Inputs**: User's product idea, market knowledge, vision
- **Outputs**: Product brief document in `output/planning-artifacts/`
- **Slash command**: `/team:create-product-brief`

### research

- **Purpose**: Conduct comprehensive research across multiple domains using current web data and verified sources. Supports market research, technical research, and domain research modes.
- **Inputs**: Research topic, domain selection (market/technical/domain)
- **Outputs**: Research report document in `output/planning-artifacts/`
- **Slash command**: `/team:research`

---

## Phase 2: Planning

### prd

- **Purpose**: Tri-modal PRD workflow -- Create, Validate, or Edit comprehensive Product Requirements Documents through collaborative discovery.
- **Inputs**: Product brief (create mode), existing PRD (validate/edit mode)
- **Outputs**: PRD document in `output/planning-artifacts/`
- **Slash command**: `/team:prd`

### create-ux-design

- **Purpose**: Work with a peer UX Design expert to plan your application's UX patterns, look and feel, through a 14-step collaborative process.
- **Inputs**: PRD, product brief, any existing design references
- **Outputs**: UX design document in `output/planning-artifacts/`
- **Slash command**: `/team:create-ux-design`

---

## Phase 3: Solutioning

### create-architecture

- **Purpose**: Collaborative architectural decision facilitation that produces a decision-focused architecture document optimized for preventing AI agent conflicts during implementation.
- **Inputs**: PRD, product brief, UX design (if applicable)
- **Outputs**: Architecture document in `output/planning-artifacts/`
- **Slash command**: `/team:create-architecture`

### create-epics-and-stories

- **Purpose**: Transform PRD requirements and architecture decisions into comprehensive epics and user stories organized by user value, with detailed acceptance criteria for development teams.
- **Inputs**: Completed PRD + Architecture documents (UX recommended if UI exists)
- **Outputs**: Epics and stories document in `output/planning-artifacts/`
- **Slash command**: `/team:create-epics-and-stories`

### check-implementation-readiness

- **Purpose**: Critical validation workflow that assesses PRD, Architecture, and Epics for completeness and alignment before implementation using an adversarial review approach.
- **Inputs**: PRD, Architecture, Epics documents
- **Outputs**: Readiness report with pass/fail assessment and gap details
- **Slash command**: `/team:check-implementation-readiness`

---

## Phase 4: Implementation

### create-story

- **Purpose**: Create the next user story file from epics with enhanced context analysis and direct ready-for-dev marking.
- **Inputs**: Epics document, sprint-status.yaml, target story identifier
- **Outputs**: Story file in `output/implementation-artifacts/stories/`, sprint-status.yaml updated
- **Slash command**: `/team:create-story`

### dev-story

- **Purpose**: Execute a story by implementing tasks/subtasks, writing tests, validating against acceptance criteria, and updating the story file. Enforces engineering discipline gates at every critical checkpoint: TDD (failing test before code), verification (fresh evidence for all completion claims), and debugging (hypothesis-first, escalate at 3 failures).
- **Inputs**: Story file, project-context.md, codebase
- **Outputs**: Implemented code, tests, updated story file with task completion markers, discipline compliance checklist
- **Slash command**: `/team:dev-story`

### code-review

- **Purpose**: Perform an adversarial Senior Developer code review that finds 3-10 specific problems in every story. Challenges code quality, test coverage, architecture compliance, security, and performance. Can auto-fix with user approval. Enforces receiving review discipline — all findings read before implementing any, grouped by severity, no performative agreement.
- **Inputs**: Implemented story, story file, project-context.md
- **Outputs**: Review findings, applied fixes, story status updated to `done` when passing
- **Slash command**: `/team:code-review`

### sprint-planning

- **Purpose**: Generate and manage the sprint status tracking file, extracting all epics and stories from epic files and tracking status through the development lifecycle.
- **Inputs**: Epics documents in planning-artifacts
- **Outputs**: `sprint-status.yaml` in `output/implementation-artifacts/`
- **Slash command**: `/team:sprint-planning`

### sprint-status

- **Purpose**: Summarize sprint-status.yaml, surface risks, and route to the right implementation workflow.
- **Inputs**: sprint-status.yaml
- **Outputs**: Sprint summary with risk assessment and next-action recommendation
- **Slash command**: `/team:sprint-status`

### epic-consistency-check

- **Purpose**: Proactive cross-epic consistency audit that detects story overlap, file conflicts, backend/frontend sync gaps, and cross-epic contradictions.
- **Inputs**: All epic files, sprint-status.yaml
- **Outputs**: Consistency report with findings
- **Slash command**: `/team:epic-consistency-check`

### correct-course

- **Purpose**: Navigate significant changes during sprint execution by analyzing impact, proposing solutions, and routing for implementation.
- **Inputs**: Description of change, sprint-status.yaml, affected stories
- **Outputs**: Impact analysis and corrective action plan
- **Slash command**: `/team:correct-course`

### retrospective

- **Purpose**: Run after epic completion to review overall success, extract lessons learned, and explore if new information emerged that might impact the next epic.
- **Inputs**: Completed epic, sprint-status.yaml
- **Outputs**: Retrospective summary with lessons learned
- **Slash command**: `/team:retrospective`

---

## Quick Flow

### quick-dev

- **Purpose**: Flexible development -- execute tech specs or direct instructions with optional planning. Minimum ceremony for small tasks.
- **Inputs**: Tech spec file or direct instructions
- **Outputs**: Implemented code with self-check and adversarial review
- **Slash command**: `/team:quick-dev`

### quick-spec

- **Purpose**: Conversational spec engineering -- ask questions, investigate code, produce an implementation-ready tech spec.
- **Inputs**: Feature description, codebase access
- **Outputs**: Tech spec document
- **Slash command**: `/team:quick-spec`

---

## DevOps

### ship

- **Purpose**: Commit changes, push to remote branch, and create a pull request with proper description and labels. Includes a verification evidence gate — fresh test output must exist in the current session before shipping. Can be overridden with `[DISCIPLINE-OVERRIDE]` logging.
- **Inputs**: Completed and reviewed story, branch state
- **Outputs**: Git commit, remote push, GitHub PR
- **Slash command**: `/team:ship`

### commit

- **Purpose**: Create a well-structured git commit with conventional commit message format.
- **Inputs**: Staged changes, story context
- **Outputs**: Git commit
- **Slash command**: `/team:commit`

### branch-cleanup

- **Purpose**: Clean up merged and stale git branches from local and remote repositories.
- **Inputs**: Git repository state
- **Outputs**: Deleted merged/stale branches
- **Slash command**: `/team:branch-cleanup`

### docker-review

- **Purpose**: Review Docker configuration files for best practices, security, layer optimization, and multi-stage build patterns.
- **Inputs**: Dockerfiles, docker-compose files
- **Outputs**: Review findings with recommendations

### environment-config

- **Purpose**: Review and manage environment configuration, secrets management, and deployment variables.
- **Inputs**: Environment files, deployment config
- **Outputs**: Configuration review and recommendations

### cicd-pipeline

- **Purpose**: Design or review CI/CD pipeline configuration for best practices, efficiency, and reliability.
- **Inputs**: CI/CD config files (GitHub Actions, GitLab CI, etc.)
- **Outputs**: Pipeline review or scaffold

---

## Testing (Test Architect)

### testarch-atdd

- **Purpose**: Generate failing acceptance tests before implementation using TDD red-green-refactor cycle.
- **Inputs**: Story file with acceptance criteria
- **Outputs**: Acceptance test files with ATDD checklist
- **Slash command**: `/team:testarch-atdd`

### testarch-automate

- **Purpose**: Expand test automation coverage after implementation, or analyze existing codebase to generate a comprehensive test suite.
- **Inputs**: Implemented code, existing test files
- **Outputs**: New automated test files
- **Slash command**: `/team:testarch-automate`

### testarch-ci

- **Purpose**: Scaffold CI/CD quality pipeline with test execution, burn-in loops, and artifact collection.
- **Inputs**: Test framework config, CI platform choice
- **Outputs**: CI pipeline config file (GitHub Actions or GitLab CI template)
- **Slash command**: `/team:testarch-ci`

### testarch-framework

- **Purpose**: Initialize production-ready test framework architecture (Playwright or Cypress) with fixtures, helpers, and configuration.
- **Inputs**: Framework choice, project structure
- **Outputs**: Test framework scaffold with config, fixtures, and helpers
- **Slash command**: `/team:testarch-framework`

### testarch-nfr

- **Purpose**: Assess non-functional requirements (performance, security, reliability, maintainability) before release with evidence-based validation.
- **Inputs**: NFR criteria, system under test
- **Outputs**: NFR assessment report
- **Slash command**: `/team:testarch-nfr`

### testarch-test-design

- **Purpose**: Dual-mode workflow: (1) System-level testability review in Solutioning phase, or (2) Epic-level test planning in Implementation phase. Auto-detects mode based on project phase.
- **Inputs**: Architecture doc or epic/story files
- **Outputs**: Test design document
- **Slash command**: `/team:testarch-test-design`

### testarch-test-review

- **Purpose**: Review test quality using comprehensive knowledge base and best practices validation.
- **Inputs**: Existing test files
- **Outputs**: Test review report with quality assessment
- **Slash command**: `/team:testarch-test-review`

### testarch-trace

- **Purpose**: Generate requirements-to-tests traceability matrix, analyze coverage, and make quality gate decision (PASS/CONCERNS/FAIL/WAIVED).
- **Inputs**: Requirements (stories/PRD), test files
- **Outputs**: Traceability matrix with quality gate verdict
- **Slash command**: `/team:testarch-trace`

---

## Data

### cache-strategy

- **Purpose**: Design or review caching strategy for database queries, API responses, and session data.
- **Inputs**: Data access patterns, current caching config
- **Outputs**: Caching strategy recommendations

### data-model-review

- **Purpose**: Review database models for normalization, indexing, relationships, and multi-tenant patterns.
- **Inputs**: Database model files
- **Outputs**: Data model review findings

### migration-review

- **Purpose**: Review database migration files for safety, reversibility, and data integrity.
- **Inputs**: Migration files
- **Outputs**: Migration review report

### query-optimization

- **Purpose**: Analyze and optimize database queries for performance using EXPLAIN ANALYZE and index recommendations.
- **Inputs**: Slow queries, database schema
- **Outputs**: Optimized queries with index recommendations

---

## API Contract

### contract-drift

- **Purpose**: Detect drift between OpenAPI specification and actual API implementation (backend routers and frontend services).
- **Inputs**: OpenAPI spec, router files, frontend API service files
- **Outputs**: Drift report with specific endpoint discrepancies

### gap-analysis

- **Purpose**: Identify missing API endpoints, undocumented routes, and coverage gaps between spec and implementation.
- **Inputs**: OpenAPI spec, router files
- **Outputs**: Gap analysis report

### schema-comparison

- **Purpose**: Compare API schemas across versions or between spec and implementation for breaking changes.
- **Inputs**: Two schema versions or spec vs. implementation
- **Outputs**: Schema comparison report with breaking change identification

---

## Security

### security-audit

- **Purpose**: Perform a comprehensive application security audit covering OWASP Top 10, authentication, authorization, and data protection.
- **Inputs**: Application code, configuration files
- **Outputs**: Security audit report with severity-ranked findings

### vulnerability-scan

- **Purpose**: Scan codebase for known vulnerability patterns, insecure dependencies, and common security anti-patterns.
- **Inputs**: Codebase, dependency files
- **Outputs**: Vulnerability report

### rls-review

- **Purpose**: Review Row Level Security policies for completeness, correctness, and multi-tenant data isolation.
- **Inputs**: RLS policy files, database models
- **Outputs**: RLS review report

### hipaa-check

- **Purpose**: Check application for HIPAA technical safeguard compliance including PHI handling, audit logging, and access controls.
- **Inputs**: Application code, data flow documentation
- **Outputs**: HIPAA compliance checklist with findings

---

## NIST RMF

### compliance-check

- **Purpose**: Check application against NIST AI Risk Management Framework requirements across GOVERN, MAP, MEASURE, and MANAGE functions.
- **Inputs**: Application documentation, AI feature descriptions
- **Outputs**: NIST RMF compliance report

### risk-assessment

- **Purpose**: Assess AI system risks using NIST RMF methodology with risk classification and mitigation recommendations.
- **Inputs**: AI system description, risk factors
- **Outputs**: Risk assessment report

### trustworthiness-analysis

- **Purpose**: Analyze AI system against NIST trustworthiness characteristics: valid/reliable, safe, secure/resilient, accountable/transparent, explainable/interpretable, privacy-enhanced, fair with harmful bias managed.
- **Inputs**: AI system documentation
- **Outputs**: Trustworthiness analysis report

---

## AI/ML

### ai-decision-framework

- **Purpose**: Evaluate whether a feature should use AI/ML, rules-based logic, or a hybrid approach, with cost-benefit analysis.
- **Inputs**: Feature description, requirements
- **Outputs**: Decision framework analysis with recommendation

### flow-design

- **Purpose**: Design agentic AI workflows with checkpointing, error handling, and multi-agent orchestration patterns.
- **Inputs**: Workflow requirements, agent capabilities
- **Outputs**: Agentic flow design document

### mcp-review

- **Purpose**: Review Model Context Protocol (MCP) tool configurations for correctness, security, and optimization.
- **Inputs**: MCP configuration files
- **Outputs**: MCP review report

### bias-detection

- **Purpose**: Analyze AI/ML models and training data for bias across protected characteristics.
- **Inputs**: Model description, training data characteristics
- **Outputs**: Bias detection report

### evaluation-methodology

- **Purpose**: Design evaluation methodology for AI/ML models with appropriate metrics, test sets, and validation approaches.
- **Inputs**: Model description, use case requirements
- **Outputs**: Evaluation methodology document

### model-review

- **Purpose**: Review ML model architecture, training pipeline, and deployment configuration for best practices.
- **Inputs**: Model files, training config, deployment config
- **Outputs**: Model review report

---

## Custodian

### dead-code-scan

- **Purpose**: Scan the repository for dead code -- unused imports, unreachable functions, orphaned files, and deprecated patterns.
- **Inputs**: Codebase
- **Outputs**: Dead code report with removal recommendations

### migration-audit

- **Purpose**: Audit database migrations for consistency, safety, and alignment with model definitions.
- **Inputs**: Migration files, model files
- **Outputs**: Migration audit report

### pattern-audit

- **Purpose**: Audit codebase for adherence to canonical patterns defined in project-context.md.
- **Inputs**: project-context.md, codebase
- **Outputs**: Pattern compliance report with violations

### pr-review

- **Purpose**: Review a pull request for code quality, pattern compliance, test coverage, and potential issues.
- **Inputs**: PR diff, project-context.md
- **Outputs**: PR review comments
- **Slash command**: `/team:pr-review`

### quality-gate

- **Purpose**: Run a comprehensive quality gate check before release, covering tests, coverage, lint, type checking, and pattern compliance.
- **Inputs**: Codebase, test results
- **Outputs**: Quality gate verdict (PASS/FAIL) with details

### repo-health-check

- **Purpose**: Comprehensive repository health assessment covering structure, documentation, CI/CD, dependencies, and technical debt.
- **Inputs**: Repository
- **Outputs**: Health check report with scores and recommendations

---

## Diagrams (Excalidraw)

### create-excalidraw-diagram

- **Purpose**: Create system architecture diagrams, ERDs, UML diagrams, or general technical diagrams in Excalidraw JSON format.
- **Inputs**: Diagram requirements, system documentation
- **Outputs**: Excalidraw `.excalidraw` file
- **Slash command**: `/team:create-excalidraw-diagram`

### create-excalidraw-dataflow

- **Purpose**: Create data flow diagrams (DFD) in Excalidraw format showing data movement through system components.
- **Inputs**: System architecture, data flow requirements
- **Outputs**: Excalidraw `.excalidraw` file
- **Slash command**: `/team:create-excalidraw-dataflow`

### create-excalidraw-flowchart

- **Purpose**: Create flowchart visualizations in Excalidraw format for processes, pipelines, or logic flows.
- **Inputs**: Process description
- **Outputs**: Excalidraw `.excalidraw` file
- **Slash command**: `/team:create-excalidraw-flowchart`

### create-excalidraw-wireframe

- **Purpose**: Create website or application wireframes in Excalidraw format for UI planning.
- **Inputs**: UX requirements, page descriptions
- **Outputs**: Excalidraw `.excalidraw` file
- **Slash command**: `/team:create-excalidraw-wireframe`

---

## Creative

### brainstorming

- **Purpose**: Facilitate interactive brainstorming sessions using diverse creative techniques and ideation methods (SCAMPER, mind mapping, Six Thinking Hats, etc.).
- **Inputs**: Topic or challenge, optional technique preference
- **Outputs**: Organized ideas with categories and action items
- **Slash command**: `/team:brainstorming`

### design-thinking

- **Purpose**: Guide human-centered design processes through Empathize, Define, Ideate, Prototype, and Test phases.
- **Inputs**: Design challenge, user context
- **Outputs**: Design thinking session document
- **Slash command**: `/team:design-thinking`

### innovation-strategy

- **Purpose**: Identify disruption opportunities and architect business model innovation through strategic analysis of markets, competitive dynamics, and business model patterns.
- **Inputs**: Market context, competitive landscape, business challenge
- **Outputs**: Innovation strategy document
- **Slash command**: `/team:innovation-strategy`

### problem-solving

- **Purpose**: Apply systematic problem-solving methodologies (TRIZ, Theory of Constraints, Systems Thinking) to crack complex challenges.
- **Inputs**: Problem description, constraints, prior attempts
- **Outputs**: Problem-solving session document with solutions
- **Slash command**: `/team:problem-solving`

### storytelling

- **Purpose**: Craft compelling narratives using proven story frameworks and techniques for products, presentations, or marketing.
- **Inputs**: Story subject, audience, purpose
- **Outputs**: Narrative document
- **Slash command**: `/team:storytelling`

---

## Project Management

### document-project

- **Purpose**: Analyze and document brownfield projects by scanning codebase, architecture, and patterns to create comprehensive reference documentation.
- **Inputs**: Existing codebase
- **Outputs**: Project documentation with overview, source tree, and deep-dive files
- **Slash command**: `/team:document-project`

### generate-project-context

- **Purpose**: Create a concise project-context.md file with critical rules and patterns that AI agents must follow when implementing code. Optimized for LLM context efficiency.
- **Inputs**: Codebase scan, architectural decisions
- **Outputs**: `project-context.md` in `output/`
- **Slash command**: `/team:generate-project-context`

### workflow-init

- **Purpose**: Initialize a new project by determining project level (method/enterprise), type (greenfield/brownfield), and creating the appropriate workflow path.
- **Inputs**: Project characteristics
- **Outputs**: Workflow status tracking file
- **Slash command**: `/team:workflow-init`

### workflow-status

- **Purpose**: Lightweight status checker that answers "what should I do now?" for any agent. Reads YAML status file for workflow tracking.
- **Inputs**: Workflow status file
- **Outputs**: Current status and next recommendation
- **Slash command**: `/team:workflow-status`

### nav-audit

- **Purpose**: Audit navigation consistency -- detect tab count violations, orphaned routes, admin gate misalignment, hidden features, and tutorial content drift.
- **Inputs**: Routing files, navigation config
- **Outputs**: Navigation audit report

---

## Core Platform Workflows

### party-mode

- **Purpose**: Orchestrate group discussions between all installed agents, enabling natural multi-agent conversations where agents debate, challenge, and build on each other's expertise.
- **Inputs**: Discussion topic, agent selection (optional)
- **Outputs**: Discussion transcript and conclusions
- **Slash command**: `/team:party-mode`

### feature-orchestrator

- **Purpose**: Decompose complex features into parallel work streams, spawn sub-features, and consolidate results.
- **Inputs**: Feature description, decomposition criteria
- **Outputs**: Consolidated feature plan with parallel work streams
- **Slash command**: `/team:feature-orchestrator`

---

## Builder Workflows

### agent (builder)

- **Purpose**: Tri-modal workflow for creating, editing, and validating compliant agents through an 8-step guided process.
- **Inputs**: Agent concept (create), existing agent file (edit/validate)
- **Outputs**: Agent `.md` file with persona, menu, and activation protocol
- **Slash command**: `/team:agent`

### module (builder)

- **Purpose**: Quad-modal workflow for creating modules (Brief, Create, Edit, Validate) with full structure, config, agents, workflows, and documentation.
- **Inputs**: Module concept (brief), module brief (create), existing module (edit/validate)
- **Outputs**: Complete module directory with config.yaml, agents, workflows, and docs
- **Slash command**: `/team:module`

### workflow (builder)

- **Purpose**: Create structured standalone workflows using markdown-based step architecture (tri-modal: create, validate, edit).
- **Inputs**: Workflow requirements
- **Outputs**: Workflow directory with workflow.md/yaml, steps, and templates
- **Slash command**: `/team:workflow`

---

## Core Tasks

These are reusable tasks invoked by workflows, not standalone workflows:

### workflow (task)

- **Purpose**: The core workflow execution engine. Parses YAML configs, resolves variables, executes steps, saves outputs.
- **Path**: `team/engine/workflow.xml`
- **Slash command**: N/A (invoked automatically by workflow handlers)

### index-docs

- **Purpose**: Generate or update an index.md of all documents in a specified directory.
- **Path**: `team/engine/index-docs.xml`
- **Slash command**: `/team:index-docs`

### shard-doc

- **Purpose**: Split large markdown documents into smaller, organized files based on level 2 sections.
- **Path**: `team/engine/shard-doc.xml`
- **Slash command**: `/team:shard-doc`

### review-adversarial-general

- **Purpose**: Cynically review content and produce findings. Used internally by code-review and other adversarial workflows.
- **Path**: `team/engine/review-adversarial-general.xml`
- **Slash command**: N/A (invoked by workflows)

---

## Workflow Count Summary

| Category | Count |
|----------|-------|
| Analysis | 2 |
| Planning | 2 |
| Solutioning | 3 |
| Implementation | 8 |
| Quick Flow | 2 |
| DevOps | 6 |
| Testing | 8 |
| Data | 4 |
| API Contract | 3 |
| Security | 4 |
| NIST RMF | 3 |
| AI/ML | 6 |
| Custodian | 6 |
| Diagrams | 4 |
| Creative | 5 |
| Project | 5 |
| Core Platform | 2 |
| Builder | 3 |
| Core Tasks | 4 |
| **Total** | **80** |
