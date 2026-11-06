from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from lithology_thermal_rsci.data_validation import read_table, validate_and_prepare
from lithology_thermal_rsci.state_aggregation import aggregate_material_states


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate and normalise the required input schema.")
    parser.add_argument("input")
    parser.add_argument("--output")
    parser.add_argument("--states-output")
    parser.add_argument("--report")
    arguments = parser.parse_args()
    prepared, validation_report = validate_and_prepare(read_table(arguments.input))
    states, state_report = aggregate_material_states(prepared)
    payload = {
        "observation_validation": asdict(validation_report),
        "material_state_aggregation": asdict(state_report),
    }
    rendered = json.dumps(payload, indent=2)
    print(rendered)
    if arguments.output:
        prepared.to_csv(arguments.output, index=False)
    if arguments.states_output:
        states.to_csv(arguments.states_output, index=False)
    if arguments.report:
        Path(arguments.report).write_text(rendered, encoding="utf-8")


if __name__ == "__main__":
    main()
