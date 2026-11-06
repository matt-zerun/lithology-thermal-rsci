#!/usr/bin/env python3
"""Generate the deterministic public demonstration dataset.

The generated values are synthetic and do not reproduce, resample, or
approximate any restricted reference observation.  The hierarchy deliberately
contains multiple measurements per material state, multiple states per sample,
and multiple samples per parent-material group so that aggregation and grouped
validation are both exercised by the public example.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


SEED = 1103
LITHOLOGY_PARAMETERS = {
    "sand": {
        "water": (2.0, 28.0),
        "density": (1.10, 2.25),
        "base": 0.38,
        "water_slope": 0.045,
        "density_slope": 0.78,
        "curvature": 0.00035,
    },
    "silt": {
        "water": (1.0, 30.0),
        "density": (1.18, 2.28),
        "base": 0.30,
        "water_slope": 0.030,
        "density_slope": 1.00,
        "curvature": -0.00045,
    },
    "clayey_soil": {
        "water": (3.0, 35.0),
        "density": (1.18, 2.38),
        "base": 0.55,
        "water_slope": -0.006,
        "density_slope": 1.25,
        "curvature": 0.00010,
    },
    "clay": {
        "water": (5.0, 48.0),
        "density": (1.58, 2.22),
        "base": 0.42,
        "water_slope": 0.008,
        "density_slope": 1.45,
        "curvature": -0.00008,
    },
}


def synthetic_response(
    water: float,
    density: float,
    parameters: dict[str, float | tuple[float, float]],
    group_shift: float,
) -> float:
    centred_water = water - 15.0
    density_offset = density - 1.0
    value = (
        float(parameters["base"])
        + float(parameters["water_slope"]) * water
        + float(parameters["density_slope"]) * density_offset
        + float(parameters["curvature"]) * centred_water**2
        + 0.012 * water * density_offset
        + group_shift
    )
    return float(np.clip(value, 0.12, 4.5))


def build_dataset() -> pd.DataFrame:
    rng = np.random.default_rng(SEED)
    rows: list[dict[str, object]] = []
    observation_number = 0
    for lithology, parameters in LITHOLOGY_PARAMETERS.items():
        water_min, water_max = parameters["water"]
        density_min, density_max = parameters["density"]
        assert isinstance(water_min, float) and isinstance(water_max, float)
        assert isinstance(density_min, float) and isinstance(density_max, float)
        for group_index in range(1, 13):
            parent_material_id = f"SYN-{lithology}-GROUP-{group_index:02d}"
            group_shift = float(rng.normal(0.0, 0.045))
            for member_index in range(1, 3):
                material_id = (
                    f"SYN-{lithology}-GROUP-{group_index:02d}-MEMBER-{member_index:02d}"
                )
                group_fraction = (group_index - 1) / 11
                member_offset = (member_index - 1.5) * 0.04
                for state_index in range(1, 3):
                    state_fraction = (state_index - 1) / 1
                    water = (
                        water_min
                        + (water_max - water_min)
                        * np.clip(0.12 + 0.70 * group_fraction + 0.10 * state_fraction, 0, 1)
                        + rng.normal(0.0, 0.55)
                    )
                    density = (
                        density_min
                        + (density_max - density_min)
                        * np.clip(0.10 + 0.74 * group_fraction + member_offset, 0, 1)
                        + 0.018 * state_fraction
                        + rng.normal(0.0, 0.025)
                    )
                    water = float(np.clip(water, water_min, water_max))
                    density = float(np.clip(density, density_min, density_max))
                    state_lambda = synthetic_response(
                        water, density, parameters, group_shift
                    )
                    measurement_count = 2 if (group_index + member_index + state_index) % 3 == 0 else 1
                    for measurement_index in range(1, measurement_count + 1):
                        observation_number += 1
                        measured_lambda = state_lambda + float(rng.normal(0.0, 0.025))
                        rows.append(
                            {
                                "observation_id": f"SYN-OBS-{observation_number:04d}",
                                "material_id": material_id,
                                "parent_material_id": parent_material_id,
                                "lithology": lithology,
                                "water_content_pct": round(water, 4),
                                "bulk_density_mg_m3": round(density, 4),
                                "thermal_conductivity_w_mk": round(
                                    max(measured_lambda, 0.10), 4
                                ),
                                "source": "synthetic_demonstration",
                                "data_origin": "generated_for_workflow_testing",
                            }
                        )
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        default="data/synthetic_example.csv",
        help="Destination CSV path.",
    )
    arguments = parser.parse_args()
    target = Path(arguments.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    table = build_dataset()
    table.to_csv(target, index=False)
    print(target)
    print(
        table.groupby("lithology").agg(
            source_observations=("observation_id", "size"),
            material_ids=("material_id", "nunique"),
            parent_materials=("parent_material_id", "nunique"),
        )
    )


if __name__ == "__main__":
    main()
