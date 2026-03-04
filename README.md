# Rataz Tech Refinery-OS

Deterministic, open-source-first document intelligence engine scaffold with:
- strict stage boundaries: extraction, normalization, chunking, indexing, querying
- Strategy + Factory + Adapter patterns
- Pydantic typed contracts for all pipeline I/O
- audit events and spatial provenance retention
- run-level `trace_id` propagation across all stage audit events
- graceful low-confidence handling and optional escalation
- built-in localization (`en`, `am`)

## Quickstart

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
python -m rataz_tech.main
```

## UI (Kivy)

```bash
pip install -e ".[ui]"
rataz-tech-ui
```

Set config path with:

```bash
export RATAZ_TECH_CONFIG=configs/settings.yaml
```

## API (FastAPI)

```bash
pip install -e ".[api]"
rataz-tech-api
```

Environment variables:
- `RATAZ_TECH_CONFIG` for config file path
- `RATAZ_TECH_API_HOST` default `127.0.0.1`
- `RATAZ_TECH_API_PORT` default `8000`

## Tests

```bash
pytest -q
```

## CI/CD

- CI (`.github/workflows/ci.yml`): runs on every push/PR to `main`, executes lint (`ruff`) and tests (`pytest`) on Python 3.11 and 3.12.
- CD (`.github/workflows/cd.yml`): runs on version tags (`v*`) or manual trigger, builds package artifacts and publishes a GitHub Release for tags.

## Traceability And Agents

- You do not need LangChain agents for critical traceability.
- Start with deterministic pipeline tracing: run-level `trace_id`, stage-level audit events, and per-chunk provenance.
- Add agent orchestration later only for bounded tasks (for example, ambiguity resolution) behind a strategy interface, while preserving the same typed audit/provenance contracts.

## Configuration

All runtime thresholds and component selections are in `configs/settings.yaml`.
