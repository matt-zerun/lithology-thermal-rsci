from __future__ import annotations

import argparse
from pathlib import Path

import joblib

from lithology_thermal_rsci.constants import FEATURES, LITHOLOGIES, MODEL_FAMILIES
from lithology_thermal_rsci.data_validation import read_table, validate_and_prepare
from lithology_thermal_rsci.response_profiles import extract_profiles
from lithology_thermal_rsci.state_aggregation import aggregate_material_states


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract one-dimensional response profiles inside the observed predictor-domain convex hull.")
    parser.add_argument("input")
    parser.add_argument("--models-dir", default="workflow_outputs/models")
    parser.add_argument("--output", default="workflow_outputs/response_profiles")
    parser.add_argument("--models", nargs="+", default=list(MODEL_FAMILIES))
    parser.add_argument("--variant", default="SMOOTH")
    arguments = parser.parse_args()
    observations, _ = validate_and_prepare(read_table(arguments.input))
    data, _ = aggregate_material_states(observations)
    output = Path(arguments.output)
    output.mkdir(parents=True, exist_ok=True)
    for lithology in LITHOLOGIES:
        observed = data.loc[data["lithology"] == lithology, FEATURES]
        densities = observed["bulk_density_mg_m3"].quantile([0.25, 0.50, 0.75]).tolist()
        waters = observed["water_content_pct"].quantile([0.25, 0.50, 0.75]).tolist()
        for family in [name.upper() for name in arguments.models]:
            source = Path(arguments.models_dir) / f"{lithology}_{family}_{arguments.variant.upper()}.joblib"
            if not source.exists():
                raise FileNotFoundError(source)
            water_profiles, density_profiles = extract_profiles(joblib.load(source), observed, densities, waters)
            water_target = output / f"{lithology}_{family}_{arguments.variant.upper()}_lambda_by_water.csv"
            density_target = output / f"{lithology}_{family}_{arguments.variant.upper()}_lambda_by_density.csv"
            water_profiles.to_csv(water_target, index=False)
            density_profiles.to_csv(density_target, index=False)
            print(water_target)
            print(density_target)


if __name__ == "__main__":
    main()
