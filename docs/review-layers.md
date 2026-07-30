# Review Layers

Every implementation workflow (`quick-dev`, `dev-auto`) runs a review pass with
one or more layers. Each layer is an independent context-free reviewer with
its own prompt. Layers are defined in each workflow's `customize.toml` and can
be overridden per project.

## Default layers

Three layers ship as defaults:

1. **blind-hunter** — adversarial correctness (`team/core-skills/bmad-review/references/lens-adversarial.md`)
2. **edge-case-hunter** — edge-case sweep (`team/core-skills/bmad-review/references/lens-edge-case-hunter.md`)
3. **verification-gap** — behavior-coverage gaps (`team/core-skills/bmad-review/references/lens-verification-gap.md`)

## Overriding

Create `team/custom/<workflow>.toml` (e.g. `team/custom/quick-dev.toml`).
Use `[[workflow.review_layers]]` blocks. Merge rules:

- Matching `id` → the block replaces the vendored one.
- New `id` → the block appends to the vendored list.
- `instruction = ""` → disables that layer.

Templates: `team/custom/quick-dev.example.toml`, `team/custom/dev-auto.example.toml`.

## Reviewer independence

Every layer runs in a fresh context-free subagent. Do not have one layer read
or reference another's output. Layers converge only in the final triage step,
where their findings are compared and duplicates collapsed.

## Verification-gap focus

The verification-gap reviewer looks for **behavior** the tests do not cover,
not raw line coverage. Deterministic test-only coverage (unit tests exercising
private helpers) is preserved and not flagged as a gap.
