from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .constants import (
    FEATURES,
    LITHOLOGIES,
    MATERIAL_ID_COLUMN,
    MATERIAL_STATE_ID_COLUMN,
    TARGET,
    PARENT_MATERIAL_ID_COLUMN,
)


STATE_KEYS = (MATERIAL_ID_COLUMN, "lithology", *FEATURES)
PROVENANCE_COLUMNS = ("source", "data_origin")


@dataclass(frozen=True)
class StateAggregationReport:
    n_observations: int
    n_material_states: int
    n_unique_materials: int
    n_parent_materials: int
    counts_by_lithology: dict[str, int]
    measurement_count_distribution: dict[int, int]


def _check_material_metadata(df: pd.DataFrame) -> None:
    """Require each material identifier to refer to one parent and provenance."""
    metadata_columns = (
        PARENT_MATERIAL_ID_COLUMN,
        "lithology",
        *PROVENANCE_COLUMNS,
    )
    grouped = df.groupby(MATERIAL_ID_COLUMN, sort=False, dropna=False)
    for column in metadata_columns:
        conflicts = grouped[column].nunique(dropna=False)
        conflicts = conflicts.loc[conflicts > 1]
        if not conflicts.empty:
            examples = conflicts.index.astype(str).tolist()[:5]
            raise ValueError(
                f"material_id must map to one {column}; conflicting examples: {examples}"
            )


def aggregate_material_states(
    observations: pd.DataFrame,
) -> tuple[pd.DataFrame, StateAggregationReport]:
    """Aggregate conductivity measurements mapped to identical material states.

    A material state is defined by ``material_id``, lithological group, gravimetric
    water content, and wet bulk density. The model target is the arithmetic mean
    of all thermal-conductivity measurements mapped to the state. Measurement
    dispersion and counts are retained for audit purposes but are not used as
    predictors. ``measurement_count`` records every contributing conductivity
    measurement and does not imply that all measurements are technical replicates.
    """
    required = {
        "observation_id",
        MATERIAL_ID_COLUMN,
        PARENT_MATERIAL_ID_COLUMN,
        "lithology",
        *FEATURES,
        TARGET,
        *PROVENANCE_COLUMNS,
    }
    missing = sorted(required - set(observations.columns))
    if missing:
        raise ValueError(f"Cannot aggregate material states; missing columns: {missing}")
    if observations.empty:
        raise ValueError("Cannot aggregate an empty observation table.")

    _check_material_metadata(observations)
    grouped = observations.groupby(list(STATE_KEYS), sort=False, dropna=False)
    states = (
        grouped
        .agg(
            thermal_conductivity_w_mk=(TARGET, "mean"),
            thermal_conductivity_sd_w_mk=(TARGET, "std"),
            thermal_conductivity_min_w_mk=(TARGET, "min"),
            thermal_conductivity_max_w_mk=(TARGET, "max"),
            measurement_count=(TARGET, "size"),
            parent_material_id=(PARENT_MATERIAL_ID_COLUMN, "first"),
            source=("source", "first"),
            data_origin=("data_origin", "first"),
            first_observation_id=("observation_id", "first"),
        )
        .reset_index()
    )
    states.insert(
        0,
        MATERIAL_STATE_ID_COLUMN,
        [f"STATE_{index:06d}" for index in range(1, len(states) + 1)],
    )
    if states[MATERIAL_STATE_ID_COLUMN].duplicated().any():
        raise AssertionError("Generated material-state identifiers are not unique.")
    if int(states["measurement_count"].sum()) != len(observations):
        raise AssertionError("Material-state aggregation did not preserve observation counts.")

    counts = states["lithology"].value_counts().reindex(LITHOLOGIES, fill_value=0)
    measurement_distribution = states["measurement_count"].value_counts().sort_index()
    report = StateAggregationReport(
        n_observations=len(observations),
        n_material_states=len(states),
        n_unique_materials=int(states[MATERIAL_ID_COLUMN].nunique()),
        n_parent_materials=int(states[PARENT_MATERIAL_ID_COLUMN].nunique()),
        counts_by_lithology={key: int(value) for key, value in counts.items()},
        measurement_count_distribution={
            int(key): int(value) for key, value in measurement_distribution.items()
        },
    )
    return states.reset_index(drop=True), report
