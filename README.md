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

Install dependencies:

```powershell
uv sync
```

Windows environment setup:

```powershell
copy .env.example .env
```

Start the API on port 8001:

```powershell
uv run uvicorn organicpath.api.main:create_app --factory --reload --no-access-log --port 8001
```

Open the API documentation:

http://localhost:8001/docs

Health check:

http://localhost:8001/health

Readiness check:

http://localhost:8001/ready

## Checks

Run automated tests:

```powershell
uv run pytest
```

Check code quality:

```powershell
uv run ruff check .
```

Format code:

```powershell
uv run ruff format .
```
## Run locally in one command

You need Docker Desktop running. From a fresh clone:

```bash
docker compose up --build
```

This starts Postgres (with pgvector), Redis, runs the migrations and loads the sample data once, then starts the API.

- API docs: http://localhost:8000/docs
- Liveness: http://localhost:8000/health
- Readiness (checks the database): http://localhost:8000/ready

Stop with `Ctrl+C`, then `docker compose down`. Add `-v` to also delete the database volume.

## Develop and test

| Task | Mac / Linux | Windows |
|---|---|---|
| Run the API with reload | `make dev` | `uv run poe dev` |
| Unit tests (no network) | `make test` | `uv run poe test` |
| Integration tests (needs `docker compose up`) | `make test-integration` | `uv run poe test-integration` |
| Coverage report | `make cov` | `uv run poe cov` |
| Lint and format check | `make lint` | `uv run poe lint` |
