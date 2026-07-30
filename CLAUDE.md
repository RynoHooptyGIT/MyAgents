# Project Instructions

## Multi-Agent Coordination

This project uses the multi-agent coordination protocol. When running as one
of multiple simultaneous Claude instances:

1. Always run `/agent-coordinator` before beginning work
2. Always run `/agent-shutdown` before ending your session
3. Never operate in the main repo checkout — use your assigned worktree
4. Check `.agents/decisions/` before making architectural choices
5. Write decisions that affect other agents to `.agents/decisions/`
6. Respect file ownership — do not edit files claimed by other agents

### Coordination Files

- `.agents/registry/` — who's running (don't edit manually)
- `.agents/claims/` — who owns what files (don't edit manually)
- `.agents/decisions/` — architectural decisions (read before designing)
- `.agents/requests/` — inter-agent requests
- `.agents/status/` — per-agent progress
- `.agents/config.yaml` — coordination settings

## Oracle Awareness

When Athena (Oracle) has been activated in this session via `/team:oracle`, maintain ambient monitoring after every tool result. Evaluate output for errors, completions, security signals, and user frustration. Respond according to the current oracle mode:

- **suggest** (default): One-line nudge at pause points when problems are detected
- **auto**: Invoke the matching skill or agent immediately
- **off**: Silent — only respond to direct commands

Mode toggles: `oracle auto` | `oracle suggest` | `oracle off` | `oracle status`

Fix triggers: `fix it` (plan + approval) | `just fix it` (auto-execute)

## Mandatory Gates

All implementation work must pass these gates. Agents and reviewers enforce them with zero tolerance.

### Gate 1: Pre-Implementation Architecture Review

Before any story implementation, `/team:architect` must verify:

**Data Architecture:**
- Enumerations use DB lookup tables, not code constants
- Configurable values come from `tenant_settings`, not hardcoded
- All mutations log to governance ledger
- All list endpoints are paginated
- All deletes are soft deletes with audit trail
- No cross-domain model imports
- Frontend data comes from API, not hardcoded arrays
- Single configurable component patterns, not per-role component proliferation

**Security-by-Design:**
- Every new endpoint declares auth requirement (authenticated vs `# PUBLIC-ENDPOINT` with CEO approval)
- `tenant_id` always derived from JWT/session, never from client input
- RBAC permission model defined before implementation

**Operational Readiness-by-Design:**
- Migration impact classified (Safe / Brief-Lock / Dangerous) if schema changes
- Rollback plan documented for API, schema, or config changes
- Feature flag strategy declared for user-visible behavior changes
- New env vars listed with defaults, target environments, and secret classification
- Error handling contract defined (status codes, error body shape, retry semantics)
- Observability plan answered: "How will we know this is working in production?"

**Data Integrity:**
- New tables include `tenant_id` column (except explicit system tables)
- Foreign keys specify ON DELETE behavior (CASCADE / SET NULL / RESTRICT)
- Concurrent access strategy declared (optimistic locking, idempotency keys)

### Gate 2: Post-Implementation Holistic Review

After implementation, before shipping, `/team:code-review` must verify:

**Architecture Fit:**
- Change fits the global architecture
- Works with all other features, not just in isolation
- Data flow is end-to-end (DB -> service -> API -> hook -> UI)
- A different tenant with different settings would still work
- No new hardcoded values that should be configurable

**Static Analysis:**
- Lint, type-check, and format pass with zero warnings on changed files
- Test coverage on changed files did not decrease

**Security Verification:**
- Secrets scan clean on all staged files (no `API_KEY=`, `SECRET=`, `PASSWORD=` patterns)
- No raw SQL string construction (f-strings, concatenation)
- No PII in log statements

**Contract and Migration:**
- OpenAPI spec updated if endpoints changed
- Migration rollback tested (upgrade -> downgrade -> upgrade cycle) if migrations created
- Error responses verified for at least one error path per new endpoint

**Hygiene:**
- No `TODO`/`FIXME`/`HACK` without a linked issue number
- Health check still returns 200

### Gate 3: Architecture Enforcement Tests

Automated tests in `tests/test_architecture.py` that block CI:

**Data Architecture (original):**
- `test_no_hard_deletes` -- no `db.delete()` in service files
- `test_no_cross_domain_imports` -- no domain model imports across boundaries
- `test_all_lists_paginated` -- all GET list endpoints accept page/limit
- `test_no_hardcoded_enums` -- no tuple/frozenset constants in models/routers
- `test_mutations_audit_logged` -- ledger writes in all create/update/delete paths

**Security:**
- `test_no_unauthed_endpoints` -- every router has auth dependency or `# PUBLIC-ENDPOINT`
- `test_no_raw_sql` -- no f-string/concatenation SQL in backend
- `test_no_hardcoded_secrets` -- no API_KEY=, SECRET=, PASSWORD= in source
- `test_tenant_scoped_queries` -- every service query includes tenant_id or `# SYSTEM-QUERY`
- `test_no_wildcard_cors` -- CORS uses explicit origin list, not `["*"]`
- `test_security_headers_present` -- middleware includes HSTS, CSP, X-Frame-Options
- `test_no_pii_in_logs` -- log statements don't reference PII field names

**Quality and Reliability:**
- `test_lint_typecheck_clean` -- ESLint + tsc + ruff/mypy pass
- `test_coverage_threshold` -- coverage doesn't drop below floor (e.g. 70%)
- `test_no_critical_cves` -- npm audit + pip-audit: zero HIGH/CRITICAL
- `test_migration_chain_integrity` -- single alembic head, chain is valid
- `test_docker_build_succeeds` -- frontend + backend images build
- `test_openapi_spec_drift` -- checked-in spec matches runtime-generated spec
- `test_no_bare_exception_handlers` -- no silent `except:` or `except Exception:`

> Gate 4 (Deployment Readiness) is designed separately in `docs/specs/2026-05-15-deployment-readiness-gate-design.md`
