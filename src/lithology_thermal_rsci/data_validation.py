from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .constants import (
    BULK_DENSITY_COLUMN,
    DRY_DENSITY_COLUMN,
    FEATURES,
    LITHOLOGIES,
    LITHOLOGY_COLUMN,
    MATERIAL_ID_COLUMN,
    MEASUREMENT_TEMPERATURE_COLUMN,
    OBSERVATION_ID_COLUMN,
    OPTIONAL_COLUMNS,
    PARENT_MATERIAL_ID_COLUMN,
    PARTICLE_DENSITY_COLUMN,
    REQUIRED_COLUMNS,
    TARGET,
    WATER_CONTENT_COLUMN,
)


class InputValidationError(ValueError):
    """Actionable error raised when canonical input is not valid."""


@dataclass(frozen=True)
class ValidationReport:
    n_input_observations: int
    n_valid_observations: int
    counts_by_lithology: dict[str, int]
    optional_columns_present: tuple[str, ...]


def read_table(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Input file not found: {path}")
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix in {".xlsx", ".xlsm"}:
        return pd.read_excel(path)
    raise ValueError(f"Unsupported input format: {suffix}. Use CSV or XLSX.")


def _row_examples(mask: pd.Series, limit: int = 5) -> list[int]:
    """Return one-based CSV-like row numbers, including the header offset."""
    return (np.flatnonzero(mask.to_numpy())[:limit] + 2).astype(int).tolist()


def _require_numeric(table: pd.DataFrame, columns: list[str]) -> None:
    for column in columns:
        supplied = table[column]
        numeric = pd.to_numeric(supplied, errors="coerce")
        invalid = supplied.notna() & numeric.isna()
        if invalid.any():
            raise InputValidationError(
                f"Column '{column}' contains non-numeric values at input rows "
                f"{_row_examples(invalid)}. Use the unit documented in DATA_SCHEMA.md."
            )
        infinite = numeric.notna() & ~np.isfinite(numeric)
        if infinite.any():
            raise InputValidationError(
                f"Column '{column}' contains infinite values at input rows "
                f"{_row_examples(infinite)}."
            )
        table[column] = numeric


def validate_and_prepare(
    df: pd.DataFrame,
    min_records_per_lithology: int = 10,
    density_identity_abs_tolerance_mg_m3: float = 0.02,
    density_identity_rel_tolerance: float = 0.02,
) -> tuple[pd.DataFrame, ValidationReport]:
    """Validate canonical observations without silent coercion or row removal."""
    if min_records_per_lithology < 3:
        raise InputValidationError("min_records_per_lithology must be at least 3.")
    missing_columns = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing_columns:
        raise InputValidationError(
            "Missing required columns: " + ", ".join(missing_columns)
        )

    retained_columns = list(REQUIRED_COLUMNS) + [
        column for column in OPTIONAL_COLUMNS if column in df.columns
    ]
    prepared = df.loc[:, retained_columns].copy()
    missing_required = prepared[list(REQUIRED_COLUMNS)].isna()
    if missing_required.any().any():
        details = []
        for column in REQUIRED_COLUMNS:
            mask = missing_required[column]
            if mask.any():
                details.append(f"{column}: rows {_row_examples(mask)}")
        raise InputValidationError(
            "Required values are missing (CSV row numbers): " + "; ".join(details)
        )

    text_columns = [
        OBSERVATION_ID_COLUMN,
        MATERIAL_ID_COLUMN,
        PARENT_MATERIAL_ID_COLUMN,
        "source",
        "data_origin",
    ]
    for column in text_columns:
        prepared[column] = prepared[column].astype("string").str.strip()
        empty = prepared[column].eq("")
        if empty.any():
            raise InputValidationError(
                f"Column '{column}' contains empty values at input rows "
                f"{_row_examples(empty)}."
            )

    prepared[LITHOLOGY_COLUMN] = (
        prepared[LITHOLOGY_COLUMN]
        .astype("string")
        .str.lower()
        .str.strip()
        .str.replace(" ", "_", regex=False)
    )
    empty_lithology = prepared[LITHOLOGY_COLUMN].eq("")
    if empty_lithology.any():
        raise InputValidationError(
            f"Column '{LITHOLOGY_COLUMN}' contains empty values at input rows "
            f"{_row_examples(empty_lithology)}."
        )
    unknown = sorted(set(prepared[LITHOLOGY_COLUMN]) - set(LITHOLOGIES))
    if unknown:
        raise InputValidationError(
            f"Unknown lithology values: {unknown}. Allowed values: {list(LITHOLOGIES)}."
        )

    duplicates = prepared[OBSERVATION_ID_COLUMN].duplicated(keep=False)
    if duplicates.any():
        examples = (
            prepared.loc[duplicates, OBSERVATION_ID_COLUMN]
            .astype(str)
            .head(5)
            .tolist()
        )
        raise InputValidationError(
            f"Duplicate observation_id values detected, examples: {examples}."
        )

    numeric_columns = [*FEATURES, TARGET] + [
        column
        for column in OPTIONAL_COLUMNS
        if column in prepared.columns
    ]
    _require_numeric(prepared, numeric_columns)
    for column in (*FEATURES, TARGET):
        missing = prepared[column].isna()
        if missing.any():
            raise InputValidationError(
                f"Column '{column}' contains missing numeric values at input rows "
                f"{_row_examples(missing)}."
            )

    negative_water = prepared[WATER_CONTENT_COLUMN] < 0
    if negative_water.any():
        raise InputValidationError(
            f"{WATER_CONTENT_COLUMN} cannot be negative; input rows "
            f"{_row_examples(negative_water)}."
        )
    invalid_bulk = prepared[BULK_DENSITY_COLUMN] <= 0
    if invalid_bulk.any():
        raise InputValidationError(
            f"{BULK_DENSITY_COLUMN} must be positive; input rows "
            f"{_row_examples(invalid_bulk)}."
        )
    invalid_lambda = prepared[TARGET] <= 0
    if invalid_lambda.any():
        raise InputValidationError(
            f"{TARGET} must be positive; input rows {_row_examples(invalid_lambda)}."
        )

    likely_density_units = prepared[BULK_DENSITY_COLUMN] > 10
    if likely_density_units.any():
        raise InputValidationError(
            f"{BULK_DENSITY_COLUMN} exceeds 10 Mg m^-3 at input rows "
            f"{_row_examples(likely_density_units)}; values may be in kg m^-3."
        )
    likely_lambda_units = prepared[TARGET] > 50
    if likely_lambda_units.any():
        raise InputValidationError(
            f"{TARGET} exceeds 50 W m^-1 K^-1 at input rows "
            f"{_row_examples(likely_lambda_units)}; verify units and material scope."
        )

    for column in (DRY_DENSITY_COLUMN, PARTICLE_DENSITY_COLUMN):
        if column not in prepared.columns:
            continue
        invalid = prepared[column].notna() & (prepared[column] <= 0)
        if invalid.any():
            raise InputValidationError(
                f"{column} must be positive when supplied; input rows "
                f"{_row_examples(invalid)}."
            )
        likely_units = prepared[column].notna() & (prepared[column] > 10)
        if likely_units.any():
            raise InputValidationError(
                f"{column} exceeds 10 Mg m^-3 at input rows "
                f"{_row_examples(likely_units)}; values may be in kg m^-3."
            )

    if DRY_DENSITY_COLUMN in prepared.columns:
        comparable = prepared[DRY_DENSITY_COLUMN].notna()
        dry_exceeds_wet = comparable & (
            prepared[DRY_DENSITY_COLUMN] > prepared[BULK_DENSITY_COLUMN]
        )
        if dry_exceeds_wet.any():
            raise InputValidationError(
                f"{DRY_DENSITY_COLUMN} exceeds {BULK_DENSITY_COLUMN} at input rows "
                f"{_row_examples(dry_exceeds_wet)}."
            )
        expected_bulk = prepared[DRY_DENSITY_COLUMN] * (
            1.0 + prepared[WATER_CONTENT_COLUMN] / 100.0
        )
        tolerance = density_identity_abs_tolerance_mg_m3 + (
            density_identity_rel_tolerance * prepared[BULK_DENSITY_COLUMN].abs()
        )
        inconsistent = comparable & (
            (prepared[BULK_DENSITY_COLUMN] - expected_bulk).abs() > tolerance
        )
        if inconsistent.any():
            raise InputValidationError(
                "Wet/dry-density identity is inconsistent at input rows "
                f"{_row_examples(inconsistent)}. Expected {BULK_DENSITY_COLUMN} = "
                f"{DRY_DENSITY_COLUMN} * (1 + {WATER_CONTENT_COLUMN}/100)."
            )

    if PARTICLE_DENSITY_COLUMN in prepared.columns:
        comparable = prepared[PARTICLE_DENSITY_COLUMN].notna()
        bulk_exceeds_particle = comparable & (
            prepared[BULK_DENSITY_COLUMN] > prepared[PARTICLE_DENSITY_COLUMN]
        )
        if bulk_exceeds_particle.any():
            raise InputValidationError(
                f"{BULK_DENSITY_COLUMN} exceeds {PARTICLE_DENSITY_COLUMN} at input rows "
                f"{_row_examples(bulk_exceeds_particle)}."
            )

    if MEASUREMENT_TEMPERATURE_COLUMN in prepared.columns:
        # No physical exclusion is introduced; the check above only enforces
        # finite numeric metadata where a value is supplied.
        pass

    counts = (
        prepared[LITHOLOGY_COLUMN]
        .value_counts()
        .reindex(LITHOLOGIES, fill_value=0)
    )
    too_small = counts[counts < min_records_per_lithology]
    if not too_small.empty:
        raise InputValidationError(
            f"Too few records for lithologies: {too_small.to_dict()}; "
            f"at least {min_records_per_lithology} are required for each."
        )

    report = ValidationReport(
        n_input_observations=len(prepared),
        n_valid_observations=len(prepared),
        counts_by_lithology={key: int(value) for key, value in counts.items()},
        optional_columns_present=tuple(
            column for column in OPTIONAL_COLUMNS if column in prepared.columns
        ),
    )
    return prepared.reset_index(drop=True), report
