---
name: bmad-dev-auto
description: 'One iteration of an unattended development loop. Use when invoked by name.'
---

Read `workflow.md` in this directory and follow it as your run recipe. The step files (`step-01-…` through `step-04-…`) contain the detailed procedures each phase invokes.

- **On failure at any step:** report exactly what went wrong and HALT — do not silently continue.
