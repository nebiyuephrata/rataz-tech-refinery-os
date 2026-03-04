# Cost Analysis -- Per-Document Estimates by Strategy Tier

## Assumptions and Derivation

Base infra profile for estimates:
- Single node: 8 vCPU / 16 GB RAM
- Effective runtime cost: **$0.42/hour**
- Storage + IO overhead per document: **$0.00005**

Cost formula:
- `compute_cost_per_doc = (processing_seconds / 3600) * 0.42`
- `total_cost_per_doc = compute_cost_per_doc + 0.00005`

All tiers are open-source only (no paid API fees in baseline).

## Strategy Tiers

- **Tier A (Fast Text):** pdfplumber/PyMuPDF + deterministic parsing
- **Tier B (Layout-Aware):** Docling/MinerU for reading-order and structure recovery
- **Tier C (Vision-Augmented):** OCR/table heavy path (Tesseract + Camelot + layout fallback)

## Per-Document Estimates by Class

### Native Financial (NF)

| Tier | Avg Time / Doc | Monetary Cost / Doc | Quality Gain |
|---|---:|---:|---|
| A | 2.8 s | $0.00038 | baseline text extraction |
| B | 7.4 s | $0.00091 | better reading-order + section boundaries |
| C | 14.2 s | $0.00171 | strongest robustness on embedded visuals |

### Scanned Legal (SL)

| Tier | Avg Time / Doc | Monetary Cost / Doc | Quality Gain |
|---|---:|---:|---|
| A | 3.1 s | $0.00041 | low utility (missing text layer) |
| B | 8.8 s | $0.00108 | moderate structure recovery |
| C | 21.6 s | $0.00257 | major gain from OCR for clause recovery |

### Mixed Assessment (MA)

| Tier | Avg Time / Doc | Monetary Cost / Doc | Quality Gain |
|---|---:|---:|---|
| A | 4.0 s | $0.00052 | inconsistent across pages |
| B | 10.6 s | $0.00129 | better handling of heterogeneous layouts |
| C | 18.9 s | $0.00226 | highest resilience with fallback routing |

### Table-Heavy Fiscal (TF)

| Tier | Avg Time / Doc | Monetary Cost / Doc | Quality Gain |
|---|---:|---:|---|
| A | 3.5 s | $0.00046 | table flattening risk |
| B | 9.7 s | $0.00118 | improved table structure capture |
| C | 16.8 s | $0.00201 | best table fidelity via Camelot + fallback |

## Multi-Dimensional Cost Summary

| Tier | Mean Time / Doc | Mean $ / Doc | Best For |
|---|---:|---:|---|
| A | 3.35 s | $0.00044 | high-throughput, simple native docs |
| B | 9.13 s | $0.00112 | balanced quality/cost for enterprise PDFs |
| C | 17.88 s | $0.00214 | difficult scans, complex tables, mixed packets |

## Cost-Quality Connection (Why pay more?)

- Tier B over Tier A: pays for layout/reading-order recovery; strongest improvement in `NF` and `MA`.
- Tier C over Tier B: pays for OCR and table-specialized recovery; strongest improvement in `SL` and `TF`.
- Recommended default: start Tier A/B by Triage, escalate to Tier C only when quality gates fail.
