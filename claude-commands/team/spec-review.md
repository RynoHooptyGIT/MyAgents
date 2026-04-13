---
name: 'spec-review'
description: 'Spec Review — Technical specification gate between story creation and implementation.'
---

You must execute the spec-review workflow precisely as defined.

<workflow-activation CRITICAL="TRUE">
1. LOAD the workflow engine: @team/engine/workflow.xml
2. READ the complete workflow engine file - this is the CORE OS for executing workflows
3. LOAD the spec-review workflow config: @team/workflows/spec-review/workflow.yaml
4. Pass the workflow config to the workflow engine and execute all steps
5. The spec MUST be approved before dev-story can begin
</workflow-activation>
