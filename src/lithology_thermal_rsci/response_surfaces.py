from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .constants import FEATURES
from .convex_hull import inside_convex_hull


@dataclass(frozen=True)
class ResponseSurface:
    table: pd.DataFrame
    water_values: np.ndarray
    density_values: np.ndarray
    predicted_grid: np.ndarray
    inside_hull_grid: np.ndarray


def generate_response_surface(model, observed_X: pd.DataFrame, grid_size: int = 80) -> ResponseSurface:
    """Predict a regular grid and mask nodes outside the observed predictor-domain convex hull."""
    if grid_size < 3:
        raise ValueError("grid_size must be at least 3.")
    missing = sorted(set(FEATURES) - set(observed_X.columns))
    if missing:
        raise ValueError(f"Missing predictor columns: {missing}")
    if len(observed_X) < 3:
        raise ValueError("At least three observations are required for response-surface generation.")

    observed = observed_X.loc[:, list(FEATURES)].astype(float)
    water_values = np.linspace(observed["water_content_pct"].min(), observed["water_content_pct"].max(), grid_size)
    density_values = np.linspace(observed["bulk_density_mg_m3"].min(), observed["bulk_density_mg_m3"].max(), grid_size)
    water_grid, density_grid = np.meshgrid(water_values, density_values)
    query = np.column_stack([water_grid.ravel(), density_grid.ravel()])
    mask = inside_convex_hull(observed.to_numpy(), query)
    query_frame = pd.DataFrame(query, columns=list(FEATURES))
    predictions = np.asarray(model.predict(query_frame), dtype=float).reshape(-1)
    if len(predictions) != len(query):
        raise ValueError("Model returned an unexpected number of response-surface predictions.")
    masked_grid = np.where(mask, predictions, np.nan).reshape(water_grid.shape)
    mask_grid = mask.reshape(water_grid.shape)
    table = pd.DataFrame(
        {
            "water_content_pct": query[:, 0],
            "bulk_density_mg_m3": query[:, 1],
            "predicted_thermal_conductivity_w_mk": np.where(mask, predictions, np.nan),
            "inside_hull": mask,
        }
    )
    return ResponseSurface(table, water_values, density_values, masked_grid, mask_grid)
