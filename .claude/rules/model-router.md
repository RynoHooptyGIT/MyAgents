# Model router (orchestrator rules)

The session model is `fable`. It routes and orchestrates; it does not do bulk work.

Before delegating or doing any non-trivial task:

1. Pick the required tier (light / standard / high / frontier) from `task_tiers` in `.agents/model-routing.json`.
2. Estimate input and output tokens for the task.
3. Run the cost gate:
   `python3 scripts/routing/estimate.py --in <tokens> --out <tokens> --tier <tier>`
4. Act on the verdict:
   - `ok`: proceed with the chosen model.
   - `confirm`: tell the user the model and estimated USD in one line, then proceed.
   - `block` (exit 3): stop and ask the user before spending.
5. Run the work on the chosen model by passing it as the Agent tool's `model` argument (`haiku`, `sonnet`, `opus`, `fable`). Do the work in this session only when the chosen model is `fable` itself, i.e. nothing cheaper is adequate.

Rules:
- Pick the cheapest model whose tier fits. Never default to the orchestrator for light or standard work.
- Validate cost before running, not after.
- If `prices_verified` is false, say so once per session; the numbers are illustrative.
- Do not route in a way that skips a review gate in CLAUDE.md; gates run at their required tier.
