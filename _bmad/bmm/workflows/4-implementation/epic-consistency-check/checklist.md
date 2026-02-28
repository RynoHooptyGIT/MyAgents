# Epic Consistency Check - Validation Checklist

<critical>This checklist is executed as part of: {project-root}/_bmad/bmm/workflows/4-implementation/epic-consistency-check/workflow.yaml</critical>
<critical>Validate each section systematically. Record findings with severity levels: CRITICAL, WARNING, INFO.</critical>
<critical>Every finding MUST include specific story IDs and file paths — no vague warnings.</critical>

<checklist>

<section n="1" title="Story Inventory Completeness">

<check-item id="1.1">
<prompt>Verify all story files in implementation_artifacts were loaded</prompt>
<action>Count story files found vs. stories listed in sprint-status.yaml</action>
<action>Flag any stories in sprint-status.yaml without corresponding .md files</action>
<action>Flag any .md files not referenced in sprint-status.yaml</action>
<status>[ ] Done / [ ] N/A / [ ] Action-needed</status>
</check-item>

<check-item id="1.2">
<prompt>Verify Story-Touch-Map extraction quality</prompt>
<action>Confirm every story has: ID, epic, layer classification, files touched list</action>
<action>Flag stories missing "Key Files to Modify" or "Tasks / Subtasks" sections</action>
<status>[ ] Done / [ ] N/A / [ ] Action-needed</status>
</check-item>

<check-item id="1.3">
<prompt>Verify epic file coverage</prompt>
<action>Confirm all epic files in planning-artifacts were loaded</action>
<action>Cross-reference epic numbers in stories against loaded epic files</action>
<status>[ ] Done / [ ] N/A / [ ] Action-needed</status>
</check-item>

</section>

<section n="2" title="File Collision Analysis">

<check-item id="2.1">
<prompt>Check for same-file modifications across stories</prompt>
<action>Build file-to-story mapping from Story-Touch-Map</action>
<action>Identify all files touched by 2+ stories</action>
<action>Classify: same-epic (expected) vs. cross-epic (risky)</action>
<status>[ ] Done / [ ] N/A / [ ] Action-needed</status>
</check-item>

<check-item id="2.2">
<prompt>Assess collision severity for each multi-touch file</prompt>
<action>For each collision, determine: additive vs. conflicting modifications</action>
<action>Check if dependency chain enforces correct ordering</action>
<action>Flag unordered parallel modifications as CRITICAL</action>
<status>[ ] Done / [ ] N/A / [ ] Action-needed</status>
</check-item>

<check-item id="2.3">
<prompt>Check for duplicate component/file creation</prompt>
<action>From "New Files" sections, detect if two stories create the same file</action>
<action>CRITICAL if same path, WARNING if same component name in different paths</action>
<status>[ ] Done / [ ] N/A / [ ] Action-needed</status>
</check-item>

</section>

<section n="3" title="Cross-Epic Consistency">

<check-item id="3.1">
<prompt>Check for semantic contradictions in acceptance criteria</prompt>
<action>Compare GIVEN/WHEN/THEN statements across epics for the same domain concepts</action>
<action>Focus on: data models, user roles, API behavior, state management</action>
<status>[ ] Done / [ ] N/A / [ ] Action-needed</status>
</check-item>

<check-item id="3.2">
<prompt>Check for database schema conflicts</prompt>
<action>Extract all table/column modifications from stories</action>
<action>Flag: same table modified by different epics, conflicting column types, contradictory constraints</action>
<status>[ ] Done / [ ] N/A / [ ] Action-needed</status>
</check-item>

<check-item id="3.3">
<prompt>Check dependency chain integrity</prompt>
<action>Parse all "Depends on" and "Dependencies" references</action>
<action>Verify referenced stories exist and are sequenced correctly</action>
<action>Flag circular dependencies or backward references</action>
<status>[ ] Done / [ ] N/A / [ ] Action-needed</status>
</check-item>

</section>

<section n="4" title="Backend/Frontend API Sync">

<check-item id="4.1">
<prompt>Inventory all API endpoints across stories</prompt>
<action>Extract every API route pattern from all story files</action>
<action>Map each endpoint to its backend story and frontend consumer story</action>
<status>[ ] Done / [ ] N/A / [ ] Action-needed</status>
</check-item>

<check-item id="4.2">
<prompt>Validate endpoint coverage</prompt>
<action>Every backend endpoint must have a frontend consumer (or be API-only with justification)</action>
<action>Every frontend API call must have a backend implementation story</action>
<action>Flag orphaned endpoints in either direction</action>
<status>[ ] Done / [ ] N/A / [ ] Action-needed</status>
</check-item>

<check-item id="4.3">
<prompt>Validate request/response schema alignment</prompt>
<action>For each endpoint pair (BE + FE story), compare field names and types</action>
<action>Check for casing mismatches (snake_case vs camelCase)</action>
<action>Check for missing error code handling on frontend</action>
<status>[ ] Done / [ ] N/A / [ ] Action-needed</status>
</check-item>

<check-item id="4.4">
<prompt>Cross-reference against architecture document</prompt>
<action>Verify story endpoints match architecture-defined API contracts</action>
<action>Flag endpoints in stories not described in architecture</action>
<action>Flag architecture endpoints with no implementing story</action>
<status>[ ] Done / [ ] N/A / [ ] Action-needed</status>
</check-item>

</section>

<section n="5" title="Gap Detection">

<check-item id="5.1">
<prompt>Check for missing migration stories</prompt>
<action>Any story modifying database schema should have or reference a migration task</action>
<action>Flag schema changes without migration coverage</action>
<status>[ ] Done / [ ] N/A / [ ] Action-needed</status>
</check-item>

<check-item id="5.2">
<prompt>Check for shared artifact gaps</prompt>
<action>Identify shared types, hooks, utilities assumed by multiple stories</action>
<action>Verify a story exists that creates each shared artifact</action>
<action>Flag shared artifacts with no creation story</action>
<status>[ ] Done / [ ] N/A / [ ] Action-needed</status>
</check-item>

<check-item id="5.3">
<prompt>Check for integration point coverage</prompt>
<action>Where two epics interact, verify integration validation stories exist</action>
<action>Flag epic boundaries without integration testing</action>
<status>[ ] Done / [ ] N/A / [ ] Action-needed</status>
</check-item>

</section>

</checklist>

<execution-notes>
<note>This is a PROACTIVE audit — run before problems manifest, not after</note>
<note>Every finding must include specific story IDs and file paths</note>
<note>Severity drives priority: CRITICAL = block sprint, WARNING = address soon, INFO = awareness</note>
<note>This checklist can be re-run after remediation to verify fixes</note>
<note>Focus on NON-DONE stories primarily, but include done stories in collision detection</note>
</execution-notes>
