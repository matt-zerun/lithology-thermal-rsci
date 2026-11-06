from __future__ import annotations

import argparse
from pathlib import Path

from lithology_thermal_rsci.data_validation import read_table, validate_and_prepare
from lithology_thermal_rsci.predictor_correlation import predictor_correlation_table
from lithology_thermal_rsci.state_aggregation import aggregate_material_states


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Calculate Pearson and Spearman correlations between water content "
            "and wet bulk density at material-state and observation levels."
        )
    )
    parser.add_argument("input")
    parser.add_argument(
        "--output",
        default="workflow_outputs/predictor_correlations.csv",
    )
    arguments = parser.parse_args()

    observations, _ = validate_and_prepare(read_table(arguments.input))
    states, _ = aggregate_material_states(observations)
    table = predictor_correlation_table(observations, states)
    output = Path(arguments.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(output, index=False)
    print(table.to_string(index=False))
    print(output)


if __name__ == "__main__":
    main()
