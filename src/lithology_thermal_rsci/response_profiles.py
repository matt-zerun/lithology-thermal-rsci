from __future__ import annotations

import numpy as np
import pandas as pd

from .convex_hull import inside_convex_hull


def extract_profiles(model, observed_X: pd.DataFrame, fixed_density_levels: list[float], fixed_water_levels: list[float], points: int = 200) -> tuple[pd.DataFrame, pd.DataFrame]:
    observed = observed_X[["water_content_pct", "bulk_density_mg_m3"]].to_numpy()
    water_grid = np.linspace(observed_X["water_content_pct"].min(), observed_X["water_content_pct"].max(), points)
    density_grid = np.linspace(observed_X["bulk_density_mg_m3"].min(), observed_X["bulk_density_mg_m3"].max(), points)
    water_rows = []
    for density in fixed_density_levels:
        query = np.column_stack([water_grid, np.full(points, density)])
        mask = inside_convex_hull(observed, query)
        predictions = model.predict(pd.DataFrame(query, columns=["water_content_pct", "bulk_density_mg_m3"]))
        for water, prediction, valid in zip(water_grid, predictions, mask):
            if valid:
                water_rows.append({"water_content_pct": water, "bulk_density_mg_m3": density, "predicted_thermal_conductivity_w_mk": float(prediction)})
    density_rows = []
    for water in fixed_water_levels:
        query = np.column_stack([np.full(points, water), density_grid])
        mask = inside_convex_hull(observed, query)
        predictions = model.predict(pd.DataFrame(query, columns=["water_content_pct", "bulk_density_mg_m3"]))
        for density, prediction, valid in zip(density_grid, predictions, mask):
            if valid:
                density_rows.append({"water_content_pct": water, "bulk_density_mg_m3": density, "predicted_thermal_conductivity_w_mk": float(prediction)})
    return pd.DataFrame(water_rows), pd.DataFrame(density_rows)
