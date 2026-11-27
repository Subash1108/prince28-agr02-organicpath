# Ingestion report

<!-- generated:start -->
_Generated 27 Nov 2026 17:27 from the database._

| What | Count |
|---|---|
| Documents in the database | 27 |
| Pages | 393 |
| Tokens of text (characters ÷ 4) | 148,521 |
| Files the parser gave up on | 2 |
| Documents with an extracted record | 27 |
| Documents whose extraction failed | 0 |

| Queue | Count |
|---|---|
| Ingest jobs started | 3 |
| Items finished (done or skipped) | 27 |
| Items that needed more than one try | 10 |
| Items in the dead-letter list | 6 |

Model calls for extraction: 96 · tokens in 81,553 · tokens out 41,176 · cost at list price Rs 1.88

Last job `cdb751218ff44acaa613b98d1414a365`: 4 requested, 2 ok, 2 failed, 0.3 minutes.

Dead-letter list by stage: parse 4, gave up after 3 tries 2
<!-- generated:end -->

## What I learnt

1. Monday estimated 353 pages, but actual ingestion reached 393 pages.
2. Estimated tokens were 92,347, but actual tokens reached 148,521.
3. The page estimate was close, but token estimate was lower because the corpus grew and text density varied.
