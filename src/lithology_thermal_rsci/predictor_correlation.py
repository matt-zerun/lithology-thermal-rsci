from __future__ import annotations

import numpy as np
import pandas as pd

from .constants import FEATURES, LITHOLOGIES, MATERIAL_ID_COLUMN, PARENT_MATERIAL_ID_COLUMN


def _correlation_row(
    table: pd.DataFrame,
    analysis_level: str,
    subset: str,
) -> dict[str, object]:
    values = table.loc[:, list(FEATURES)].astype(float)
    finite = np.isfinite(values).all(axis=1)
    analysed = table.loc[finite].copy()
    if len(analysed) < 2:
        pearson = np.nan
        spearman = np.nan
    else:
        pearson = analysed[FEATURES[0]].corr(analysed[FEATURES[1]], method="pearson")
        spearman = analysed[FEATURES[0]].corr(analysed[FEATURES[1]], method="spearman")
    return {
        "analysis_level": analysis_level,
        "subset": subset,
        "n_records": int(len(analysed)),
        "n_unique_materials": int(analysed[MATERIAL_ID_COLUMN].nunique()),
        "n_parent_materials": int(analysed[PARENT_MATERIAL_ID_COLUMN].nunique()),
        "pearson_r": float(pearson),
        "spearman_rho": float(spearman),
    }


def predictor_correlation_table(
    observations: pd.DataFrame,
    material_states: pd.DataFrame,
) -> pd.DataFrame:
    """Calculate w–rho_b correlations at state and observation levels.

    The unique-material-state analysis is primary. The all-observation analysis
    is a sensitivity check showing how repeated conductivity readings reweight
    otherwise identical predictor states.
    """
    rows: list[dict[str, object]] = []
    levels = (
        ("unique_material_states", material_states),
        ("all_observations", observations),
    )
    for level_name, table in levels:
        rows.append(_correlation_row(table, level_name, "all"))
        for lithology in LITHOLOGIES:
            subset = table.loc[table["lithology"] == lithology]
            rows.append(_correlation_row(subset, level_name, lithology))
        experimental = table.loc[
            table["data_origin"].astype(str).str.lower().str.strip() == "experimental"
        ]
        if not experimental.empty:
            rows.append(
                _correlation_row(
                    experimental,
                    level_name,
                    "experimental_only",
                )
            )
    return pd.DataFrame(rows)
