---
name: 'v-02c-validate-menu'
description: 'Validate menu structure and append to report'

nextStepFile: './v-02d-validate-structure.md'
validationReport: '{bmb_creations_output_folder}/validation-report-{agent-name}.md'
agentMenuPatterns: ../data/agent-menu-patterns.md
agentFile: '{agent-file-path}'
---

# Validate Step 2c: Validate Menu

## STEP GOAL

Validate the agent's command menu structure against system standards as defined in agentMenuPatterns.md. Append findings to validation report and auto-advance.

## MANDATORY EXECUTION RULES

- 📖 CRITICAL: Read the complete step file before taking any action
- 🔄 CRITICAL: Read validationReport and agentMenuPatterns first
- 🔄 CRITICAL: Load the actual agent file to validate menu
- 🚫 NO MENU - append findings and auto-advance
- ✅ YOU MUST ALWAYS SPEAK OUTPUT In your Agent communication style with the config `{communication_language}`

### Step-Specific Rules:

- 🎯 Validate menu against agentMenuPatterns.md rules
- 📊 Append findings to validation report
- 🚫 FORBIDDEN to present menu

## EXECUTION PROTOCOLS

- 🎯 Load agentMenuPatterns.md reference
- 🎯 Load the actual agent file for validation
- 📊 Validate commands and menu
- 💾 Append findings to validation report
- ➡️ Auto-advance to next validation step

## MANDATORY SEQUENCE

**CRITICAL:** Follow this sequence exactly. Do not skip, reorder, or improvise unless user explicitly requests a change.

### 1. Load References

Read `{agentMenuPatterns}`, `{validationReport}`, and `{agentFile}`.

### 2. Validate Menu

Perform these checks systematically - validate EVERY rule specified in agentMenuPatterns.md:

1. **Menu Structure**
   - [ ] Menu section exists and is properly formatted
   - [ ] At least one menu item defined (unless intentionally tool-less)
   - [ ] Menu items follow proper YAML structure
   - [ ] Each item has required fields (name, description, pattern)

2. **Menu Item Requirements**
   For each menu item:
   - [ ] name: Present, unique, uses kebab-case
   - [ ] description: Clear and concise
   - [ ] pattern: Valid regex pattern or tool reference
   - [ ] scope: Appropriate scope defined (if applicable)

3. **Pattern Quality**
   - [ ] Patterns are valid and testable
   - [ ] Patterns are specific enough to match intended inputs
   - [ ] Patterns are not overly restrictive
   - [ ] Patterns use appropriate regex syntax

4. **Description Quality**
   - [ ] Each item has clear description
   - [ ] Descriptions explain what the item does
   - [ ] Descriptions are consistent in style
   - [ ] Descriptions help users understand when to use

5. **Alignment Checks**
   - [ ] Menu items align with agent's role/purpose
   - [ ] Menu items are supported by agent's expertise
   - [ ] Menu items fit within agent's constraints
   - [ ] Menu items are appropriate for target users

6. **Completeness**
   - [ ] Core capabilities for this role are covered
   - [ ] No obvious missing functionality
   - [ ] Menu scope is appropriate (not too sparse/overloaded)
   - [ ] Related functionality is grouped logically

7. **Standards Compliance**
   - [ ] No prohibited patterns or commands
   - [ ] No security vulnerabilities in patterns
   - [ ] No ambiguous or conflicting items
   - [ ] Consistent naming conventions

8. **Menu Link Validation (Agent Type Specific)**
   - [ ] Determine agent type from metadata:
     - Simple: module property is 'stand-alone' AND hasSidecar is false/absent
     - Expert: hasSidecar is true
     - Module: module property is a module code (e.g., 'bmm', 'bmb', 'bmgd', 'bmad')
   - [ ] For Expert agents (hasSidecar: true):
     - Menu handlers SHOULD reference external sidecar files (e.g., `./{agent-name}-sidecar/...`)
     - OR have inline prompts defined directly in the handler
   - [ ] For Module agents (module property is a module code):
     - Menu handlers SHOULD reference external module files under the module path
     - Exec paths must start with `{project-root}/team/{module}/...`
     - Verify referenced files exist under the module directory
   - [ ] For Simple agents (stand-alone, no sidecar):
     - Menu handlers MUST NOT have external file links
     - Menu handlers SHOULD only use relative links within the same file (e.g., `#section-name`)
     - OR have inline prompts defined directly in the handler

### 3. Append Findings to Report

Append to `{validationReport}`:

```markdown
### Menu Validation

**Status:** {✅ PASS / ⚠️ WARNING / ❌ FAIL}

**Checks:**
- [ ] A/P/C convention followed
- [ ] Command names clear and descriptive
- [ ] Command descriptions specific and actionable
- [ ] Menu handling logic properly specified
- [ ] Agent type appropriate menu links verified

**Detailed Findings:**

*PASSING:*
{List of passing checks}

*WARNINGS:*
{List of non-blocking issues}

*FAILURES:*
{List of blocking issues that must be fixed}
```

### 4. Auto-Advance

Load and execute `{nextStepFile}` immediately.

---

**Validating YAML structure...**
