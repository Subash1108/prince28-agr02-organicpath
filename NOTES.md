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

## D06 · Collecting the corpus

- Start target: NPOP standards + PGS-India manual
- Collected locally today: 9 files, 353 pages, 3.3 MB (from DATASET.md); PGS-India manual is still missing.
- Doors used: URL list for eight APEDA downloads; one existing NPOP PDF was registered by hand.

### Licence check

| Source | Licence or terms, in my words | May I show full text in answers? |
|---|---|---|
| APEDA | APEDA permits non-commercial internal copying of APEDA-owned documents if notices are retained. Redistribution, modification and other use need written permission. | No; link the original and paraphrase. |
| PGS-India | Could not verify copyright terms; site policy page was inaccessible. | No; do not collect until terms are confirmed. |

### robots.txt

- APEDA hosts (`npop.apeda.gov.in`, `apeda.gov.in`, `organic.apeda.gov.in`): `User-agent: *`; disallows system, admin, login and search paths. The listed document paths are allowed.
- PGS-India: `robots.txt` returned an HTML page (HTTP 200), not valid robots rules. I treated the site as blocked and did not request its manual.

### Kill and resume

- Run 1: interrupted after 2 files were downloaded.
- Run 2: downloaded=6 skipped=3; completed the remaining APEDA entries.
- Run 3: downloaded=0 skipped=9.

### Capacity (from docs/CAPACITY.md)

- Tokens per page, estimated: 262 (characters divided by four).
- Full corpus target: 0.39 M tokens, about 1,130 chunks, embedding about Rs 6, vectors about 3 MB.
- The low estimated embedding cost surprised me most. It depends on approximate token counts, model price and exchange rate.

### One thing that went wrong today, and how I fixed it

- The sandboxed HTTP client could not retrieve robots.txt and correctly blocked the URLs. After separately verifying APEDA robots rules and terms, I reran the approved APEDA-only fetch with network access and resumed from the completed files.

## D07 · Parser comparison

<!-- parsers:start -->
| File | Parsers (A / B) | Pages | A found | B found | Time (A / B) | Better, why |
|---|---|---|---|---|---|---|
| NPOP_Eight_Edition_2024.pdf | PyMuPDF / pypdf | 248 | 358,765 chars, 539 headings, 50 tables | 347,333 chars, 0 headings, 0 tables | 11.20 s / 9.63 s | |
| npop-procedures-2024-6de50cba.pdf | PyMuPDF / pypdf | 89 | 124,668 chars, 49 headings, 28 tables | 114,665 chars, 0 headings, 0 tables | 2.05 s / 5.08 s | |
| revised-npop-standards-2014-ed784840.html | trafilatura / strip tags | 2 | 13,149 chars, 1 headings, 0 tables | 14,571 chars, 0 headings, 0 tables | 0.32 s / 0.01 s | |
| tracenet-4febcc3c.html | trafilatura / strip tags | 2 | 1,043 chars, 2 headings, 0 tables | 4,630 chars, 0 headings, 0 tables | 0.12 s / 0.01 s | |
| organic-certification-data-under-npop-2024-25-fe | trafilatura / strip tags | 7 | 10,445 chars, 4 headings, 0 tables | 11,039 chars, 0 headings, 0 tables | 0.24 s / 0.01 s | |
| announcement-cw-5ba32715.html | trafilatura / strip tags | 2 | 4,821 chars, 2 headings, 0 tables | 8,846 chars, 0 headings, 0 tables | 0.10 s / 0.01 s | |
| about-organic-products-e5aad613.html | trafilatura / strip tags | 4 | 2,970 chars, 5 headings, 0 tables | 5,892 chars, 0 headings, 0 tables | 0.10 s / 0.01 s | |
| npop-bf521382.html | trafilatura / strip tags | 4 | 3,378 chars, 5 headings, 0 tables | 4,610 chars, 0 headings, 0 tables | 4.06 s / 0.00 s | |
| organic-certification-bodies-1c59f389.html | trafilatura / strip tags | 4 | 1,800 chars, 5 headings, 0 tables | 2,990 chars, 0 headings, 0 tables | 0.07 s / 0.00 s | |
<!-- parsers:end -->

Only 9 eligible PDF/HTML files were available for comparison; all 9 were downloaded and present locally.

### D07 · Parsing my corpus

- Files in the manifest: 9 · parsed: 9 · failed: 0 · pages in Postgres: 362
- Parsing coverage: 100% of downloaded files present on disk (9/9)

### Failures by reason

| Reason | Files | What I did |
|---|---:|---|
| None | 0 | No parse failures; retry was not needed. |

- The one I fixed: none; 0 failures out of 9 downloaded files.

### What I saw when I read my parsed pages

- A page where the heading path is right: NPOP Eighth Edition 2024, page 8, `[TABLE OF CONTENTS]`.
- Something that came out wrong: NPOP Eighth Edition 2024, pages 1-5 contain roman-numbered preliminaries; page 5 starts introductory prose but inherits `EIGHTH EDITION : 2024` / `Department of Commerce` as its path.
- A table: NPOP Eighth Edition 2024, page 7, table of contents is a Markdown grid; some cells contain `<br>` markup and generated column names.

### My parser choice

- For PDFs I use PyMuPDF because it found 539 headings and 50 tables in the 248-page NPOP edition; pypdf found 0 of each. On the 89-page Procedures PDF, PyMuPDF found 49 headings and 28 tables, while pypdf found 0 of each. PyMuPDF took 7.34 s vs 5.68 s on the larger edition and 2.66 s vs 2.47 s on Procedures.
- A kind of document in my corpus that neither parser handles well: scanned PDFs without a text layer (none in this current corpus); the current PDF comparisons also show pypdf does not infer headings or tables.

### One thing that went wrong today, and how I fixed it

- `uv` was unavailable, so I used the project virtual environment. The sandbox initially blocked pytest temporary directories; after running pytest with normal Windows temp access, all 74 unit tests passed. I also changed the pasted Tamil fixture to Unicode escapes to preserve its text. Ruff checks pass.
- The parser upsert was exercised by refreshing the seven HTML documents in Neon and checking their stored pages, heading paths, document count, and parse failures. The disposable-Postgres integration test suite (including the new page-replacement regression test) was not run in this final review; the Neon database was not used as a destructive test fixture.


A (PyMuPDF) – detected 539 headings and 50 tables; pypdf detected none.
A (PyMuPDF) – detected 49 headings and 28 tables; pypdf detected none.
A (Trafilatura) – extracted a heading; strip-tags found none.
A (Trafilatura) – extracted 2 headings; strip-tags found none.
A (Trafilatura) – extracted 4 headings; strip-tags found none.
A (Trafilatura) – extracted 2 headings; strip-tags found none.
A (Trafilatura) – extracted 5 headings; strip-tags found none.
A (Trafilatura) – extracted 5 headings; strip-tags found none.
A (Trafilatura) – extracted 5 headings; strip-tags found none.


English vs Tamil token experiment:
Hi baseline: 235 tokens
English message: 243 - 235 = 8 tokens
Tamil message: 257 - 235 = 22 tokens
Tamil uses 2.75x more tokens than English.

Question: What price will organic turmeric fetch next season?
Observed response: "I’m sorry, but I can’t provide that."
Result: Did not invent a price, but failed to use the required
"I am not sure" wording.

Off-topic question:
Who won the 2011 cricket world cup?

Observed response:
"I'm sorry, but that question is outside the scope of OrganicPath."

Result: PASS — declined in one sentence.

Question: What is NPOP?
Observed answer: National Programme for Organic Production.
Result: Relevant answer, but source-document accuracy not verified.
Provider: Groq (fallback=YES).

Question: What is the conversion period for perennial crops under NPOP?
Observed answer: At least 36 months (3 years).
Result: Relevant answer, but source-document accuracy not verified.
Provider: Gemini (fallback=no).

Fallback test 1:
Primary model: gemini-no-such-model
Fallback provider: Groq
Fallback: YES
Observed answer: 5 years
Note: Different models gave inconsistent conversion periods.

Fallback test:
- 5 requests sent with invalid Gemini model.
- All requests fell back to Groq successfully.
- fallback=YES in all responses.
- Gemini returned HTTP 404 on every request.
- Circuit breaker did not visibly skip Gemini after 4 failures.
- Circuit breaker behavior needs investigation.

## Day 08 - Task 5: Break It on Purpose

### Token experiment
- Hi baseline: 235 tokens
- English: 243 tokens
- Tamil: 257 tokens
- English message tokens: 8
- Tamil message tokens: 22
- Tamil/English ratio: 2.75x

### Uncertainty and off-topic tests
- Organic turmeric price: Did not invent a price, but did not use the required "I am not sure" wording.
- Cricket question: Correctly declined as outside OrganicPath scope.
- NPOP answer: Source-document accuracy not yet verified.
- Perennial conversion period: Conflicting answers observed (3 years and 5 years). Source verification pending.

### Fallback and circuit breaker
- Five requests tested with invalid Gemini model.
- All five successfully fell back to Groq.
- Gemini HTTP 404 occurred on all five attempts.
- Circuit breaker did not visibly stop Gemini attempts after repeated failures.
- Restored original Gemini model.
- Original Gemini model produced ReadTimeout; Groq fallback succeeded.

### Usage and database verification
- Total calls: 28
- Errors: 13
- Fallbacks: 14
- Input tokens: 3611
- Output tokens: 2480
- Estimated cost: Rs. 0.1395
- SQL verification confirmed Gemini errors and Groq fallback records.

@'

### D08 · LLM gateway

- Primary: gemini-3.8-flash (Gemini) · fallback: openai/gpt-oss-20b (Groq)
- Laptop NPOP question: first words after 35.09 s, total 35.67 s, tokens in 340 / out 187, cost Rs 0.007752
- Live URL (second, awake request): pending
- Day 1 target: under 1.5 s

### Tokens: English against Tamil

| Message | tokens in |
|---|---:|
| Hi (baseline: mostly my system prompt) | 235 |
| English sentence | 243 |
| Same sentence in Tamil | 257 |

- English message tokens: 8
- Tamil message tokens: 22
- Tamil message needs about 2.75 times the tokens of English.

### What the model does without my documents

- Organic turmeric price: It did not invent a price, but did not use the required "I am not sure" wording.
- Detail that was inconsistent: NPOP perennial conversion period → Gemini answered 3 years and Groq answered 5 years → verified NPOP Eighth Edition section 3.1.3(ii): at least 3 years. Prompt updated with the verified rule.
- Off-topic cricket question: Correctly declined as outside OrganicPath scope.

### Fallback and circuit breaker

- With the primary broken: provider Gemini (invalid test model), fallback Groq.
- Three Gemini failures occurred before the fourth request skipped Gemini.
- Log confirmed: "llm circuit open; skipping provider gemini".
- After cooldown, half-open probe retried Gemini and failed. Re-opening after that failure still needs confirmation.
- Original model setting restored to gemini-3.8-flash.

### The bill

- /v1/usage snapshot: calls 28, errors 13, fallbacks 14, cost Rs 0.1395.
- Average per call in that snapshot: approximately Rs 0.005.
- Day 1 target: under Rs 0.50.

### One thing that went wrong today, and how I fixed it

- Gemini and Groq gave conflicting NPOP conversion-period answers. Verified the NPOP source and added the correct rule to the system prompt.
- Circuit breaker did not visibly skip the primary provider initially. Updated the gateway and verified the open-circuit skip log.
'@ | Add-Content NOTES.md
