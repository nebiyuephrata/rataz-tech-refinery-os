from __future__ import annotations

from pathlib import Path
from typing import List

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


class ComponentConfig(BaseModel):
    extractor: str
    normalizer: str
    chunker: str
    indexer: str
    query_engine: str


class ApiConfig(BaseModel):
    require_api_key: bool
    api_key_env_var: str
    max_audit_records: int = Field(gt=0)
    max_upload_bytes: int = Field(gt=0)
    fallback_mime_type: str
    allowed_upload_mime_types: List[str]


class Settings(BaseModel):
    app: AppConfig
    pipeline: PipelineConfig
    components: ComponentConfig
    api: ApiConfig


def load_settings(path: str | Path) -> Settings:
    with Path(path).open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    return Settings.model_validate(raw)
