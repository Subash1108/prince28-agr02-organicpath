# OrganicPath

Guides farmer groups through organic certification (NPOP and PGS-India): standards, conversion periods, permitted inputs and documentation.

**Status:** Day 1 foundation (FastAPI skeleton, quality gates). Live URL planned from Day 5.

## Who it's for

Coordinator of a 40-farmer turmeric producer group in Erode seeking organic certification for export.

## The problem

Farmer groups often struggle to understand the rules involved in organic certification. NPOP and PGS-India follow different requirements for conversion periods, permitted agricultural inputs and group certification. Finding the correct information in lengthy standards and annex tables takes considerable time. OrganicPath aims to make these rules easier to understand and help coordinators find reliable information with official references.

## Data sources

- NPOP standards (APEDA, latest edition)
- PGS-India operational manual
- Tracenet documents
- Organic import requirements notes

Official sources:
- https://apeda.gov.in/
- https://pgsindia-ncof.gov.in/

Terms: Public standards documents.

## Hardest problem (my interview story)

Two standards and annex tables: NPOP and PGS-India differ on conversion and group certification. The system must check whether an input is permitted using the correct annex and must clearly identify the applicable standard.

## Signature feature

Input checker: type a fertiliser or pesticide name and see whether it is allowed under NPOP and PGS-India, with the annex cited.

## Target metric

- Input decisions correct for 95%+ of 50 inputs.
- Conversion answers correct for 90%+ of 20 questions.

## Performance target explanation

The initial API response-time targets are designed for a document-based application. I will measure actual performance during testing and adjust the targets based on the results.

## Run it locally

```bash
uv sync
```

Windows:

```powershell
copy .env.example .env
```

Start the API when the FastAPI application entry point is implemented:

```bash
uv run uvicorn organicpath.api.main:create_app --factory --reload
```

Then open http://localhost:8000/docs

## Checks

```bash
uv run pytest
uv run ruff check .
```