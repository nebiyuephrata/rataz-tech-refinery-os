# Code Skeletons + Prompt

## Pydantic Models
- `src/rataz_tech/core/models.py`
- `src/rataz_tech/api/models.py`

## Extractor Scaffolds
- `src/rataz_tech/extraction/strategies.py` (pdfplumber, PyMuPDF, Docling, MinerU, Tesseract, Camelot adapters)
- `src/rataz_tech/extraction/triage.py` (decision logic)
- `src/rataz_tech/extraction/factory.py` (strategy + factory wiring)

## Triage Logic
- Config-driven thresholds in `configs/settings.yaml` under `extraction`.
- No hardcoded routing thresholds in code.

## System Prompt
- `prompts/SYSTEM_PROMPT.md`
