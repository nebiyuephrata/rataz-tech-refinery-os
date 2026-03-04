# Rataz Tech Refinery-OS

Deterministic, open-source-first document intelligence engine scaffold with:
- strict stage boundaries: extraction, normalization, chunking, indexing, querying
- Strategy + Factory + Adapter patterns
- Pydantic typed contracts for all pipeline I/O
- audit events and spatial provenance retention
- graceful low-confidence handling and optional escalation
- built-in localization (`en`, `am`)

## Quickstart

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
python -m rataz_tech.main
```

## Tests

```bash
pytest -q
```

## Configuration

All runtime thresholds and component selections are in `configs/settings.yaml`.
