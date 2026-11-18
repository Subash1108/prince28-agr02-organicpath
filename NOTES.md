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
