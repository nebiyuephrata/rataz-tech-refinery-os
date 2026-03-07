# Rataz Tech Refinery-OS

Open-source document intelligence engine for deterministic extraction, provenance-preserving transformation, and auditable semantic retrieval.

## Stack (Free & Minimal)

| Layer | Tool |
|---|---|
| PDF reading | pdfplumber / PyMuPDF adapters |
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
- `GET /audit/requests`
- `GET /extractions/{document_id}`
- `GET /pageindex/{document_id}`
- `POST /pageindex/query`

## Config

Runtime controls are in `configs/settings.yaml`:
- extraction routing thresholds and fallback chain
- query confidence/escalation controls
- API auth, upload limits, and audit retention
- storage backend (`memory` or `sqlite`) and SQLite path/retention caps

## Test

```bash
uv run --with pytest pytest -q
```
