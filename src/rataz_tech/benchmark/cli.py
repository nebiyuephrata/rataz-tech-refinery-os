from __future__ import annotations

import argparse

from rataz_tech.benchmark.runner import run_benchmark


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Refinery-OS benchmark.")
    parser.add_argument("--config", default="configs/settings.yaml")
    parser.add_argument("--corpus", required=True)
    parser.add_argument("--output", default="docs/TEST_RESULTS.generated.md")
    args = parser.parse_args()

    summary = run_benchmark(config_path=args.config, corpus_dir=args.corpus, output_path=args.output)
    print(summary)


if __name__ == "__main__":
    main()
