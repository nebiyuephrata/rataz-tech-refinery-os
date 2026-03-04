# DOMAIN_NOTES

## Corpus Scope

The notes below are grounded in four document classes used in the project benchmark corpus:

- Native financial: `NF-01`, `NF-02`
- Scanned legal: `SL-01`, `SL-02`
- Mixed assessment packet: `MA-01`, `MA-02`
- Table-heavy fiscal reports: `TF-01`, `TF-02`

If your local corpus uses different filenames, map these IDs to your actual files and keep the same class labels.

## 1) Failure Mode Analysis (Empirical)

| Class | Corpus Docs | Observed Failure | Why It Happens (Technical) | Primary Mitigation |
|---|---|---|---|---|
| Native financial | `NF-01`, `NF-02` | Reading order drift in multi-column sections | Naive line concatenation ignores x/y block grouping; headers/footers leak into body | Layout-aware route (`docling_layout` or `mineru_layout`) |
| Scanned legal | `SL-01`, `SL-02` | Missing clauses and broken entity strings | Source text layer is absent; OCR noise from skew/low contrast causes token fragmentation | OCR-first (`tesseract_ocr`) + confidence checks |
| Mixed assessment | `MA-01`, `MA-02` | Inconsistent page behavior (some digital, some scan) | Heterogeneous pages require page-level strategy selection; single-pass strategy underfits | Triage + fallback chain per document characteristics |
| Table-heavy fiscal | `TF-01`, `TF-02` | Row/column collapse, totals detached | Plain text extraction linearizes table geometry; merged cells lose structure | `camelot_table` first, then layout fallback |

## 2) Extraction Strategy Decision Tree

### Classification dimensions

- Origin type: digital text layer vs scanned image layer
- Layout complexity: single-column vs multi-column/blocks/forms
- Domain characteristics: table density, legal clause density, mixed-page heterogeneity

### Decision tree with fallback/escalation

1. If printable ratio `< extraction.low_printable_ratio_for_ocr`:
- Route to `tesseract_ocr`
- Escalate to layout parser if OCR confidence is low or empty output

2. Else if table markers `>= extraction.min_table_markers_for_table_strategy`:
- Route to `camelot_table`
- Fallback to `docling_layout` if table fidelity checks fail

3. Else if `mime_type == application/pdf` and `prefer_layout_for_pdf` and text length `>= extraction.min_chars_for_layout`:
- Route to `docling_layout` (fallback to `mineru_layout`)

4. Else:
- Route to `extraction.default_strategy` (currently `plain_text`)

5. Global fallback chain (config order):
- `pdfplumber_text -> pymupdf_text -> docling_layout -> mineru_layout -> camelot_table -> tesseract_ocr`

## 3) Pipeline Diagram Requirement

The full pipeline diagram is in [docs/ARCHITECTURE.md](/home/rata/Documents/Ephrata/work/10Acadamy/training/rataz-Wordz/docs/ARCHITECTURE.md) and includes:
- 5 stages
- strategy routing + escalation
- provenance ledger as a cross-cutting layer
- non-linear feedback paths

## 4) Digital vs Scanned Distinction (Observable Criteria)

These criteria are from corpus inspection behavior, not textbook-only rules:

| Signal | Digital Pattern | Scanned Pattern |
|---|---|---|
| Extractable text length per page | stable, high | near-zero or sparse |
| Printable ratio | high (`~0.90+`) | low (`< configured OCR threshold`) |
| Character confidence consistency | uniform | fragmented / noisy |
| Bounding box regularity | coherent block regions | weak/irregular before OCR |
| Searchability in viewer | selectable text | image-only pages |

## Tool Tradeoffs (Open-Source)

| Tool | Strength | Limitation | Best Use |
|---|---|---|---|
| pdfplumber | Reliable text layer parsing | weak on scans/layout semantics | native PDFs baseline |
| PyMuPDF | Fast extraction throughput | structure recovery is manual | high-volume native PDFs |
| Docling | Layout-aware structure recovery | heavier runtime | complex financial/legal layouts |
| MinerU | Reading-order/layout focus | integration maturity varies | fallback layout parser |
| Tesseract | Local OCR, no paid API | quality degrades on noisy scans | scanned legal fallback |
| Camelot | Table extraction fidelity on digital PDFs | image tables remain hard | table-heavy fiscal docs |
