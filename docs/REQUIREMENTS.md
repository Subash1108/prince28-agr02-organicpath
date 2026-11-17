# Requirements: OrganicPath

## Functional (what it does)

1. **Question Answering:** A user can ask a question in plain English and get an answer drawn from the official organic certification sources.

2. **Source Citations:** Every certification-related answer must cite the document and page number or section from which the information was obtained.

3. **Unknown Answer Handling:** If the documents do not contain the answer, the product must respond with "I don't know" instead of guessing.

4. **Input Checker:** Users can enter a fertiliser or pesticide name and check whether it is allowed under NPOP and PGS-India, with the relevant annex cited.

5. **Document Search:** Users can browse and search the underlying records through `GET /v1/documents`.

## Non-functional (how well, with numbers)

| # | Quality | Target | How I will measure it |
|---|---|---|---|
| 1 | Speed: record lookups | p95 under 500 ms for GET /v1/documents | Load test (Week 6) |
| 2 | Speed: answers | p95 under 5 seconds for a full answer; first token under 1.5 seconds | Traces (Week 5) |
| 3 | Accuracy | Input decisions correct for 95%+ of 50 inputs; conversion answers correct for 90%+ of 20 questions | Golden question set (Weeks 4 and 5) |
| 4 | Cost | Under Rs 0.50 per answered question | llm_calls table (Week 2) |
| 5 | Availability | 99% monthly uptime of the live URL | Uptime monitor from Day 5 |

## Target adjustment explanation

I changed the record lookup target from 300 ms to 500 ms and the full-answer target from 4 seconds to 5 seconds. These are initial targets for a document-based application, and I will review them after performance testing.

