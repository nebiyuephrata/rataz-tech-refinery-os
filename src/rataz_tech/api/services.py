from __future__ import annotations

import io
import os
from collections import deque
from typing import Deque

from fastapi import Header, HTTPException, UploadFile
from pypdf import PdfReader

from rataz_tech.api.models import RequestAuditRecord
from rataz_tech.core.config import ApiConfig


class APIKeyAuthService:
    def __init__(self, config: ApiConfig) -> None:
        self._config = config

    def verify(self, x_api_key: str | None = Header(default=None)) -> None:
        if not self._config.require_api_key:
            return
        expected = os.environ.get(self._config.api_key_env_var)
        if not expected:
            raise HTTPException(status_code=500, detail="API key environment variable is not configured")
        if x_api_key != expected:
            raise HTTPException(status_code=401, detail="Invalid API key")


class RequestAuditService:
    def __init__(self, max_records: int) -> None:
        self._records: Deque[RequestAuditRecord] = deque(maxlen=max_records)

    def add(self, record: RequestAuditRecord) -> None:
        self._records.append(record)

    def list(self) -> list[RequestAuditRecord]:
        return list(self._records)


class FileIngestService:
    def __init__(self, config: ApiConfig) -> None:
        self._config = config

    async def read_upload_as_text(self, upload: UploadFile) -> tuple[str, str]:
        raw = await upload.read()
        if len(raw) > self._config.max_upload_bytes:
            raise HTTPException(status_code=413, detail="Uploaded file exceeds configured size limit")

        mime_type = upload.content_type or self._config.fallback_mime_type
        if mime_type not in self._config.allowed_upload_mime_types:
            raise HTTPException(status_code=415, detail="Unsupported media type")

        if mime_type == "application/pdf":
            reader = PdfReader(io.BytesIO(raw))
            content = "\n".join((page.extract_text() or "") for page in reader.pages).strip()
            if not content:
                raise HTTPException(status_code=422, detail="No extractable text found in PDF")
            return content, mime_type

        content = raw.decode("utf-8", errors="replace").strip()
        if not content:
            raise HTTPException(status_code=422, detail="Uploaded file does not contain text")
        return content, mime_type
