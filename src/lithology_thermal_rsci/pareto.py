from __future__ import annotations

import pandas as pd


def mark_pareto_front(
    table: pd.DataFrame,
    accuracy_column: str = "R2_OOF",
    consistency_column: str = "RSCI_0_100",
) -> pd.DataFrame:
    required = {"lithology", accuracy_column, consistency_column}
    missing = required - set(table.columns)
    if missing:
        raise ValueError(f"Missing Pareto columns: {sorted(missing)}")
    result = table.copy()
    result["pareto_optimal"] = False
    for lithology, group in result.groupby("lithology"):
        for index, candidate in group.iterrows():
            dominated = (
                (group[accuracy_column] >= candidate[accuracy_column])
                & (group[consistency_column] >= candidate[consistency_column])
                & (
                    (group[accuracy_column] > candidate[accuracy_column])
                    | (group[consistency_column] > candidate[consistency_column])
                )
            ).any()
            result.loc[index, "pareto_optimal"] = not bool(dominated)
    return result
