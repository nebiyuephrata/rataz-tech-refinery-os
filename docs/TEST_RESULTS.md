# Test Results

## Unit/Integration Status

| Suite | Status | Summary |
|---|---|---|
| `tests/test_pipeline.py` | Pass | end-to-end ingest/query + localization + trace |
| `tests/test_api.py` | Pass | health, ingest, file ingest, query, audit, auth guard |

## Extraction Quality Benchmark Template

Use this table when running doc benchmark sets.

| Document Type | Strategy | Reading Order Accuracy | Table Fidelity | Bounding Box Completeness | Notes |
|---|---|---:|---:|---:|---|
| Native PDF (forms) | docling_layout | TBD | TBD | TBD | |
| Native PDF (tables) | camelot_table | TBD | TBD | TBD | |
| Scanned PDF | tesseract_ocr | TBD | TBD | TBD | |
| Mixed enterprise packet | auto_triage | TBD | TBD | TBD | |

## Current Summary

- Deterministic fallback chain is active.
- Trace IDs and request-level audit records are emitted for API calls.
- MIME/size constraints and API-key guard are verified.
