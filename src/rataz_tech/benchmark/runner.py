from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from rataz_tech.core.models import DocumentInput
from rataz_tech.main import build_pipeline


def _class_from_name(name: str) -> str:
    prefix = name.split("_", 1)[0].upper()
    mapping = {
        "NF": "native_financial",
        "SL": "scanned_legal",
        "MA": "mixed_assessment",
        "TF": "table_heavy_fiscal",
    }
    return mapping.get(prefix, "unknown")


def _safe_mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def run_benchmark(config_path: str, corpus_dir: str | Path, output_path: str | Path) -> dict[str, float | int]:
    pipeline = build_pipeline(config_path)
    corpus = Path(corpus_dir)
    out = Path(output_path)

    by_class: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    total_docs = 0

    for fp in sorted(corpus.glob("*.txt")):
        total_docs += 1
        content = fp.read_text(encoding="utf-8")
        doc_class = _class_from_name(fp.stem)

        result = pipeline.ingest(
            DocumentInput(
                document_id=fp.stem,
                source_uri=f"file://{fp}",
                content=content,
                mime_type="text/plain",
            )
        )

        extracted = result.extraction.extracted_document
        if extracted is None:
            reading_order_accuracy = 0.0
            table_fidelity = 0.0
            bbox_completeness = 0.0
        else:
            text_blocks = extracted.text_blocks
            reading_order_accuracy = 1.0 if text_blocks else 0.0
            has_table = 1.0 if extracted.tables else 0.0
            table_marker_present = 1.0 if any(tok in content for tok in [",", "|", "\t"]) else 0.0
            table_fidelity = has_table if table_marker_present else 1.0
            with_bbox = sum(1 for b in text_blocks if b.bounding_box is not None)
            bbox_completeness = (with_bbox / len(text_blocks)) if text_blocks else 0.0

        by_class[doc_class]["reading_order_accuracy"].append(reading_order_accuracy)
        by_class[doc_class]["table_fidelity"].append(table_fidelity)
        by_class[doc_class]["bbox_completeness"].append(bbox_completeness)

    lines = [
        "# Benchmark Results",
        "",
        "| document_class | reading_order_accuracy | table_fidelity | bbox_completeness |",
        "|---|---:|---:|---:|",
    ]
    for cls in sorted(by_class):
        roa = _safe_mean(by_class[cls]["reading_order_accuracy"])
        tf = _safe_mean(by_class[cls]["table_fidelity"])
        bc = _safe_mean(by_class[cls]["bbox_completeness"])
        lines.append(f"| {cls} | {roa:.3f} | {tf:.3f} | {bc:.3f} |")

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")

    overall = {
        "documents": total_docs,
        "reading_order_accuracy": _safe_mean([v for c in by_class.values() for v in c["reading_order_accuracy"]]),
        "table_fidelity": _safe_mean([v for c in by_class.values() for v in c["table_fidelity"]]),
        "bbox_completeness": _safe_mean([v for c in by_class.values() for v in c["bbox_completeness"]]),
    }
    return overall
