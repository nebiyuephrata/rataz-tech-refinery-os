from __future__ import annotations

from rataz_tech.benchmark.runner import run_benchmark


def test_benchmark_runner_generates_metrics_table(tmp_path) -> None:
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "NF_01.txt").write_text("Revenue,Cost\n100,50\n", encoding="utf-8")
    (corpus / "SL_01.txt").write_text("whereas plaintiff affidavit", encoding="utf-8")
    (corpus / "MA_01.txt").write_text("score rubric evaluation", encoding="utf-8")
    (corpus / "TF_01.txt").write_text("budget,tax\n10,2\n", encoding="utf-8")

    out = tmp_path / "benchmark.md"
    summary = run_benchmark(config_path="configs/settings.yaml", corpus_dir=corpus, output_path=out)

    assert out.exists()
    text = out.read_text(encoding="utf-8")
    assert "reading_order_accuracy" in text
    assert "table_fidelity" in text
    assert "bbox_completeness" in text
    assert summary["documents"] == 4
