# Epic Consistency Check - Proactive Cross-Epic Audit

<critical>The workflow execution engine is governed by: {project-root}/_bmad/core/tasks/workflow.xml</critical>
<critical>You MUST have already loaded and processed: {project-root}/_bmad/bmm/workflows/4-implementation/epic-consistency-check/workflow.yaml</critical>
<critical>Communicate all responses in {communication_language} and language MUST be tailored to {user_skill_level}</critical>
<critical>Generate all documents in {document_output_language}</critical>

<critical>PERSONA: You are Bob, the Scrum Master. Crisp, checklist-driven. Every finding is specific: story ID, file path, line of conflict. Zero tolerance for vague "might overlap" statements. If you cannot identify a concrete conflict, do not report one.</critical>

<critical>DOCUMENT OUTPUT: A structured consistency audit report with severity-classified findings and actionable remediation steps. No fluff.</critical>

<workflow>

<step n="0.5" goal="Discover and load ALL project documents">
  <invoke-protocol name="discover_inputs" />
  <note>After discovery, these content variables are available: {epics_content}, {stories_content}, {architecture_content}, {sprint_status_content}</note>
  <action>Confirm story files were loaded. Count total story files found.</action>
  <action>If fewer than 5 story files loaded, WARN user and ask if this is expected before proceeding.</action>
  <action>Parse sprint-status.yaml to understand which stories are backlog, ready-for-dev, in-progress, review, or done.</action>
  <action>Display loading summary:</action>
  <example>
  ## Documents Loaded
  - Epic files: X
  - Story files: Y
  - Architecture: loaded/not found
  - Sprint status: loaded/not found
  </example>
</step>

<step n="1" goal="Build Story Inventory and File-Touch Map">
  <action>For EACH loaded story file, extract the following into a structured inventory:</action>

  1. **Story ID** — from filename (e.g., `mt-4-1`, `14-3`, `1-2`)
  2. **Epic** — from the numeric prefix (e.g., `mt-4` belongs to MT-Epic 4, `14` belongs to Epic 14)
  3. **Story title** — from the H1 heading
  4. **Status** — from the `Status:` field in the story or from sprint-status.yaml
  5. **Layer** — classify as BACKEND, FRONTEND, or FULL-STACK based on:
     - File paths in "Key Files to Modify" / "New Files" containing `backend/` = BACKEND
     - File paths containing `packages/frontend/` = FRONTEND
     - Both present = FULL-STACK
     - If no file paths found, infer from task descriptions (DB/API tasks = BE, UI/component tasks = FE)
  6. **Files touched** — extract ALL file paths from:
     - "Key Files to Modify" section
     - "New Files" section
     - File paths mentioned inline in Tasks/Subtasks
  7. **API endpoints** — extract any API routes mentioned (e.g., `POST /api/v1/auth/switch-tenant`)
  8. **Dependencies** — extract from "Dependencies" or references like "Depends on: MT-1.7"
  9. **Components** — extract React component names, Python service/router class names

  <action>Store this as the **Story-Touch-Map** — the foundation for all analysis.</action>

  <action>Display summary table to user:</action>
  <example>
  ## Story Inventory ({Y} stories across {X} epics)

  | Story ID | Epic | Layer | Status | Files | APIs | Deps |
  |----------|------|-------|--------|-------|------|------|
  | mt-4-1   | MT-4 | FE    | ready  | 5     | 0    | —    |
  | mt-4-2   | MT-4 | FULL  | ready  | 8     | 1    | mt-4-1 |
  | 14-3     | 14   | FULL  | done   | 6     | 2    | —    |

  Unique files touched: Z
  </example>
</step>

<step n="2" goal="Detect Story-to-Story File Overlap">
  <action>Using the Story-Touch-Map, build a **File Collision Matrix**:</action>

  1. Group all files by path
  2. For each file path touched by MORE THAN ONE story, record:
     - File path
     - All story IDs that touch it
     - Whether the stories are in the SAME epic or DIFFERENT epics
     - Whether modifications are likely additive (adding new fields/methods) or conflicting (changing existing behavior)

  <action>Classify each collision by severity:</action>

  - **CRITICAL**: Two non-done stories in DIFFERENT epics modify the same file in ways that could create merge conflicts or semantic contradictions. Example: Story A adds field `activeTenantId` to `AuthState` while Story B restructures `AuthState` entirely.

  - **WARNING**: Two stories in the SAME epic modify the same file. Expected if sequential (story B depends on A), but flag if they are independent and could run in parallel without declared ordering.

  - **INFO**: A done story and a non-done story touch the same file. Normal — note for awareness that the file has existing modifications.

  <action>For each CRITICAL or WARNING finding, specify:</action>
  - The exact file path
  - Which stories touch it (with their epic)
  - What each story intends to do to the file (from Tasks/Subtasks)
  - Whether the modifications are complementary or contradictory
  - Recommended resolution (sequencing, story consolidation, or interface abstraction)

  <example>
  ### CRITICAL: Cross-Epic File Collision

  **EC-001** | Severity: CRITICAL
  **File:** `packages/frontend/src/features/auth/hooks/useAuth.ts`
  **Stories:** mt-4-1 (MT-Epic 4) + 14-4 (Epic 14)
  **Analysis:**
  - mt-4-1: Adds `activeTenantId` to auth state, modifies `_handleSuccessfulAuth`
  - 14-4: Adds data classification permission checks to auth context
  **Assessment:** POTENTIALLY CONFLICTING — both modify auth state independently without declared dependency
  **Resolution:** Add explicit dependency from 14-4 → mt-4-2. Sequence 14-4 after MT-Epic 4 completion.
  </example>
</step>

<step n="3" goal="Detect Cross-Epic Consistency Conflicts">
  <action>For stories across DIFFERENT epics, check for:</action>

  1. **Semantic contradictions**: Two stories define conflicting behavior for the same domain concept
     - Compare acceptance criteria GIVEN/WHEN/THEN statements for the same entities
     - Example: Epic 1 story marks `tenant_id` as required; MT-Epic 1 story makes it nullable

  2. **Schema conflicts**: Stories modifying the same database table/model with incompatible changes
     - Extract table/model names from tasks and dev notes
     - Flag when two stories add columns to the same table or modify the same model relationships

  3. **Component ownership conflicts**: Stories that both create or heavily modify the same React component or backend service
     - From "New Files" sections, detect duplicate file creation
     - From "Key Files to Modify", detect when the same component is a primary target of multiple cross-epic stories

  4. **Dependency chain violations**: Story A depends on Story B, but B is in a later epic or has a lower priority
     - Parse "Dependencies" and "Depends on" references
     - Cross-reference against sprint-status.yaml ordering and epic sequencing
     - Flag circular dependencies

  <action>For each finding, produce a structured entry:</action>

  <example>
  **EC-005** | Severity: CRITICAL | Category: SCHEMA
  **Stories:** mt-1-8 (MT-Epic 1) vs. 14-1 (Epic 14)
  **Conflict:** mt-1-8 marks `users.tenant_id` as deprecated/nullable. 14-1 references `users.tenant_id` in a JOIN query.
  **Evidence:**
  - mt-1-8 AC: "Make users.tenant_id nullable and mark as deprecated"
  - 14-1 tasks: "JOIN users ON users.tenant_id = ..."
  **Resolution:** Update 14-1 to use `user_tenants` junction table instead of deprecated column.
  </example>
</step>

<step n="4" goal="Backend/Frontend API Sync Validation">
  <action>For EVERY API endpoint found in stories, validate full-stack coverage:</action>

  1. **Extract all API endpoints** from story files:
     - Scan for route patterns: `GET /api/...`, `POST /api/...`, `PUT /api/...`, `DELETE /api/...`
     - Also extract from architecture document as the canonical reference

  2. **For each endpoint, check:**
     - **Backend story exists?** — a story with backend tasks implements this endpoint
     - **Frontend story exists?** — a story with frontend tasks consumes this endpoint
     - **Request/response schema match?** — frontend references the same fields backend defines
     - **Error handling aligned?** — frontend handles error codes backend specifies

  3. **Classify findings:**

  - **CRITICAL: Orphaned backend endpoint** — backend story creates endpoint, no frontend story consumes it
  - **CRITICAL: Frontend calls non-existent endpoint** — frontend references API no backend story creates
  - **WARNING: Schema mismatch** — field naming inconsistency (e.g., `tenant_name` vs `tenantName`)
  - **WARNING: Missing error handling** — backend defines error codes frontend doesn't handle
  - **INFO: Architecture endpoint without story** — architecture defines API but no story implements it yet

  <action>Display as endpoint coverage table:</action>

  <example>
  ### API Endpoint Coverage

  | Endpoint | BE Story | FE Story | Schema Match | Status |
  |----------|----------|----------|--------------|--------|
  | POST /api/v1/auth/switch-tenant | mt-4-2 | mt-4-2 | YES | OK |
  | GET /api/v1/admin/users/:id/tenants | mt-3-1 | mt-4-5 | PARTIAL | WARNING |
  | POST /api/v1/classify | 14-2 | — | — | CRITICAL |

  **EC-010** | Severity: WARNING | Category: SCHEMA MISMATCH
  **Endpoint:** `GET /api/v1/admin/users/:id/tenants`
  **Backend (mt-3-1):** Returns `tenant_associations` with `roles: string[]`
  **Frontend (mt-4-5):** Expects `role_display_names` field not in BE response
  **Resolution:** Clarify field ownership — derive client-side or add to BE response.
  </example>
</step>

<step n="5" goal="Gap Detection — Missing Stories">
  <action>Identify work implied by existing stories that has no story of its own:</action>

  1. **Dependency gap analysis:**
     - For each dependency reference (e.g., "Depends on: MT-1.7"), verify the referenced story exists
     - For each story creating an API endpoint/component, verify a consumer/test exists

  2. **Architecture coverage gaps:**
     - Compare architecture document's component/API list against stories
     - Identify architecture-defined items with no implementing story
     - Focus on: middleware, migration scripts, shared utilities, configuration

  3. **Implied work detection:**
     - Schema changes without migration task
     - New API endpoints without integration test coverage
     - New UI components without unit test tasks
     - Auth/permission changes without security validation story

  4. **Cross-epic bridge gaps:**
     - Where two epic scopes meet, is there a story validating the integration point?
     - Are there shared types, hooks, or schemas that multiple epics assume exist but nobody creates?

  <action>For each gap:</action>

  <example>
  **GAP-001** | Severity: WARNING
  **Missing:** Integration test story for multi-tenant + data governance interaction
  **Implied by:** mt-4-2 (cache invalidation on tenant switch) + 14-6 (data governance dashboard)
  **Description:** No story validates data governance dashboard refreshes correctly after tenant switch
  **Recommendation:** Create story in MT-Epic 5: "Validate data governance dashboard after tenant switch"
  </example>
</step>

<step n="6" goal="Generate Consistency Audit Report">
  <action>Compile the complete audit report and write to {default_output_file}.</action>

  <action>Report structure:</action>

  ```
  # Epic Consistency Audit Report

  **Generated:** {date}
  **Project:** {project_name}
  **Audited by:** Bob (SM Agent)
  **Scope:** {epic_count} epics, {story_count} stories, {file_count} unique files

  ## Executive Summary

  - **CRITICAL findings:** X
  - **WARNING findings:** Y
  - **INFO findings:** Z
  - **Gaps detected:** N
  - **Overall health:** [HEALTHY | NEEDS ATTENTION | AT RISK]

  Health determination:
  - HEALTHY: 0 CRITICAL, <=3 WARNING
  - NEEDS ATTENTION: 1-2 CRITICAL or >3 WARNING
  - AT RISK: 3+ CRITICAL

  ## Section 1: File Collision Analysis
  [Results from Step 2]

  ## Section 2: Cross-Epic Conflicts
  [Results from Step 3]

  ## Section 3: Backend/Frontend API Sync
  [Results from Step 4]

  ## Section 4: Gap Analysis
  [Results from Step 5]

  ## Section 5: Remediation Roadmap

  ### Immediate Actions (CRITICAL)
  [Numbered list with specific remediation steps]

  ### Next Sprint Actions (WARNING)
  [Numbered list with recommended timing]

  ### Backlog Items (INFO + GAPS)
  [Numbered list of awareness items]

  ## Appendix A: Complete Story-Touch-Map
  [Full inventory table from Step 1]

  ## Appendix B: File Collision Matrix
  [Complete file-to-story mapping]
  ```

  <action>Write the report to {default_output_file}</action>
  <action>Display Executive Summary and all CRITICAL findings to the user</action>

  <ask>Review audit results. Options:
  1. **[V]** View full report
  2. **[R]** Re-analyze a specific section
  3. **[C]** Generate correct-course proposals for CRITICAL findings
  4. **[D]** Done — dismiss
  </ask>

  <check if="user selects C">
    <action>For each CRITICAL finding, draft a mini correct-course proposal:</action>
    - Problem statement (from finding)
    - Affected stories (with IDs)
    - Proposed fix (story modification, new story, or sequencing change)
    - Offer to invoke full correct-course workflow for complex changes
  </check>
</step>

</workflow>
