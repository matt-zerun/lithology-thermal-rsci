from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from lithology_thermal_rsci.pareto import mark_pareto_front


def main() -> None:
    parser = argparse.ArgumentParser(description="Merge predictive metrics with RSCI and mark Pareto-optimal candidates.")
    parser.add_argument("--accuracy", default="workflow_outputs/grouped_cv_summary.csv")
    parser.add_argument("--rsci", default="workflow_outputs/rsci_scores.csv")
    parser.add_argument("--output", default="workflow_outputs/model_review_summary.csv")
    arguments = parser.parse_args()
    accuracy = pd.read_csv(arguments.accuracy)
    rsci = pd.read_csv(arguments.rsci)
    merged = rsci.merge(accuracy, on=["lithology", "model", "variant"], validate="one_to_one")
    reviewed = mark_pareto_front(merged, accuracy_column="R2_OOF")
    target = Path(arguments.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    reviewed.to_csv(target, index=False)
    print(target)


if __name__ == "__main__":
    main()
