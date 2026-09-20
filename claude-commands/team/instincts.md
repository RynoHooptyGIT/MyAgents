---
name: 'instincts'
description: 'Review, promote, or prune learned instincts — status | review | promote | prune | export | import'
---

Manage the instinct capture loop (learned behaviors mined from sessions). Instincts are context, not policy.

Subcommand = the first word after `/team:instincts` (default `status`):

- `status` → run `python3 scripts/instincts/instinct.py status` and show it verbatim.
- `review` → run `python3 scripts/instincts/instinct.py status --json`; for each pending instinct ask "accept / reject / skip?" and apply via `python3 scripts/instincts/instinct.py accept <id>` or `reject <id>`. Never bulk-accept without the user saying so. (Oracle auto mode's threshold accept is the one user-authorized exception — the user opted in with 'oracle auto'.)
- `promote` → `python3 scripts/instincts/instinct.py promote` (project → `~/.claude/instincts/` when active in 2+ projects with mean confidence ≥ 0.8).
- `prune` → `python3 scripts/instincts/instinct.py prune`.
- `export` → `python3 scripts/instincts/instinct.py export` and show the JSON.
- `import <file>` → `python3 scripts/instincts/instinct.py import < <file>`.

After any change, print one line summarizing what changed. Do not edit instinct YAML by hand; use the CLI so writes stay atomic.
