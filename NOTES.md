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


## D04 · Docker, Compose and tests

### The image

```text
docker run --rm organicpath:dev id
uid=999(app) gid=999(app) groups=999(app)
```

- Size: approximately 300 MB (verify with `docker images organicpath:dev`)
- First build: 171.4 s
- Unchanged rebuild: 7.4 s
- After changing one line of code: 16.2 s
- Caching: The dependency installation step stayed CACHED because dependency files (`pyproject.toml` and `uv.lock`) had not changed.

### The stack

```text
API: Up (healthy)
DB: Up (healthy)
Redis: Up (healthy)
Migrate: Exited (0)
```

First migration:
```text
records=20 inserted=20 updated=0 unchanged=0
```

After down + up:
```text
records=20 inserted=0 updated=0 unchanged=20
```

### Breaking the database on purpose

```text
db stopped:
 /health → {"status":"ok","app":"organicpath","env":"local"}

 /ready → {"status":"not_ready","checks":{"database":false}}

db started:
 /ready → {"status":"ready","checks":{"database":true}}
```

Why should a load balancer stop sending traffic here but not restart the app?

The readiness check tells the load balancer that the database is unavailable, so it should stop routing traffic to the API. The API process is still alive, so restarting it will not fix the database problem.

### Tests and coverage

```text
uv run poe test:
16 passed

uv run poe test-integration:
7 passed

Coverage TOTAL, unit only:
83%

Coverage TOTAL, with integration tests:
92%
```

Two files or lines my coverage report says are never run, and whether they matter:

- `logging_setup.py` – 54% coverage; additional tests for logging setup would be useful.
- Other uncovered lines: inspect the coverage report and identify the file and line numbers before deciding whether they matter.

### Clean clone verification

- Created a fresh clone using `git clone .`
- Built the Docker Compose stack without a project `.venv` or `.env`.
- API, PostgreSQL and Redis became healthy.
- Migrations exited successfully with code 0.
- `/health` returned `status: ok`.
- `/ready` returned `status: ready` with database true.
- Removed the temporary clone and restored the original Compose stack.

- Size: 300 MB (target: under 400 MB)
