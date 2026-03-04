# Cost Estimation

## Strategy Cost Bands

| Strategy | Compute Cost | Latency Cost | Notes |
|---|---|---|---|
| plain_text | Low | Low | Best throughput baseline |
| pdfplumber_text / pymupdf_text | Low | Low | PDF parsing with minimal overhead |
| docling_layout / mineru_layout | Medium | Medium | Better structure at higher CPU/RAM cost |
| camelot_table | Medium | Medium | Focused table extraction pass |
| tesseract_ocr | High | High | OCR is expensive, use as fallback |

## Query Path Cost

| Query Mode | Cost | Notes |
|---|---|---|
| Deterministic lexical retrieval | Low | default production path |
| Optional vector retrieval (BGE-small + FAISS) | Medium | better semantic recall |
| LLM escalation | High | disabled by default |

## Environment Tiers

| Tier | Suggested Stack | Cost Profile |
|---|---|---|
| Low | plain_text + deterministic query | minimal |
| Medium | layout adapters + deterministic query | balanced |
| High | layout + OCR + vector + optional LLM escalation | maximum quality, highest cost |
