from __future__ import annotations

import argparse
from pathlib import Path

import joblib

from lithology_thermal_rsci.config import load_json
from lithology_thermal_rsci.constants import FEATURES, LITHOLOGIES, MODEL_FAMILIES, MODEL_VARIANTS
from lithology_thermal_rsci.data_validation import read_table, validate_and_prepare
from lithology_thermal_rsci.response_surfaces import generate_response_surface
from lithology_thermal_rsci.state_aggregation import aggregate_material_states


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate convex-hull-restricted response-surface grids.")
    parser.add_argument("input")
    parser.add_argument("--models-dir", default="workflow_outputs/models")
    parser.add_argument("--output", default="workflow_outputs/response_surfaces")
    parser.add_argument("--models", nargs="+", default=list(MODEL_FAMILIES))
    parser.add_argument("--variants", nargs="+", default=list(MODEL_VARIANTS))
    arguments = parser.parse_args()

    observations, _ = validate_and_prepare(read_table(arguments.input))
    data, _ = aggregate_material_states(observations)
    config = load_json("config/model_variants.json")
    models_dir = Path(arguments.models_dir)
    output = Path(arguments.output)
    output.mkdir(parents=True, exist_ok=True)

    for lithology in LITHOLOGIES:
        observed = data.loc[data["lithology"] == lithology, FEATURES]
        for family in [name.upper() for name in arguments.models]:
            for variant in [name.upper() for name in arguments.variants]:
                model_path = models_dir / f"{lithology}_{family}_{variant}.joblib"
                if not model_path.exists():
                    raise FileNotFoundError(model_path)
                surface = generate_response_surface(joblib.load(model_path), observed, int(config["grid_size"]))
                target = output / f"{lithology}_{family}_{variant}.csv"
                surface.table.to_csv(target, index=False)
                print(target)


if __name__ == "__main__":
    main()
