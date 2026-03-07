from __future__ import annotations

from fastapi.testclient import TestClient
import yaml

from rataz_tech.api.server import create_app


def test_sqlite_facttable_structured_query_returns_numeric_fact(tmp_path) -> None:
    with open("configs/settings.yaml", "r", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)

    cfg["storage"]["backend"] = "sqlite"
    cfg["storage"]["sqlite_path"] = str(tmp_path / "refinery.db")
    cfg_path = tmp_path / "settings-sqlite-fact.yaml"
    cfg_path.write_text(yaml.safe_dump(cfg), encoding="utf-8")

    client = TestClient(create_app(str(cfg_path)))

    ingest = client.post(
        "/ingest",
        json={
            "document_id": "fact-sql-1",
            "source_uri": "local://fact-sql-1.txt",
            "content": "Revenue was $4200 in Q3. EBITDA was 900.",
            "mime_type": "text/plain",
        },
    )
    assert ingest.status_code == 200

    response = client.post(
        "/query/structured",
        json={"document_id": "fact-sql-1", "query": "revenue", "limit": 5},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["rows"]
    assert any(float(row["value"]) == 4200.0 for row in body["rows"])
