from __future__ import annotations

from abc import ABC, abstractmethod
from collections import deque
from datetime import datetime, timezone
import io
import json
import os
from pathlib import Path
import sqlite3
import threading
from typing import Deque, Optional

from fastapi import Header, HTTPException, UploadFile
from pypdf import PdfReader

from rataz_tech.api.models import RequestAuditRecord, StoredExtractionResponse, StoredPageIndexResponse
from rataz_tech.core.config import ApiConfig, StorageConfig
from rataz_tech.core.models import PageIndexBuildResult, PipelineResult


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


class RequestStore(ABC):
    @abstractmethod
    def add_audit(self, record: RequestAuditRecord) -> None:
        raise NotImplementedError

    @abstractmethod
    def list_audit(self, limit: int = 100, route: str | None = None, document_id: str | None = None) -> list[RequestAuditRecord]:
        raise NotImplementedError

    @abstractmethod
    def save_extraction(self, result: PipelineResult) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_latest_extraction(self, document_id: str) -> Optional[StoredExtractionResponse]:
        raise NotImplementedError

    @abstractmethod
    def save_pageindex(self, pageindex: PageIndexBuildResult) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_pageindex(self, document_id: str) -> Optional[StoredPageIndexResponse]:
        raise NotImplementedError


class InMemoryRequestStore(RequestStore):
    def __init__(self, max_audit_records: int, max_extraction_records: int) -> None:
        self._audit: Deque[RequestAuditRecord] = deque(maxlen=max_audit_records)
        self._latest_by_doc: dict[str, StoredExtractionResponse] = {}
        self._pageindex_by_doc: dict[str, StoredPageIndexResponse] = {}
        self._max_extraction_records = max_extraction_records

    def add_audit(self, record: RequestAuditRecord) -> None:
        self._audit.append(record)

    def list_audit(self, limit: int = 100, route: str | None = None, document_id: str | None = None) -> list[RequestAuditRecord]:
        items = list(self._audit)
        if route:
            items = [r for r in items if r.route == route]
        if document_id:
            items = [r for r in items if r.document_id == document_id]
        return items[-limit:]

    def save_extraction(self, result: PipelineResult) -> None:
        doc_id = result.extraction.document_id
        self._latest_by_doc[doc_id] = StoredExtractionResponse(
            document_id=doc_id,
            trace_id=result.trace_id,
            extracted_at_utc=datetime.now(timezone.utc),
            pipeline_result=result,
        )
        if len(self._latest_by_doc) > self._max_extraction_records:
            # Drop oldest insertion key to cap memory growth.
            oldest_key = next(iter(self._latest_by_doc))
            self._latest_by_doc.pop(oldest_key, None)

    def get_latest_extraction(self, document_id: str) -> Optional[StoredExtractionResponse]:
        return self._latest_by_doc.get(document_id)

    def save_pageindex(self, pageindex: PageIndexBuildResult) -> None:
        self._pageindex_by_doc[pageindex.document_id] = StoredPageIndexResponse(
            document_id=pageindex.document_id,
            trace_id=pageindex.trace_id,
            built_at_utc=pageindex.built_at_utc,
            pageindex=pageindex,
        )

    def get_pageindex(self, document_id: str) -> Optional[StoredPageIndexResponse]:
        return self._pageindex_by_doc.get(document_id)


class SQLiteRequestStore(RequestStore):
    def __init__(self, db_path: str, max_audit_records: int, max_extraction_records: int) -> None:
        self._db_path = db_path
        self._max_audit_records = max_audit_records
        self._max_extraction_records = max_extraction_records
        self._lock = threading.Lock()

        db_file = Path(db_path)
        db_file.parent.mkdir(parents=True, exist_ok=True)

        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS request_audit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    route TEXT NOT NULL,
                    method TEXT NOT NULL,
                    trace_id TEXT NOT NULL,
                    document_id TEXT,
                    timestamp_utc TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS extraction_result (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id TEXT NOT NULL,
                    trace_id TEXT NOT NULL,
                    extracted_at_utc TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS page_index (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id TEXT NOT NULL,
                    trace_id TEXT NOT NULL,
                    built_at_utc TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_request_audit_route ON request_audit(route);
                CREATE INDEX IF NOT EXISTS idx_request_audit_document_id ON request_audit(document_id);
                CREATE INDEX IF NOT EXISTS idx_extraction_result_document_id ON extraction_result(document_id);
                CREATE INDEX IF NOT EXISTS idx_page_index_document_id ON page_index(document_id);
                """
            )

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def add_audit(self, record: RequestAuditRecord) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO request_audit(route, method, trace_id, document_id, timestamp_utc)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    record.route,
                    record.method,
                    record.trace_id,
                    record.document_id,
                    record.timestamp_utc.isoformat(),
                ),
            )
            conn.execute(
                """
                DELETE FROM request_audit
                WHERE id NOT IN (
                    SELECT id FROM request_audit ORDER BY id DESC LIMIT ?
                )
                """,
                (self._max_audit_records,),
            )

    def list_audit(self, limit: int = 100, route: str | None = None, document_id: str | None = None) -> list[RequestAuditRecord]:
        where = []
        params: list[object] = []
        if route:
            where.append("route = ?")
            params.append(route)
        if document_id:
            where.append("document_id = ?")
            params.append(document_id)

        query = "SELECT route, method, trace_id, document_id, timestamp_utc FROM request_audit"
        if where:
            query += " WHERE " + " AND ".join(where)
        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)

        with self._lock, self._connect() as conn:
            rows = conn.execute(query, params).fetchall()

        return [
            RequestAuditRecord(
                route=row["route"],
                method=row["method"],
                trace_id=row["trace_id"],
                document_id=row["document_id"],
                timestamp_utc=datetime.fromisoformat(row["timestamp_utc"]),
            )
            for row in reversed(rows)
        ]

    def save_extraction(self, result: PipelineResult) -> None:
        payload = json.dumps(result.model_dump(mode="json"), ensure_ascii=False)
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO extraction_result(document_id, trace_id, extracted_at_utc, payload_json)
                VALUES (?, ?, ?, ?)
                """,
                (
                    result.extraction.document_id,
                    result.trace_id,
                    datetime.now(timezone.utc).isoformat(),
                    payload,
                ),
            )
            conn.execute(
                """
                DELETE FROM extraction_result
                WHERE id NOT IN (
                    SELECT id FROM extraction_result ORDER BY id DESC LIMIT ?
                )
                """,
                (self._max_extraction_records,),
            )

    def get_latest_extraction(self, document_id: str) -> Optional[StoredExtractionResponse]:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                """
                SELECT document_id, trace_id, extracted_at_utc, payload_json
                FROM extraction_result
                WHERE document_id = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (document_id,),
            ).fetchone()

        if row is None:
            return None

        return StoredExtractionResponse(
            document_id=row["document_id"],
            trace_id=row["trace_id"],
            extracted_at_utc=datetime.fromisoformat(row["extracted_at_utc"]),
            pipeline_result=PipelineResult.model_validate_json(row["payload_json"]),
        )

    def save_pageindex(self, pageindex: PageIndexBuildResult) -> None:
        payload = json.dumps(pageindex.model_dump(mode="json"), ensure_ascii=False)
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO page_index(document_id, trace_id, built_at_utc, payload_json)
                VALUES (?, ?, ?, ?)
                """,
                (
                    pageindex.document_id,
                    pageindex.trace_id,
                    pageindex.built_at_utc.isoformat(),
                    payload,
                ),
            )

    def get_pageindex(self, document_id: str) -> Optional[StoredPageIndexResponse]:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                """
                SELECT document_id, trace_id, built_at_utc, payload_json
                FROM page_index
                WHERE document_id = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (document_id,),
            ).fetchone()
        if row is None:
            return None
        pageindex = PageIndexBuildResult.model_validate_json(row["payload_json"])
        return StoredPageIndexResponse(
            document_id=row["document_id"],
            trace_id=row["trace_id"],
            built_at_utc=datetime.fromisoformat(row["built_at_utc"]),
            pageindex=pageindex,
        )


def build_request_store(storage_cfg: StorageConfig, api_cfg: ApiConfig) -> RequestStore:
    if storage_cfg.backend == "sqlite":
        return SQLiteRequestStore(
            db_path=storage_cfg.sqlite_path,
            max_audit_records=api_cfg.max_audit_records,
            max_extraction_records=storage_cfg.max_extraction_records,
        )
    return InMemoryRequestStore(
        max_audit_records=api_cfg.max_audit_records,
        max_extraction_records=storage_cfg.max_extraction_records,
    )


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
