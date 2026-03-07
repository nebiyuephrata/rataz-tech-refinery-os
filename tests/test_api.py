from __future__ import annotations

from fastapi.testclient import TestClient
import yaml

from rataz_tech.api.server import create_app


def test_health_endpoint() -> None:
    client = TestClient(create_app("configs/settings.yaml"))
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "app" in body
    assert "storage_backend" in body


def test_ingest_query_and_request_audit() -> None:
    client = TestClient(create_app("configs/settings.yaml"))

    ingest_resp = client.post(
        "/ingest",
        json={
            "document_id": "api-doc-1",
            "source_uri": "local://api-doc-1.txt",
            "content": "Rataz Tech keeps traceable provenance in document pipelines.",
            "mime_type": "text/plain",
        },
    )
    assert ingest_resp.status_code == 200
    ingest_body = ingest_resp.json()
    assert ingest_body["trace_id"].startswith("ingest-")
    doc_id = ingest_body["extraction"]["document_id"]

    query_resp = client.post(
        "/query",
        json={"query": "traceable provenance", "language": "en", "max_results": 3},
    )
    assert query_resp.status_code == 200
    query_body = query_resp.json()
    assert query_body["trace_id"].startswith("query-")

    audit_resp = client.get("/audit/requests")
    assert audit_resp.status_code == 200
    records = audit_resp.json()["records"]
    assert len(records) >= 2
    assert {records[-2]["route"], records[-1]["route"]} == {"/ingest", "/query"}

    extraction_resp = client.get(f"/extractions/{doc_id}")
    assert extraction_resp.status_code == 200
    extraction_body = extraction_resp.json()
    assert extraction_body["document_id"] == doc_id
    assert extraction_body["pipeline_result"]["trace_id"].startswith("ingest-")

    pageindex_resp = client.get(f"/pageindex/{doc_id}")
    assert pageindex_resp.status_code == 200
    assert pageindex_resp.json()["document_id"] == doc_id

    pageindex_query = client.post(
        "/pageindex/query",
        json={"document_id": doc_id, "query": "traceable provenance", "top_k": 3},
    )
    assert pageindex_query.status_code == 200
    assert pageindex_query.json()["document_id"] == doc_id


def test_file_ingest_text() -> None:
    client = TestClient(create_app("configs/settings.yaml"))

    response = client.post(
        "/ingest/file",
        files={"file": ("sample.txt", b"MVP upload flow from file endpoint", "text/plain")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["trace_id"].startswith("ingest-")
    assert body["extraction"]["units"][0]["provenance"]["source_uri"].startswith("upload://")


def test_api_key_auth_when_enabled(tmp_path, monkeypatch) -> None:
    with open("configs/settings.yaml", "r", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)

    cfg["api"]["require_api_key"] = True
    cfg["api"]["api_key_env_var"] = "TEST_RATAZ_API_KEY"
    cfg_path = tmp_path / "settings-auth.yaml"
    cfg_path.write_text(yaml.safe_dump(cfg), encoding="utf-8")

    monkeypatch.setenv("TEST_RATAZ_API_KEY", "secret")
    client = TestClient(create_app(str(cfg_path)))

    unauthorized = client.post(
        "/query",
        json={"query": "x", "language": "en", "max_results": 1},
    )
    assert unauthorized.status_code == 401

    authorized = client.post(
        "/query",
        json={"query": "x", "language": "en", "max_results": 1},
        headers={"x-api-key": "secret"},
    )
    assert authorized.status_code == 200


def test_audit_filtering_by_route() -> None:
    client = TestClient(create_app("configs/settings.yaml"))
    client.post(
        "/ingest",
        json={
            "document_id": "api-doc-filter",
            "source_uri": "local://api-doc-filter.txt",
            "content": "route filtering test",
            "mime_type": "text/plain",
        },
    )
    client.post("/query", json={"query": "test", "language": "en", "max_results": 1})

    response = client.get("/audit/requests", params={"route": "/query", "limit": 5})
    assert response.status_code == 200
    records = response.json()["records"]
    assert records
    assert all(r["route"] == "/query" for r in records)


def test_sqlite_store_persists_extraction_lookup(tmp_path) -> None:
    with open("configs/settings.yaml", "r", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)

    cfg["storage"]["backend"] = "sqlite"
    cfg["storage"]["sqlite_path"] = str(tmp_path / "refinery.db")
    cfg_path = tmp_path / "settings-sqlite.yaml"
    cfg_path.write_text(yaml.safe_dump(cfg), encoding="utf-8")

    client = TestClient(create_app(str(cfg_path)))
    ingest_resp = client.post(
        "/ingest",
        json={
            "document_id": "sql-doc-1",
            "source_uri": "local://sql-doc-1.txt",
            "content": "sqlite persistence check",
            "mime_type": "text/plain",
        },
    )
    assert ingest_resp.status_code == 200

    lookup = client.get("/extractions/sql-doc-1")
    assert lookup.status_code == 200
    assert lookup.json()["document_id"] == "sql-doc-1"
