from __future__ import annotations

import argparse
import re
from pathlib import Path

import numpy as np
import pandas as pd

from lithology_thermal_rsci.config import load_json
from lithology_thermal_rsci.rsci import RSCISettings, normalise_and_score, raw_components

PATTERN = re.compile(
    r"^(sand|silt|clayey_soil|clay)_(SVR|GAM|RF|XGB)_(BASE|SMOOTH|INTERMEDIATE|TUNED)$"
)


def _coerce_inside_hull(series: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series
    mapping = {"true": True, "false": False, "1": True, "0": False}
    converted = series.astype(str).str.strip().str.lower().map(mapping)
    if converted.isna().any():
        examples = series.loc[converted.isna()].astype(str).head(5).tolist()
        raise ValueError(f"Unrecognised inside_hull values, examples: {examples}")
    return converted.astype(bool)


def table_to_arrays(table: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    required = {"water_content_pct", "bulk_density_mg_m3", "predicted_thermal_conductivity_w_mk", "inside_hull"}
    missing = sorted(required - set(table.columns))
    if missing:
        raise ValueError(f"Response-surface table is missing columns: {missing}")
    mask = _coerce_inside_hull(table["inside_hull"])
    inside = table.loc[mask].copy()
    water = np.sort(pd.to_numeric(table["water_content_pct"], errors="raise").unique())
    density = np.sort(pd.to_numeric(table["bulk_density_mg_m3"], errors="raise").unique())
    pivot = (
        inside.pivot_table(
            index="bulk_density_mg_m3",
            columns="water_content_pct",
            values="predicted_thermal_conductivity_w_mk",
            aggfunc="mean",
        )
        .reindex(index=density, columns=water)
    )
    return pivot.to_numpy(), water, density


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Calculate raw RSCI diagnostics and within-lithology normalised scores."
    )
    parser.add_argument("--surfaces", default="workflow_outputs/response_surfaces")
    parser.add_argument("--raw-output", default="workflow_outputs/rsci_raw_components.csv")
    parser.add_argument("--score-output", default="workflow_outputs/rsci_scores.csv")
    arguments = parser.parse_args()

    settings = RSCISettings.from_mapping(load_json("config/rsci_definition.json"))
    settings.validate()
    rows = []
    for path in sorted(Path(arguments.surfaces).glob("*.csv")):
        match = PATTERN.match(path.stem)
        if not match:
            continue
        lithology, model, variant = match.groups()
        values, water, density = table_to_arrays(pd.read_csv(path))
        rows.append(
            {
                "lithology": lithology,
                "model": model,
                "variant": variant,
                **raw_components(values, water, density, settings),
            }
        )
    if not rows:
        raise FileNotFoundError(f"No recognised response-surface CSV files in {arguments.surfaces}")
    raw = pd.DataFrame(rows)
    scored = normalise_and_score(raw, settings)
    raw_path = Path(arguments.raw_output)
    score_path = Path(arguments.score_output)
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    score_path.parent.mkdir(parents=True, exist_ok=True)
    raw.to_csv(raw_path, index=False)
    scored.to_csv(score_path, index=False)
    print(raw_path)
    print(score_path)


if __name__ == "__main__":
    main()
