---
name: "oracle-dispatch-map"
description: "Routing table for Oracle ambient intelligence — maps problem categories to skills and agents"
version: 1.0.0
---

# Oracle Dispatch Map

Athena loads this file on activation and references it when determining how to handle detected problems. Edit this file to add new skills or agents without touching oracle.md.

## Claude Code Skills — read-only skills Athena invokes directly; skills that edit files produce a brief instead

Mode `direct` runs in the current session. Mode `brief` means Athena writes a brief and presents `/team:X` for a worker to run the skill.

| Category | Skill | Mode | When to Use |
|----------|-------|------|-------------|
| Bug / error / test failure | systematic-debugging | diagnose directly; fix phase → brief | Single error, test failure, unexpected behavior, build failure |
| Multiple independent bugs | dispatching-parallel-agents | brief one worker per independent problem | 2+ independent problems with no shared state |
| Code quality | simplify | brief | Code smell, redundancy, unnecessary complexity |
| New feature or fix | test-driven-development | brief | Implementation needs tests first |
| Completion check | verification-before-completion | direct | Before claiming anything is done or shipping |
| Feature planning | brainstorming | direct | User wants to explore an idea before fixing |

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
| ML / model eval | Neuron | /team:ml-expert | Model selection, evaluation, MLOps |
| Compliance (Gov) | Senator | /team:government-expert | Government regulations, public-sector policy |
| Compliance (Financial) | Sterling | /team:financial-expert | Financial-services regulation, AI governance |
| PRD / product | John | /team:pm | PRD creation/editing, product requirements |
| Brainstorming | Carson | /team:creative-thinking-coach | Idea exploration, creative thinking |
| Design / innovation | Maya | /team:design-strategy-coach | Design thinking, innovation strategy |
| Storytelling | Sophia | /team:storyteller-presenter | Narratives, presentations |
| Sprint lifecycle | Athena | Self (CS, DS, CR, SH) | Story creation, dev, review, ship |
| Learning | Athena | /team:instincts | Repeated user corrections, "we keep doing this", `[instincts] … pending` banner at session start |

**BRAINSTORMING LIFECYCLE:** After brainstorming, ideas must flow Brainstorm → Update Epics/PRD → CS → DS. No shortcut from brainstorm to implementation.

## Escalation Rules

| Condition | Action |
|-----------|--------|
| Problem spans 3+ categories | Run [LR] Let's Ride — scan-and-plan (Athena executes directly) |
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
