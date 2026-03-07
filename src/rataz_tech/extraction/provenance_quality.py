from __future__ import annotations

import hashlib

from pydantic import BaseModel, Field

from rataz_tech.core.config import ProvenanceQualityConfig
from rataz_tech.core.models import ExtractionResult


class ProvenanceQualityResult(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    unit_spatial_ratio: float = Field(ge=0.0, le=1.0)
    chain_bbox_ratio: float = Field(ge=0.0, le=1.0)
    content_hash_match_ratio: float = Field(ge=0.0, le=1.0)
    review_required: bool


def evaluate_provenance_quality(result: ExtractionResult, config: ProvenanceQualityConfig) -> ProvenanceQualityResult:
    units = result.units
    extracted_document = result.extracted_document

    spatial_present = sum(1 for unit in units if unit.provenance.spatial is not None)
    unit_spatial_ratio = spatial_present / max(1, len(units))

    chains = extracted_document.provenance_chains if extracted_document else []
    chain_bbox_ratio = sum(1 for chain in chains if chain.bbox is not None) / max(1, len(chains))

    text_hashes = set()
    if extracted_document:
        text_hashes = {hashlib.sha256(block.content.encode("utf-8", errors="ignore")).hexdigest() for block in extracted_document.text_blocks}
    if not chains:
        content_hash_match_ratio = 0.0
    else:
        matches = sum(1 for chain in chains if chain.content_hash in text_hashes)
        content_hash_match_ratio = matches / len(chains)

    score = (unit_spatial_ratio + chain_bbox_ratio + content_hash_match_ratio) / 3.0

    hash_gate_failed = config.require_content_hash_match and content_hash_match_ratio < 1.0
    score_gate_failed = score < config.min_overall_score
    ratio_gate_failed = unit_spatial_ratio < config.min_unit_spatial_ratio or chain_bbox_ratio < config.min_chain_bbox_ratio

    review_required = bool(hash_gate_failed or score_gate_failed or ratio_gate_failed)
    return ProvenanceQualityResult(
        score=round(score, 4),
        unit_spatial_ratio=round(unit_spatial_ratio, 4),
        chain_bbox_ratio=round(chain_bbox_ratio, 4),
        content_hash_match_ratio=round(content_hash_match_ratio, 4),
        review_required=review_required,
    )
