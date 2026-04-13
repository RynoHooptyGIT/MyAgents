---
name: 'checkpoint-preview'
description: 'Checkpoint Preview — Human-in-the-loop review. Walk through a change from purpose to details.'
---

You must execute the checkpoint-preview workflow precisely as defined.

<workflow-activation CRITICAL="TRUE">
1. LOAD the workflow engine: @team/engine/workflow.xml
2. READ the complete workflow engine file - this is the CORE OS for executing workflows
3. LOAD the checkpoint-preview workflow config: @team/workflows/checkpoint-preview/workflow.yaml
4. Pass the workflow config to the workflow engine and execute all steps
5. Follow the 5-step review: Orientation → Walkthrough → Detail Pass → Testing → Wrap-Up
</workflow-activation>
