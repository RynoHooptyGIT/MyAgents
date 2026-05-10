---
name: "oracle-dispatch-map"
description: "Routing table for Oracle ambient intelligence — maps problem categories to skills and agents"
version: 1.0.0
---

# Oracle Dispatch Map

Athena loads this file on activation and references it when determining how to handle detected problems. Edit this file to add new skills or agents without touching oracle.md.

## Claude Code Skills (direct execution)

Athena invokes these directly — they run in the current session.

| Category | Skill | When to Use |
|----------|-------|-------------|
| Bug / error / test failure | systematic-debugging | Single error, test failure, unexpected behavior, build failure |
| Multiple independent bugs | dispatching-parallel-agents | 2+ independent problems with no shared state |
| Code quality | simplify | Code smell, redundancy, unnecessary complexity |
| New feature or fix | test-driven-development | Implementation needs tests first |
| Completion check | verification-before-completion | Before claiming anything is done or shipping |
| Feature planning | brainstorming | User wants to explore an idea before fixing |

## Team Agents (domain routing)

Athena recommends these via their `/team:` command. The user invokes them.

| Category | Agent | Command | When to Use |
|----------|-------|---------|-------------|
| Security | Shield | /team:security-auditor | Auth gaps, injection patterns, secrets exposure, OWASP concerns |
| Architecture | Winston | /team:architect | Design gaps, scalability concerns, pattern violations |
| Data / schema | Vault | /team:data-architect | Schema issues, query optimization, migration conflicts, caching |
| Test strategy | Murat | /team:tea | Test coverage gaps, framework issues, test architecture |
| DevOps / CI/CD | Forge | /team:devops | Pipeline failures, Docker issues, deployment, infrastructure |
| Frontend | Pixel | /team:frontend-dev | UI bugs, component issues, build tooling |
| UX / design | Sally | /team:ux-designer | Flow problems, accessibility, usability |
| API contract | Pact | /team:api-contract | Contract drift, endpoint issues, OpenAPI spec |
| Compliance (NIST) | Atlas | /team:nist-rmf-expert | Regulatory gaps, NIST RMF framework |
| Compliance (HIPAA) | Dr. Vita | /team:healthcare-expert | Healthcare regulatory, HIPAA |
| Code health | Sentinel | /team:custodian | Repo health, dead code, pattern audit |
| Quick fix | Barry | /team:quick-flow-solo-dev | Small isolated fix, prototype |
| Sprint lifecycle | Athena | Self (CS, DS, CR, SH) | Story creation, dev, review, ship |

## Escalation Rules

| Condition | Action |
|-----------|--------|
| Problem spans 3+ categories | Recommend Maestro scan-and-plan (`/team:maestro` then `LR`) |
| Major architecture change needed | Route through CEO approval gate (ceo-approval.xml) |
| 3+ fix attempts failed on same problem | Stop. Question assumptions. Suggest `/team:architect` for design review |
| Classification ambiguous (2+ categories equally likely) | Present top 2 routing options to user, let them choose |
| Security finding rated CRITICAL | Immediate escalation — halt current work, route to Shield |

## Priority Order

When multiple problems are detected, dispatch in this order:

1. **CRITICAL** — Security vulnerabilities, data loss risks, production-breaking bugs
2. **HIGH** — Test failures, build errors, blocked stories
3. **MEDIUM** — Code quality, coverage gaps, stale state
4. **LOW** — Documentation, minor cleanup, optimization opportunities
