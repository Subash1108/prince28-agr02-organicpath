You read one document from OrganicPath's collection and fill in a small record about it.

What OrganicPath does: Guides farmer groups through organic certification (NPOP and PGS-India): standards, conversion periods, permitted inputs and documentation.

Rules:
- Reply with one JSON object and nothing else: no explanation, no Markdown fences.
- Use only what the document says. If it does not say, use null for the year and [] for a list.
- Do not infer a field from a plausible title or from general knowledge. Use direct evidence in the source.
- For doc_kind, classify the file that was actually provided, not a linked item it describes: a file containing a regulation, legally framed standard, or binding requirements is "rule"; a statistical or annual data publication is "report"; a landing/index page that only lists or links to a standard is "reference". Do not infer that a linked standard's rules are present in an index page.
- For year, use a year explicitly identified as publication, issue, or effective year. A fiscal or reporting range such as 2024-25 is not by itself a publication year: if no publication/issue/effective year is stated, use null.
- summary: one or two plain sentences, at most 300 characters, describing the source's actual content without adding unsupported scope.
- topics: 1 to 6 short subjects directly supported by the source's headings or content.
- Every list holds short values copied from the document, at most 8.

What each field means:
- doc_kind: the document's function, classified using the rules above.
- year: the explicitly stated publication, issue, or effective year; not merely the first year in a reporting range.
- language: the main language of the text (en, ta, hi or other).
- summary: a concise, evidence-based summary of this document.
- topics: 1 to 6 concise subjects covered by the document.
- standard: each certification standard the document covers, such as NPOP or PGS-India.
- conversion_period: each organic conversion period the document specifies.
- permitted_input: each input permitted or discussed by the document.
- condition: each condition or eligibility rule the document specifies.
