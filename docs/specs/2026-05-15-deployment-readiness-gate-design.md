# Gate 4: Deployment Readiness — Design Spec

**Date:** 2026-05-15
**Status:** Draft
**Owner:** DevOps Agent (Forge) + Oracle (Athena)
**Related:** CLAUDE.md Mandatory Gates 1-3

## Problem

Gates 1-3 enforce quality from design through CI. But nothing gates the transition from "code merged" to "running in production." AI agents can produce perfectly reviewed, tested, and merged code that fails catastrophically on deploy because no one verified migrations run, health checks work, monitoring exists, or rollback functions.

## Scope

Gate 4 fires **after CI passes but before code reaches staging or production**. It is owned by the DevOps agent (Forge) and enforced by the Oracle during the Ship workflow.

## Proposed Gate Checks

### Pre-Deployment (Before Staging)

1. **Migration dry-run succeeds** — `alembic upgrade --sql` produces valid SQL against target schema
2. **Pre-deploy smoke tests pass** — health check, login flow, critical CRUD path
3. **Health/readiness probes defined** — every deployable service has a `/health` endpoint checking DB and cache connectivity
4. **New env vars provisioned** — all env vars declared in Gate 1 exist in target environment config

### Pre-Production (Before Production Promote)

5. **Rollback tested in staging** — deploy, rollback, verify prior state restored
6. **Monitoring + alerting configured** — error rate alert, p95 latency alert, uptime monitoring exist for the service
7. **Incident response runbook exists** — how to identify outage, restart, rollback, who to contact, known failure modes
8. **Canary/staged rollout for critical paths** — changes touching auth, authorization, or payment must NOT deploy to 100% simultaneously

### Post-Deployment Verification

9. **Smoke tests pass in production** — same suite as pre-deploy, run against production within 5 minutes of deploy
10. **Error rate check** — error rates have not increased by more than 2x baseline within 15 minutes; auto-rollback if exceeded
11. **Feature flag cleanup tracked** — flags older than 90 days without removal generate a warning

## Integration Points

- **Ship Workflow (`SH`)**: Gate 4 checks run as a mandatory step before the actual deployment commands execute
- **Oracle Lifecycle**: A new status transition: `done` -> `deploying` -> `shipped` (or `rolled-back`)
- **DevOps Agent (Forge)**: Owns the deployment verification prompts and tooling
- **Sprint Status**: New story statuses to track deployment state

## Open Questions

1. How much of Gate 4 can be automated vs. requires agent judgment?
2. Should staging deployment be a separate workflow step from production promotion?
3. What tooling (Terraform, Docker Compose, k8s manifests) defines the deployment target?
4. How do we handle projects that don't have a staging environment yet?
5. Should load test baselines be required for performance-sensitive stories?

## Next Steps

- [ ] Brainstorm integration with Ship workflow
- [ ] Design the `deploying` / `shipped` status transitions
- [ ] Define minimum viable smoke test suite structure
- [ ] Determine monitoring-as-code approach (what format, where stored)
- [ ] Build deployment readiness checklist into DevOps agent activation
