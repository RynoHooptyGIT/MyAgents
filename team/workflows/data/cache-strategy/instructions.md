# Cache Strategy Review - Data Architect Workflow

Design and review Redis cache strategy for {project_name}. Validates tenant isolation in cache keys, TTL policies, invalidation, and failure handling.

---

## Step 1: Identify Cache Candidates

1. List read-heavy endpoints in `backend/app/routers/` by call frequency (e.g., `/api/v1/tools/{id}`, `/api/v1/catalogs/`).
2. Identify service queries in `backend/app/services/*.py` hitting the database on every request.
3. Flag expensive computed/aggregated data (dashboard rollups, report summaries).
4. List high read-to-write ratio data: tool catalog, tenant settings, NIST framework definitions.

**Pass**: At least 5 candidates identified with read/write ratio estimates. **Fail**: Fewer than 3 candidates.

---

## Step 2: Select Caching Pattern

| Pattern | When to Use | {project_name} Examples |
|---------|------------|---------------------|
| **Cache-aside** | Read-heavy, brief staleness OK | Tool catalog (`/api/v1/tools/`), user profiles, tenant settings |
| **Write-through** | Must be consistent after writes | Session tokens, intake form state, MFA challenge data |
| **Write-behind** | High-write, eventual consistency OK | Analytics counters, audit log buffering |

- `[CRITICAL]` Every pattern must include tenant-scoped key design; no shared entries across tenants.
- `[WARNING]` Write-behind must document acceptable staleness window and data loss risk.

**Pass**: Every candidate has an assigned pattern with justification. **Fail**: Missing pattern or tenant consideration.

---

## Step 3: Design Key Structure

- Format: `{tenant_id}:{entity}:{sub-type}:{identifier}`
- Examples: `t42:tool:detail:107`, `t42:catalog:list:page1`, `t42:user:profile:55`
- `[CRITICAL]` ALL keys MUST include `tenant_id` as leading prefix — missing prefix is a cross-tenant leak.
- Document wildcard patterns for bulk invalidation (e.g., `t42:catalog:*`).
- `[WARNING]` Verify no service builds cache keys from unsanitized user input.

**Pass**: Key schema documented with tenant prefix enforced. **Fail**: Any key missing tenant_id prefix.

---

## Step 4: Configure TTL Strategy

All values must be configurable via `backend/app/core/config.py`, not hardcoded.

| Data Category | TTL | Examples |
|--------------|-----|----------|
| Static reference | 24h | Tool categories, NIST framework definitions |
| Semi-static | 1h | Tool catalog, tenant configuration |
| User-specific | 15m | Dashboard aggregations, profile data |
| Session | Match session timeout (30m sliding) | Auth sessions, MFA challenges |
| Real-time | 30s-2m | Active intake status, notification counts |

- `[WARNING]` Set MAX TTL ceiling (48h) to prevent stale accumulation.

**Pass**: TTL defined for every candidate; values in config. **Fail**: Hardcoded TTL in service code.

---

## Step 5: Design Invalidation Strategy

1. Map each cached entity to write operations in `backend/app/services/*.py` that trigger invalidation.
2. Use explicit DELETE on cache key in every create/update/delete service method.
3. Implement tag-based invalidation for related entries (tool update invalidates detail + catalog list).
4. `[CRITICAL]` `apply_multi_tenant_rls()` patterns must extend to cache — hits must not bypass tenant filtering.
5. `[WARNING]` Plan tenant-wide cache flush for data reset or migration scenarios.

**Pass**: Every entity has explicit invalidation triggers. **Fail**: Any entity relying solely on TTL.

---

## Step 6: Select Redis Data Structures and Plan Failure Handling

**Data structures** — assign per entity: STRING (serialized JSON), HASH (partial field access), LIST/SET (collections), SORTED SET (ranked data). Choose JSON serialization for dev, MessagePack for production.

**Failure handling**:
1. Degrade gracefully to DB-only when Redis is unreachable — no user-facing errors.
2. Configure pool limits and timeouts in `backend/app/core/config.py` (`REDIS_POOL_SIZE`, `REDIS_TIMEOUT_MS`).
3. Implement circuit breaker: after N consecutive failures, bypass Redis for a cooldown period.
4. Plan post-restart cache warming for critical hot keys (tenant configs, active sessions).
5. `[CRITICAL]` Redis failure must NEVER expose cached data across tenants.
6. `[WARNING]` Implement singleflight pattern to prevent thundering herd on cache miss.

**Pass**: Fallback, circuit breaker, and monitoring documented. **Fail**: Missing fallback or tenant leak in failure path.

---

## Step 7: Produce Report

Output to `{output_folder}/data-architect/cache-strategy.md` with:

1. **Cache Candidates** - table with read/write ratio, latency, and assigned pattern
2. **Key Schema** - namespace documentation with examples
3. **TTL Matrix** - all TTL assignments with config variable names
4. **Invalidation Map** - entity-to-trigger mapping for write-flush relationships
5. **Findings Summary** - issues sorted by severity (`[CRITICAL]` > `[WARNING]` > `[INFO]`)
6. **Action Items** - numbered list of changes required before Redis integration

---

## Step 8: Present Results

- State total cache candidates identified and patterns assigned.
- Highlight top 3 findings by severity — lead with any `[CRITICAL]` tenant isolation gaps.
- Provide estimated latency improvement for highest-impact endpoints.
- Confirm whether the strategy is **APPROVED**, **APPROVED WITH CONDITIONS**, or **BLOCKED**.
