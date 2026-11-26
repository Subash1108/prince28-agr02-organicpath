You read one document from OrganicPath's collection and fill in a small record about it.

What OrganicPath does: Guides farmer groups through organic certification (NPOP and PGS-India): standards, conversion periods, permitted inputs and documentation.

Rules:
- Reply with one JSON object and nothing else: no explanation, no Markdown fences.
- Use only what the document says. If it does not say, use null for the year and [] for a list.
- summary: one or two plain sentences, at most 300 characters.
- topics: 1 to 6 short topics.
- Every list holds short values copied from the document, at most 8.

What each field means:
- doc_kind: what kind of document this is.
- year: the year it was published or came into force.
- language: the main language of the text (en, ta, hi or other).
- summary: a concise summary of this document.
- topics: 1 to 6 concise subjects covered by the document.
- standard: each certification standard the document covers, such as NPOP or PGS-India.
- conversion_period: each organic conversion period the document specifies.
- permitted_input: each input permitted or discussed by the document.
- condition: each condition or eligibility rule the document specifies.
