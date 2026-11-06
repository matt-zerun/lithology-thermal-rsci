from __future__ import annotations

import argparse
from pathlib import Path

from lithology_thermal_rsci.constants import MODEL_FAMILIES, MODEL_VARIANTS
from lithology_thermal_rsci.pipeline import run_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Run the complete lithology-specific analysis on a screened, "
            "schema-compliant CSV or XLSX observation table."
        )
    )
    parser.add_argument("input", help="Screened source-observation CSV or XLSX")
    parser.add_argument("output", help="Directory for the complete workflow output")
    parser.add_argument(
        "--models",
        nargs="+",
        choices=MODEL_FAMILIES,
        default=MODEL_FAMILIES,
        help="Model families to evaluate (default: SVR GAM RF XGB)",
    )
    parser.add_argument(
        "--variants",
        nargs="+",
        choices=MODEL_VARIANTS,
        default=("BASE", "SMOOTH", "INTERMEDIATE"),
        help=(
            "Candidate variants to evaluate. TUNED may be listed here or "
            "added with --include-tuned."
        ),
    )
    parser.add_argument(
        "--include-tuned",
        action="store_true",
        help=(
            "Add nested-CV TUNED candidates. Required for the complete "
            "16-candidate-per-lithology diagnostic review."
        ),
    )
    parser.add_argument(
        "--grid-size",
        type=int,
        help="Override the configured response-grid size (default: config value)",
    )
    parser.add_argument(
        "--existing-tuning-only",
        action="store_true",
        help="Do not calculate a missing tuning result; fail if its cache is absent",
    )
    arguments = parser.parse_args()
    if arguments.grid_size is not None and arguments.grid_size < 10:
        parser.error("--grid-size must be at least 10")

    outputs = run_pipeline(
        arguments.input,
        arguments.output,
        families=arguments.models,
        variants=arguments.variants,
        include_tuned=arguments.include_tuned,
        tune_missing=not arguments.existing_tuning_only,
        grid_size=arguments.grid_size,
    )
    for name, path in outputs.items():
        print(f"{name}: {Path(path).resolve()}")


if __name__ == "__main__":
    main()
