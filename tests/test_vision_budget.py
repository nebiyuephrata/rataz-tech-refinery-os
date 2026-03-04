from __future__ import annotations

import yaml

from rataz_tech.core.models import DocumentInput
from rataz_tech.main import build_pipeline


def test_vision_budget_cap_enforced(tmp_path) -> None:
    with open("configs/settings.yaml", "r", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)

    cfg["extraction"]["strategy_confidence_thresholds"]["A_fast_text"] = 0.99
    cfg["extraction"]["strategy_confidence_thresholds"]["B_layout_aware"] = 0.99
    cfg["extraction"]["vision_budget"]["max_tokens_per_document"] = 50
    cfg_path = tmp_path / "settings-budget.yaml"
    cfg_path.write_text(yaml.safe_dump(cfg), encoding="utf-8")

    pipeline = build_pipeline(str(cfg_path))
    large_text = "budget " * 1000
    result = pipeline.ingest(
        DocumentInput(
            document_id="budget-1",
            source_uri="local://budget-1.txt",
            content=large_text,
            mime_type="text/plain",
        )
    )

    assert result.extraction.review_required is True
    assert any("budget cap exceeded" in a.message.lower() for a in result.extraction.audit)
