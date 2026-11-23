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


## D03 – PostgreSQL

### Database setup
- Migrated OrganicPath from the initial database setup to PostgreSQL.
- Configured the PostgreSQL connection using environment variables.
- Used Neon PostgreSQL for the deployed database.

### Migrations
- Created two database migrations using Alembic.
- Created and updated database tables through migrations.
- Verified that migrations were applied successfully.

### Database loader
- Implemented `scripts/load_db.py` to load sample records into PostgreSQL.
- Tested repeated loader execution to verify idempotency.

### Query performance
- Added database indexes for frequently queried fields.
- Used `EXPLAIN` to inspect query execution plans.

### Verification
- Verified database connectivity.
- Verified API database reads and filtering.
- Confirmed that the deployed `/ready` endpoint reports database connectivity.

### Learning
- Understood PostgreSQL, migrations, idempotent data loading, indexes and query execution plans.

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

## D05 · CI/CD and going live

- Live URL: https://organicpath.onrender.com
- CI run for pull request 1: https://github.com/Subash1108/prince28-agr02-organicpath/actions
- First deploy that ran by itself: ([paste CD #2 run link](https://github.com/Subash1108/prince28-agr02-organicpath/actions/runs/44738255984))
- Merge clicked at __:__ → "Smoke test passed" at __:__ → lead time: ___ min

### Smoke test output from that CD run

```text
dc3f323bb95ac03141116196b353cfac788652c4  Merge pull request #6 from Subash1108/fix/health-head-monitor
fa06e46b85d4e9e66312df5e64de8118cc3aaa09  fix: support HEAD requests on health endpoint
06baee806dc4693a99cd0943018d6c706904e239  Merge pull request #5 from Subash1108/feat/day-05-cd
888b5da6a3c3391593604deb501c3e4ca4f65335  ci: deploy every green main to render with migrations and smoke test
```

### Rollback drill

- Rolled back to sha `8c80279445655090478a40fb6e9801214624aac6` : started __:__, smoke passed __:__ (47 seconds)
- Rolled forward to sha `dc3f323bb95ac03141116196b353cfac788652c4` : 50 seconds
- During the rollback, the database stayed on the newer schema. Why is that safe here?
  The rollback skips migrations and changes only the application image.
  The newer database schema remains unchanged, provided it is backward-compatible with the older application version.

### Where my secrets live

- Neon string: GitHub Secret DATABASE_URL + Render environment. Not in Git, not in the image.
- Render deploy hook: GitHub Secret RENDER_DEPLOY_HOOK only.

### Monitoring

- UptimeRobot checks /health every 5 minutes; alerts go to my email.
- One thing that would make my live app faster on its first request: Keep the Render instance warm to reduce cold-start delay.
