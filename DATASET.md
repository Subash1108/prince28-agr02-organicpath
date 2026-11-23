# Dataset: OrganicPath

Guides farmer groups through organic certification (NPOP and PGS-India): standards, conversion periods, permitted inputs and documentation.

- **Start target:** NPOP standards + PGS-India manual
- **Full target:** + annexes, Tracenet manuals and circulars (1,500+ pages)
- **Collected by:** `scripts/fetch.py` as `examate-student-bot` (https://github.com/Subash1108/prince28-agr02-organicpath): robots.txt respected, at most 4 requests at once, 0.5 s between requests to one site.

## Where the documents come from

- https://apeda.gov.in/
- https://pgsindia-ncof.gov.in/

## Terms I follow

APEDA allows noncommercial internal copying of APEDA-owned material with notices retained; redistribution, modification and full-text display require written permission. PGS-India reuse terms remain unverified, so that source stays pending. The downloader rejects entries marked as pending.

- Every answer links to the original document.
- No personal data is collected.

<!-- generated:start -->
## Sources (generated 2026-11-23 13:44 UTC by scripts/dataset_report.py)

| Source | Licence / terms | Files | MB | Pages* | How | Fetched | Example URL |
|---|---|---|---|---|---|---|---|
| apeda | APEDA permits non-commercial internal copying of APEDA-owned documents with copyright notices retained; no redistribution, modification or full-text answer display without written permission. | 9 | 3.3 | 353 | http+manual | 2026-11-23 | https://npop.apeda.gov.in/sites/default/files/2024-10/NPOP_Eight_Edition_2024.pdf |

**Total:** 9 files, 3.3 MB, 353 pages. Not downloaded: 0 blocked by robots.txt, 0 failed, 1 permission pending, 0 not attempted.

*Pages = PDF pages, plus one page per 3,000 characters of text or HTML.

## Files (first 9 of 9)

The complete list, with a sha256 fingerprint of every file, is `data/manifest.jsonl`.

| # | Title / file | Source | Pages | Fetched | URL |
|---|---|---|---|---|---|
| 1 | NPOP Eighth Edition 2024 | apeda | 248 | 2026-11-23 | https://npop.apeda.gov.in/sites/default/files/2024-10/NPOP_Eight_Edition_2024.pdf |
| 2 | About Organic Products | apeda | 2 | 2026-11-23 | https://npop.apeda.gov.in/about-organic-products |
| 3 | NPOP Announcements | apeda | 3 | 2026-11-23 | https://npop.apeda.gov.in/announcement-cw?field_npop_announcement_type_target_id=60 |
| 4 | NPOP Overview | apeda | 1 | 2026-11-23 | https://organic.apeda.gov.in/npop/ |
| 5 | NPOP Procedures 2024 | apeda | 89 | 2026-11-23 | https://npop.apeda.gov.in/sites/default/files/2025-11/NPOP_PROCEDURES_2024.pdf |
| 6 | Certification Bodies | apeda | 1 | 2026-11-23 | https://organic.apeda.gov.in/Organic-Certification-Bodies |
| 7 | Organic Certification Data 2024-25 | apeda | 3 | 2026-11-23 | https://npop.apeda.gov.in/organic-certification-data-under-npop-2024-25 |
| 8 | NPOP Standards 2014 (historical) | apeda | 4 | 2026-11-23 | https://npop.apeda.gov.in/Revised-NPOP-Standards-2014 |
| 9 | TraceNet Overview | apeda | 1 | 2026-11-23 | https://apeda.gov.in/tracenet |
<!-- generated:end -->

## Known gaps

- The PGS-India manual is still missing because its robots.txt URL returned an HTML fallback page rather than usable rules, and its terms could not be verified. Additional NPOP annexes and TraceNet manuals remain gaps. Nine APEDA-hosted items were collected for non-commercial internal use; do not redistribute or show full text without written permission.
