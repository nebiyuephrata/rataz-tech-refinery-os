# Rataz Tech Refinery-OS

Open-source document intelligence engine for deterministic extraction, provenance-preserving transformation, and auditable semantic retrieval.

## Stack (Free & Minimal)

| Layer | Tool |
|---|---|
| PDF reading | pdfplumber / PyMuPDF (implemented for Tier A) |
| Layout extraction | Docling / MinerU adapters |
| OCR | Tesseract adapter |
| Table extraction | Camelot adapter |
| Embeddings | BGE-small (planned) |
| Vector store | FAISS local (planned) |
| DB | SQLite (planned persistent audit) |
| API | FastAPI |

## Submission Artifacts

- [DOMAIN_NOTES.md](/home/rata/Documents/Ephrata/work/10Acadamy/training/rataz-Wordz/DOMAIN_NOTES.md)
- [Architecture Diagram](/home/rata/Documents/Ephrata/work/10Acadamy/training/rataz-Wordz/docs/ARCHITECTURE.md)
- [Code Skeletons + Prompt](/home/rata/Documents/Ephrata/work/10Acadamy/training/rataz-Wordz/docs/CODE_SKELETONS.md)
- [Cost Estimation](/home/rata/Documents/Ephrata/work/10Acadamy/training/rataz-Wordz/docs/COST_ESTIMATION.md)
- [Test Results](/home/rata/Documents/Ephrata/work/10Acadamy/training/rataz-Wordz/docs/TEST_RESULTS.md)

## MVP Features

- Five executable stages: triage, structure extraction, semantic chunking, page index builder, query interface.
- Strategy + Factory + Adapter patterns.
- Config-driven extraction triage and fallback chain.
- Pydantic typed outputs across pipeline and API.
- Trace IDs + request audit trail.
- Persistent storage backends for audit/extraction history (`memory` and `sqlite`).
- Amharic + English localization support.
- PageIndex tree build and query (`/pageindex/{document_id}`, `/pageindex/query`).
- Vector ingestion stores full per-chunk metadata (`chunk_type`, `page_refs`, `content_hash`, `parent_section`).
- FactTable extraction persists numerical key-value facts into SQLite with SQL retrieval via `/query/structured`.

## Storage Rubric Evidence

- Vector metadata ingestion:
  - [/home/rata/Documents/Ephrata/work/10Acadamy/training/rataz-Wordz/src/rataz_tech/indexing/strategies.py](/home/rata/Documents/Ephrata/work/10Acadamy/training/rataz-Wordz/src/rataz_tech/indexing/strategies.py)
  - [/home/rata/Documents/Ephrata/work/10Acadamy/training/rataz-Wordz/tests/test_indexing_metadata_ingestion.py](/home/rata/Documents/Ephrata/work/10Acadamy/training/rataz-Wordz/tests/test_indexing_metadata_ingestion.py)
- FactTable extractor + SQLite schema + SQL query path:
  - [/home/rata/Documents/Ephrata/work/10Acadamy/training/rataz-Wordz/src/rataz_tech/indexing/facts.py](/home/rata/Documents/Ephrata/work/10Acadamy/training/rataz-Wordz/src/rataz_tech/indexing/facts.py)
  - [/home/rata/Documents/Ephrata/work/10Acadamy/training/rataz-Wordz/src/rataz_tech/api/services.py](/home/rata/Documents/Ephrata/work/10Acadamy/training/rataz-Wordz/src/rataz_tech/api/services.py)
  - [/home/rata/Documents/Ephrata/work/10Acadamy/training/rataz-Wordz/tests/test_storage_facttable_sqlite.py](/home/rata/Documents/Ephrata/work/10Acadamy/training/rataz-Wordz/tests/test_storage_facttable_sqlite.py)

## Run Locally

```bash
pip install -U -r requirements.txt
pip install -e .
uvicorn rataz_tech.api.server:app --reload
```

## Docker

```bash
docker build -t refinery-os .
docker run -p 8000:8000 refinery-os
```

## API Endpoints

- `GET /health`
- `POST /ingest`
- `POST /ingest/file`
- `POST /query`
- `POST /query/agent`
- `POST /query/structured`
- `GET /audit/requests`
- `POST /audit/claim`
- `GET /extractions/{document_id}`
- `GET /pageindex/{document_id}`
- `POST /pageindex/query`

## Frontend (Vite + React + TypeScript + Tailwind)

Modern neon UI with:
- drag/drop file upload to `/ingest/file`
- realtime request feed (polling `/audit/requests`)
- extraction stage status timeline
- extracted table JSON viewer
- PageIndex tree viewer from `/pageindex/{document_id}`
- query panel with provenance-ready responses
- dark/light theme toggle
- React hooks with memoization (`useMemo`) and stable handlers (`useCallback`)

Run frontend:

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

## Config

Runtime controls are in `configs/settings.yaml`:
- extraction routing thresholds and fallback chain
- query confidence/escalation controls
- API auth, upload limits, and audit retention
- storage backend (`memory` or `sqlite`) and SQLite path/retention caps

## Tier A Backends

Tier A fast text now attempts real PDF parsing in this order:
1. `pdfplumber`
2. `PyMuPDF`
3. deterministic plain-text fallback

## Test

```bash
uv run --with pytest pytest -q
```

## Benchmark

Run extraction benchmark on a local corpus (`*.txt` naming pattern like `NF_01.txt`, `SL_01.txt`, `MA_01.txt`, `TF_01.txt`):

```bash
rataz-tech-benchmark --corpus ./corpus --output docs/TEST_RESULTS.generated.md
```
