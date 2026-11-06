from __future__ import annotations

import argparse
from pathlib import Path

from lithology_thermal_rsci.pipeline import run_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the complete demonstration workflow.")
    parser.add_argument("--input", default="data/synthetic_example.csv")
    parser.add_argument("--output", default="demo_outputs")
    parser.add_argument("--models", nargs="+", default=["SVR", "GAM", "RF", "XGB"])
    parser.add_argument(
        "--include-tuned",
        action="store_true",
        help="Also tune and evaluate TUNED variants. This is substantially slower.",
    )
    arguments = parser.parse_args()
    outputs = run_pipeline(
        arguments.input,
        arguments.output,
        families=arguments.models,
        include_tuned=arguments.include_tuned,
    )
    for name, path in outputs.items():
        print(f"{name}: {Path(path).resolve()}")


if __name__ == "__main__":
    main()
