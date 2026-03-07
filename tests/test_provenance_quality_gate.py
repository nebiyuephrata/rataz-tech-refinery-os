from __future__ import annotations

import hashlib

from rataz_tech.core.config import load_settings
from rataz_tech.core.models import (
    AuditEvent,
    BBox,
    ChunkType,
    DocumentInput,
    DocumentProfile,
    DomainHint,
    ExtractedDocument,
    ExtractionCostTier,
    ExtractionResult,
    ExtractedUnit,
    LayoutComplexity,
    LogicalDocumentUnit,
    OriginType,
    PageIndexNode,
    PageRef,
    ProvenanceChain,
    ProvenanceRecord,
    SpatialProvenance,
    StageName,
)
from rataz_tech.extraction.provenance_quality import evaluate_provenance_quality
from rataz_tech.main import build_pipeline


def _profile() -> DocumentProfile:
    return DocumentProfile(
        origin_type=OriginType.NATIVE_DIGITAL,
        layout_complexity=LayoutComplexity.SINGLE_COLUMN,
        language="en",
        domain_hint=DomainHint.GENERAL,
        extraction_cost=ExtractionCostTier.A_FAST_TEXT,
        confidence=0.9,
        char_count=100,
        char_density=100.0,
        image_ratio=0.0,
        font_metadata_present=True,
        table_marker_count=0,
    )


def _result(valid: bool) -> ExtractionResult:
    content = "alpha beta"
    h = hashlib.sha256(content.encode("utf-8")).hexdigest()
    chain_hash = h if valid else "deadbeef0"
    chain_bbox = BBox(x0=0.0, y0=0.0, x1=1.0, y1=1.0) if valid else None

    ldu = LogicalDocumentUnit(
        ldu_id="ldu-1",
        content=content,
        chunk_type=ChunkType.TEXT,
        token_count=2,
        page_refs=[PageRef(page_start=1, page_end=1)],
        bounding_box=BBox(x0=0.0, y0=0.0, x1=1.0, y1=1.0),
        content_hash=h,
        parent_section="root",
        chunk_relationships=[],
    )
    extracted_document = ExtractedDocument(
        document_id="d1",
        profile=_profile(),
        text_blocks=[ldu],
        tables=[],
        figures=[],
        page_index=PageIndexNode(node_id="root", title="Doc", page_start=1, page_end=1, children=[]),
        provenance_chains=[
            ProvenanceChain(document_name="local://d1", page_number=1, bbox=chain_bbox, content_hash=chain_hash)
        ],
    )

    unit_spatial = SpatialProvenance(page=1, x0=0.0, y0=0.0, x1=1.0, y1=1.0) if valid else None
    units = [
        ExtractedUnit(
            unit_id="u1",
            text=content,
            provenance=ProvenanceRecord(
                source_uri="local://d1",
                extractor="t",
                record_id="r1",
                confidence=0.8,
                spatial=unit_spatial,
            ),
        )
    ]

    return ExtractionResult(
        document_id="d1",
        profile=_profile(),
        extracted_document=extracted_document,
        strategy_used="plain_text",
        strategy_confidence=0.8,
        units=units,
        audit=[AuditEvent(stage=StageName.EXTRACTION, message="seed")],
    )


def test_provenance_quality_passes_on_complete_chains() -> None:
    settings = load_settings("configs/settings.yaml")
    quality = evaluate_provenance_quality(_result(valid=True), settings.extraction.provenance_quality)
    assert quality.review_required is False
    assert quality.score >= settings.extraction.provenance_quality.min_overall_score


def test_provenance_quality_flags_missing_spatial_or_hash_chain() -> None:
    settings = load_settings("configs/settings.yaml")
    quality = evaluate_provenance_quality(_result(valid=False), settings.extraction.provenance_quality)
    assert quality.review_required is True
    assert quality.score < settings.extraction.provenance_quality.min_overall_score


def test_pipeline_emits_provenance_quality_audit_event() -> None:
    pipeline = build_pipeline("configs/settings.yaml")
    result = pipeline.ingest(
        DocumentInput(
            document_id="prov-gate-1",
            source_uri="local://prov-gate-1.txt",
            content="Revenue and expense schedule with clear provenance.",
            mime_type="text/plain",
        )
    )

    events = [a for a in result.extraction.audit if a.message == "Provenance quality gate evaluated"]
    assert events
    assert "quality_score" in events[0].metadata
