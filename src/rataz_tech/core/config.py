from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Literal

import yaml
from pydantic import BaseModel, Field


class AppConfig(BaseModel):
    name: str
    default_language: str
    supported_languages: List[str]


class PipelineConfig(BaseModel):
    max_chunk_chars: int = Field(gt=0)
    chunk_overlap_chars: int = Field(ge=0)
    max_query_results: int = Field(gt=0)
    confidence_threshold: float = Field(ge=0.0, le=1.0)
    enable_semantic_navigation: bool
    enable_llm_escalation: bool
    chunking_constitution: List[str] = Field(default_factory=list)
    semantic_query: "SemanticQuerySettings" = Field(default_factory=lambda: SemanticQuerySettings())


class SemanticQuerySettings(BaseModel):
    enabled: bool = True
    top_k: int = Field(default=5, gt=0)
    lexical_weight: float = Field(default=0.6, ge=0.0)
    semantic_weight: float = Field(default=0.4, ge=0.0)
    embedder_provider: Literal["hashing", "bge-small"] = "hashing"
    vector_store_provider: Literal["inmemory", "faiss"] = "inmemory"
    bge_model_name: str = "BAAI/bge-small-en-v1.5"
    hashing_dim: int = Field(default=128, gt=0)


class ComponentConfig(BaseModel):
    extractor: str
    normalizer: str
    chunker: str
    indexer: str
    query_engine: str


class VisionBudgetConfig(BaseModel):
    max_tokens_per_document: int = Field(gt=0)
    max_cost_usd_per_document: float = Field(gt=0)
    estimated_cost_per_1k_tokens_usd: float = Field(gt=0)


class EscalationConfig(BaseModel):
    strategy_order: List[str] = Field(min_length=3)
    review_on_final_low_confidence: bool = True


class ExtractionConfig(BaseModel):
    default_strategy: str
    fallback_chain: List[str]

    min_chars_for_layout: int = Field(gt=0)
    min_table_markers_for_table_strategy: int = Field(ge=0)
    low_printable_ratio_for_ocr: float = Field(ge=0.0, le=1.0)
    native_char_density_min: float = Field(ge=0.0)
    mixed_image_ratio_min: float = Field(ge=0.0, le=1.0)
    scanned_image_ratio_min: float = Field(ge=0.0, le=1.0)
    mixed_layout_short_line_ratio_min: float = Field(ge=0.0, le=1.0)
    multi_column_short_line_ratio_min: float = Field(ge=0.0, le=1.0)
    prefer_layout_for_pdf: bool

    strategy_by_cost: Dict[str, str]
    strategy_confidence_thresholds: Dict[str, float]
    domain_keywords: Dict[str, List[str]]

    escalation: EscalationConfig
    vision_budget: VisionBudgetConfig


class ApiConfig(BaseModel):
    require_api_key: bool
    api_key_env_var: str
    max_audit_records: int = Field(gt=0)
    max_upload_bytes: int = Field(gt=0)
    fallback_mime_type: str
    allowed_upload_mime_types: List[str]


class StorageConfig(BaseModel):
    backend: Literal["memory", "sqlite"] = "memory"
    sqlite_path: str = "./data/refinery_os.db"
    max_extraction_records: int = Field(gt=0, default=1000)


class Settings(BaseModel):
    app: AppConfig
    pipeline: PipelineConfig
    components: ComponentConfig
    extraction: ExtractionConfig
    api: ApiConfig
    storage: StorageConfig = Field(default_factory=StorageConfig)


def load_settings(path: str | Path) -> Settings:
    with Path(path).open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    return Settings.model_validate(raw)
