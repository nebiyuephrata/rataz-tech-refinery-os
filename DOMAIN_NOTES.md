# DOMAIN_NOTES

## Failure Modes

1. Scanned PDFs with low text signal
- Symptom: minimal extractable text, broken reading order.
- Mitigation: OCR-first route (`tesseract_ocr`) using configurable printable-ratio threshold.

2. Multi-column legal/financial layouts
- Symptom: line-by-line plain extraction loses semantic order.
- Mitigation: layout-aware route (`docling_layout`, `mineru_layout`) for large PDF content.

3. Table-heavy documents
- Symptom: row/column collapse, broken table retrieval.
- Mitigation: table strategy route (`camelot_table`) based on configurable table marker threshold.

4. Bounding box gaps
- Symptom: difficult provenance/audit trail validation.
- Mitigation: preserve page references and spatial metadata on extracted units and query hits.

5. Unsupported/failed optional backends
- Symptom: runtime import failure for optional OSS tools.
- Mitigation: deterministic fallback adapters to `plain_text` with explicit audit events.

## Strategy Decision Tree

1. If printable ratio < `extraction.low_printable_ratio_for_ocr` -> `tesseract_ocr`.
2. Else if table markers >= `extraction.min_table_markers_for_table_strategy` -> `camelot_table`.
3. Else if PDF + `prefer_layout_for_pdf` + chars >= `min_chars_for_layout` -> `docling_layout`.
4. Else -> `extraction.default_strategy`.
5. Fallback chain always uses `extraction.fallback_chain` in configured order.

## Tool Tradeoffs (Open-Source)

| Tool | Strength | Limitation | Best Use |
|---|---|---|---|
| pdfplumber | Reliable text extraction on digital PDFs | weak on scans/layout semantics | fast baseline parsing |
| PyMuPDF | High performance PDF parsing | needs extra logic for layout semantics | throughput-oriented extraction |
| Docling | Strong layout awareness | extra setup/runtime overhead | structured enterprise docs |
| MinerU | layout/reading-order oriented extraction | evolving ecosystem maturity | complex documents |
| Tesseract | local OCR, no paid API | lower quality on noisy scans | scan fallback |
| Camelot | good table extraction on lattice/stream PDFs | struggles on image-based tables | table-heavy digital PDFs |
| BGE-small | inexpensive embeddings | lower quality than large models | local semantic retrieval |
| FAISS | local vector index performance | persistence/ops must be engineered | single-node semantic index |
| SQLite | trivial deployment, auditable | limited write concurrency at scale | MVP metadata/audit store |

## Benchmark Themes For Submission

Track and compare by tool/strategy:
- reading order accuracy
- table extraction fidelity
- bounding box completeness

Use the same document set and fixed evaluation rubric for repeatability.
