# Query Optimization - Data Architect Workflow

Optimize SQL queries for {project_name} using EXPLAIN ANALYZE, index strategy, and N+1 detection. Targets services in `backend/app/services/*.py` and indexes in `backend/alembic/versions/`.

---

## Step 1: Identify Target Queries

1. Gather slow queries from application logs or `pg_stat_statements` (sort by total_time descending).
2. Prioritize by **frequency x latency** — highest combined impact first.
3. Note the calling service file (`backend/app/services/*.py`) and API endpoint for each query.
4. Verify queries use `AsyncSession` with SQLAlchemy 2.0 `select()` patterns (not legacy `session.query()`).
5. `[INFO]` Document baseline metrics: current p50 and p95 latency per target query.

**Pass**: At least 5 target queries identified with service file, endpoint, and baseline latency.
**Fail**: No slow query data available or fewer than 3 targets identified.

---

## Step 2: Run EXPLAIN ANALYZE

1. Execute `EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)` for each target query.
2. Record planning time, execution time, rows estimated vs. actual, and buffer hits.
3. `[CRITICAL]` Flag nodes with estimation errors > 10x — indicates stale statistics or missing ANALYZE.
4. `[WARNING]` Flag sequential scans on tables with > 10k rows where an index scan is expected.
5. Flag nested loop joins on result sets > 1,000 rows — consider hash or merge joins.

**Pass**: All target queries profiled with documented plan analysis.
**Fail**: Any query skipped or run without BUFFERS output.

---

## Step 3: Detect N+1 Query Patterns

1. Search `backend/app/services/*.py` for loops containing `await db.execute()` or `await session.execute()`.
2. Check for relationship access inside loops without eager loading (e.g., `for item in items: item.related`).
3. `[CRITICAL]` Flag any endpoint issuing > 10 queries per request.
4. Recommend: `selectinload()` for one-to-many, `joinedload()` for many-to-one, `subqueryload()` for deep chains.
5. `[WARNING]` Verify eager loading does not over-fetch — avoid `joinedload()` on large collections.

**Pass**: No N+1 patterns, or all detected patterns have fix plans. **Fail**: N+1 on high-traffic endpoint without remediation.

---

## Step 4: Review Index Strategy

1. List indexes on involved tables via `pg_indexes` or scan `backend/alembic/versions/` for `op.create_index` calls.
2. `[CRITICAL]` Verify `tenant_id` is the leading column on all multi-tenant indexes.
3. Check for missing indexes on WHERE clause columns and JOIN keys from Step 2.
4. Evaluate composite index column ordering — highest-selectivity column first.
5. `[WARNING]` Identify unused indexes (check `pg_stat_user_indexes` for `idx_scan = 0`).
6. Consider partial indexes for common filters (e.g., `WHERE is_active = true`, `WHERE deleted_at IS NULL`).

**Pass**: All EXPLAIN plans show index scans on tenant-scoped queries; no missing indexes on hot paths.
**Fail**: Sequential scan on tenant-scoped table or missing index on JOIN key.

---

## Step 5: Optimize Query Patterns

1. Replace correlated subqueries with JOINs or CTEs where the planner benefits.
2. `[CRITICAL]` Verify `apply_multi_tenant_rls()` is applied — `tenant_id` filter must appear before expensive operations.
3. Verify `escape_ilike_pattern()` is used for all ILIKE queries to prevent wildcard injection.
4. `[WARNING]` Validate pagination uses keyset (WHERE id > last_id), not OFFSET on large datasets.
5. Assess whether filtering can be pushed to database instead of Python-side post-filtering.

**Pass**: All queries use tenant-scoped filters early; no correlated subqueries on hot paths.
**Fail**: Missing tenant filter or OFFSET pagination on table with > 50k rows.

---

## Step 6: Validate Multi-Tenant Performance

1. Test queries against tenants with small (100), medium (10k), and large (100k+) row counts.
2. `[CRITICAL]` Confirm `tenant_id` filter is applied before JOINs and aggregations in the plan.
3. Verify index scans use `tenant_id` prefix consistently across all data volumes.
4. `[WARNING]` Check for lock contention in concurrent multi-tenant workloads.

**Pass**: Performance degrades linearly with data volume. **Fail**: > 5x degradation between medium and large tenants.

---

## Step 7: Produce Report

Output to `{output_folder}/data-architect/query-optimization.md` with:

1. **Target Queries** - table with service file, endpoint, and baseline latency
2. **EXPLAIN Analysis** - plan issues: sequential scans, estimation errors, nested loops
3. **N+1 Detections** - patterns with file, line, and recommended fix
4. **Index Recommendations** - CREATE INDEX statements ready for Alembic migration
5. **Before/After Metrics** - execution time, buffer hits, rows scanned comparison
6. **Findings Summary** - issues sorted by severity (`[CRITICAL]` > `[WARNING]` > `[INFO]`)
7. **Action Items** - prioritized: index additions, query rewrites, eager loading changes

---

## Step 8: Present Results

- State total queries analyzed and optimizations applied.
- Highlight top 3 findings by severity — lead with `[CRITICAL]` missing tenant filters or N+1 patterns.
- Report aggregate latency improvement (total p95 reduction across optimized queries).
- Confirm whether performance is **ACCEPTABLE**, **NEEDS OPTIMIZATION**, or **BLOCKED ON INDEX CHANGES**.
