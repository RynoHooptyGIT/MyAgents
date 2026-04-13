---
name: 'validate-prd'
description: 'Validate PRD — 13-step comprehensive PRD validation against quality standards.'
---

You must execute the validate-prd workflow precisely as defined.

<workflow-activation CRITICAL="TRUE">
1. LOAD the workflow engine: @team/engine/workflow.xml
2. READ the complete workflow engine file - this is the CORE OS for executing workflows
3. LOAD the validate-prd workflow config: @team/workflows/validate-prd/workflow.yaml
4. Pass the workflow config to the workflow engine and execute all steps
5. Run all 13 validation checks and produce the validation report
</workflow-activation>
