# Capacity plan: OrganicPath

Full corpus target: + annexes, Tracenet manuals and circulars (1,500+ pages)

<!-- generated:start -->
## Measured on my start corpus (2026-11-23 13:44 UTC)

| What | Value |
|---|---|
| Files | 9 |
| Size on disk | 3.3 MB |
| Pages (PDF pages + 1 per 3,000 characters of text/HTML) | 353 |
| Characters of text | 369,388 |
| Estimated tokens (characters / 4) | 92,347 |
| Tokens per page | 262 |
| PDFs with almost no text (scanned? OCR is Day 7) | 0 |
| Files not measured (zip, xlsx, unreadable) | 0 |

## Estimate for the full corpus (target: 1,500 pages)

| What | How | Value |
|---|---|---|
| Scale factor | target / measured | x 4.3 |
| Tokens | measured tokens x scale | 0.39 M |
| Raw files | measured MB x scale | 14 MB |
| Chunks | tokens / 400 x 1.15 overlap | 1,130 |
| Embedding cost, one time | tokens x 1.15 x $0.15 per 1M | $0.07 = Rs 6 |
| Vector storage | chunks x 768 numbers x 4 bytes | 3 MB |
| Text in Postgres | characters x scale x 1.2 | 2 MB |

Assumptions: 4 characters per token, 400-token chunks, 768-dimension embeddings at $0.15 per 1M tokens, Rs 95 per US dollar.
<!-- generated:end -->

## What I conclude

1. At the 1,500-page target, estimated one-time embedding is about Rs 6 (0.39 M tokens at the stated rate), so embedding cost is small at this estimate.
2. The estimate is about 2 MB of text plus 3 MB of vectors. The free Postgres limit is not in this repository, so confirm the dashboard limit before loading.
3. Tokens per page (262) is least certain: characters divided by four is only a rough estimate. Measure with the actual embedding tokenizer.
4. At ten times this target, expect about 3.9 M tokens, Rs 60 embedding cost, 30 MB of vectors and 20 MB of text. Recheck the model price and database limit first.
