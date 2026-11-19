## Migration 2 – GIN Index Rollback Test

**Migration:** add gin index on metadata

**Revision IDs:**
- Migration 1: `a028dde0a177`
- Migration 2: `4e013562c762`

### Commands executed

```cmd
uv run alembic downgrade -1
uv run alembic current
uv run alembic upgrade head
uv run alembic history
```

### Results

1. Successfully downgraded Migration 2.
2. Current revision showed `a028dde0a177` (Migration 1).
3. Successfully upgraded Migration 2 again.
4. Migration history confirmed both revisions.

### Final migration history

```text
a028dde0a177 -> 4e013562c762 (head), add gin index on metadata
<base> -> a028dde0a177, create documents and pages
```

**Status:** PASS – Downgrade and upgrade verified successfully.

Verified results
Test	Expected	Actual	Status
First run	20 inserted	20 inserted	PASS
Second run	20 unchanged	20 unchanged	PASS
Modified record	1 updated, 19 unchanged	1 updated, 19 unchanged	PASS

records=20 inserted=0 updated=0 unchanged=20
records=20 inserted=0 updated=0 unchanged=20
records=20 inserted=0 updated=1 unchanged=19


### EXPLAIN for `?standard=VALUE`

**Planner chooses Seq Scan:**
```text
Seq Scan on documents
Rows Removed by Filter: 20
Execution Time: 1.631 ms
```

**With sequential scan disabled:**
```text
Bitmap Heap Scan on documents
  -> Bitmap Index Scan on ix_documents_metadata_gin
Execution Time: 2.215 ms
```

**Why did the planner choose a Seq Scan on my table?**

My table contains only 20 records. PostgreSQL estimates that reading all rows directly is cheaper than using an index and fetching matching rows.

**When would it switch to the GIN index?**

When the table becomes larger and the query planner estimates that using the GIN index is cheaper than scanning the entire table.

Docker Build Results

Test

Build Time

Result

Initial Docker build

171.4 seconds

Success

Unchanged rebuild

7.4 seconds

Cached

Code-change rebuild

16.2 seconds

Success



### Docker Compose verification

- PostgreSQL container started and passed its healthcheck.
- Redis container started and passed its healthcheck.
- API container started and passed its healthcheck.
- Migration completed successfully (`Exited (0)`).
- `/health` returned `{"status":"ok","app":"organicpath","env":"local"}`.
- `/ready` returned `ready` when the database was available.
- After stopping PostgreSQL, `/health` remained `ok` and `/ready` returned `not_ready`.
- After restarting PostgreSQL, `/ready` returned `ready` without restarting the API.
- After `docker compose down` and `docker compose up -d`, all 20 records remained unchanged.
- Idempotency verification: `records=20 inserted=0 updated=0 unchanged=20`.
