from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

import numpy as np
import pandas as pd
from scipy.ndimage import gaussian_filter, maximum_filter, minimum_filter

from .constants import MODEL_FAMILIES, MODEL_VARIANTS


@dataclass(frozen=True)
class RSCISettings:
    lambda_min: float = 0.0
    lambda_max: float = 5.0
    gaussian_sigma: float = 1.0
    extrema_neighbourhood: int = 5
    tolerance_fraction: float = 0.05
    tolerance_percentile: float = 75.0
    weights: dict[str, float] | None = None

    @classmethod
    def from_mapping(cls, config: Mapping[str, Any]) -> "RSCISettings":
        admissible = config.get("admissible_lambda_range", [0.0, 5.0])
        if len(admissible) != 2:
            raise ValueError("admissible_lambda_range must contain exactly two values.")
        return cls(
            lambda_min=float(admissible[0]),
            lambda_max=float(admissible[1]),
            gaussian_sigma=float(config.get("gaussian_smoothing_sigma", 1.0)),
            extrema_neighbourhood=int(config.get("local_extrema_neighbourhood", 5)),
            tolerance_fraction=float(config.get("fragmentation_tolerance_fraction", 0.05)),
            tolerance_percentile=float(config.get("fragmentation_tolerance_percentile", 75.0)),
            weights={str(key): float(value) for key, value in config.get("weights", {}).items()} or None,
        )

    def resolved_weights(self) -> dict[str, float]:
        return self.weights or {
            "bounds_score": 0.20,
            "smoothness_score": 0.25,
            "extrema_score": 0.20,
            "gradient_stability_score": 0.20,
            "fragmentation_score": 0.15,
        }

    def validate(self) -> None:
        if not self.lambda_min < self.lambda_max:
            raise ValueError("lambda_min must be smaller than lambda_max.")
        if self.gaussian_sigma < 0:
            raise ValueError("gaussian_sigma must be non-negative.")
        if self.extrema_neighbourhood < 1:
            raise ValueError("extrema_neighbourhood must be positive.")
        if not 0 <= self.tolerance_fraction:
            raise ValueError("tolerance_fraction must be non-negative.")
        if not 0 <= self.tolerance_percentile <= 100:
            raise ValueError("tolerance_percentile must lie between 0 and 100.")
        weights = self.resolved_weights()
        expected = {
            "bounds_score",
            "smoothness_score",
            "extrema_score",
            "gradient_stability_score",
            "fragmentation_score",
        }
        if set(weights) != expected:
            raise ValueError(f"RSCI weight keys must be {sorted(expected)}.")
        if not np.isclose(sum(weights.values()), 1.0):
            raise ValueError("RSCI weights must sum to 1.0.")


def _fill_for_derivatives(values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    array = np.asarray(values, dtype=float)
    if array.ndim != 2:
        raise ValueError("Response surface must be a two-dimensional array.")
    valid = np.isfinite(array)
    if not valid.any():
        raise ValueError("Response surface contains no valid inside-hull cells.")
    return np.where(valid, array, np.nanmean(array)), valid


def derivatives(
    values: np.ndarray,
    water_values: np.ndarray,
    density_values: np.ndarray,
    sigma: float = 1.0,
) -> dict[str, np.ndarray]:
    filled, valid = _fill_for_derivatives(values)
    water = np.asarray(water_values, dtype=float)
    density = np.asarray(density_values, dtype=float)
    if len(water) < 2 or len(density) < 2:
        raise ValueError("At least two grid coordinates are required in each predictor direction.")
    dw = float(water[1] - water[0])
    drho = float(density[1] - density[0])
    if np.isclose(dw, 0.0) or np.isclose(drho, 0.0):
        raise ValueError("Response-surface grid spacing must be non-zero.")
    smooth = gaussian_filter(filled, sigma=sigma) if sigma > 0 else filled
    d_drho, d_dw = np.gradient(smooth, drho, dw)
    d2_drho2, _ = np.gradient(d_drho, drho, dw)
    _, d2_dw2 = np.gradient(d_dw, drho, dw)
    curvature = np.sqrt(d2_dw2**2 + d2_drho2**2)

    def mask(array: np.ndarray) -> np.ndarray:
        return np.where(valid, array, np.nan)

    return {
        "smooth": mask(smooth),
        "d_dw": mask(d_dw),
        "d_drho": mask(d_drho),
        "curvature": mask(curvature),
    }


def bounds_inputs(values: np.ndarray, settings: RSCISettings) -> dict[str, float]:
    valid_values = np.asarray(values, dtype=float)[np.isfinite(values)]
    if not len(valid_values):
        raise ValueError("Response surface contains no valid values for bounds assessment.")
    negative_fraction = float(np.mean(valid_values < settings.lambda_min))
    above_fraction = float(np.mean(valid_values > settings.lambda_max))
    violation = negative_fraction + above_fraction
    return {
        "bounds_violation_fraction": violation,
        "negative_thermal_conductivity_fraction": negative_fraction,
        "above_max_thermal_conductivity_fraction": above_fraction,
        "bounds_score": float(np.clip(1.0 - violation, 0.0, 1.0)),
    }


def extrema_inputs(smooth: np.ndarray, neighbourhood: int) -> dict[str, int]:
    valid = np.isfinite(smooth)
    if not valid.any():
        raise ValueError("Smoothed response surface contains no valid cells.")
    minimum = np.nanmin(smooth)
    maximum = np.nanmax(smooth)
    for_max = np.where(valid, smooth, minimum - 9999.0)
    for_min = np.where(valid, smooth, maximum + 9999.0)
    local_max = (for_max == maximum_filter(for_max, size=neighbourhood)) & valid
    local_min = (for_min == minimum_filter(for_min, size=neighbourhood)) & valid
    n_max, n_min = int(local_max.sum()), int(local_min.sum())
    return {
        "n_local_maxima": n_max,
        "n_local_minima": n_min,
        "n_local_extrema_total": n_max + n_min,
    }


def _sign_with_tolerance(array: np.ndarray, epsilon: float) -> np.ndarray:
    signs = np.zeros_like(array, dtype=float)
    signs[array > epsilon] = 1.0
    signs[array < -epsilon] = -1.0
    signs[~np.isfinite(array)] = np.nan
    return signs


def _count_sign_changes(values: np.ndarray) -> int:
    valid = values[np.isfinite(values)]
    valid = valid[valid != 0]
    return 0 if len(valid) <= 1 else int(np.sum(valid[1:] != valid[:-1]))


def _fragmentation(gradient: np.ndarray, axis: int, epsilon: float) -> float:
    signs = _sign_with_tolerance(gradient, epsilon)
    if axis == 1:
        changes = [_count_sign_changes(signs[row, :]) for row in range(signs.shape[0])]
    elif axis == 0:
        changes = [_count_sign_changes(signs[:, column]) for column in range(signs.shape[1])]
    else:
        raise ValueError("axis must be 0 or 1")
    return float(np.mean(changes))


def raw_components(
    values: np.ndarray,
    water_values: np.ndarray,
    density_values: np.ndarray,
    settings: RSCISettings | None = None,
) -> dict[str, float]:
    settings = settings or RSCISettings()
    settings.validate()
    derivative_fields = derivatives(values, water_values, density_values, settings.gaussian_sigma)
    valid_dw = derivative_fields["d_dw"][np.isfinite(derivative_fields["d_dw"])]
    valid_drho = derivative_fields["d_drho"][np.isfinite(derivative_fields["d_drho"])]
    if not len(valid_dw) or not len(valid_drho):
        raise ValueError("Response surface contains insufficient valid gradients for RSCI calculation.")
    dw_epsilon = settings.tolerance_fraction * np.percentile(
        np.abs(valid_dw), settings.tolerance_percentile
    )
    drho_epsilon = settings.tolerance_fraction * np.percentile(
        np.abs(valid_drho), settings.tolerance_percentile
    )
    dw_fragmentation = _fragmentation(derivative_fields["d_dw"], 1, float(dw_epsilon))
    drho_fragmentation = _fragmentation(derivative_fields["d_drho"], 0, float(drho_epsilon))
    output: dict[str, float] = {}
    output.update(bounds_inputs(values, settings))
    output["smoothness_raw"] = float(np.nanmedian(np.abs(derivative_fields["curvature"])))
    output.update(extrema_inputs(derivative_fields["smooth"], settings.extrema_neighbourhood))
    dw_std = float(np.std(valid_dw))
    drho_std = float(np.std(valid_drho))
    output.update(
        {
            "dw_gradient_std": dw_std,
            "drho_gradient_std": drho_std,
            "gradient_stability_raw": float(np.sqrt(dw_std**2 + drho_std**2)),
            "dw_fragmentation_raw": dw_fragmentation,
            "drho_fragmentation_raw": drho_fragmentation,
            "fragmentation_raw": float(np.mean([dw_fragmentation, drho_fragmentation])),
            "dw_epsilon": float(dw_epsilon),
            "drho_epsilon": float(drho_epsilon),
        }
    )
    return output


def inverse_minmax(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    minimum, maximum = numeric.min(), numeric.max()
    if pd.isna(minimum) or pd.isna(maximum):
        return pd.Series(np.nan, index=series.index, dtype=float)
    if np.isclose(minimum, maximum):
        return pd.Series(1.0, index=series.index, dtype=float)
    return ((maximum - numeric) / (maximum - minimum)).clip(0.0, 1.0)


def normalise_and_score(
    raw_table: pd.DataFrame,
    settings: RSCISettings | None = None,
) -> pd.DataFrame:
    settings = settings or RSCISettings()
    settings.validate()
    required = {
        "lithology",
        "bounds_score",
        "smoothness_raw",
        "n_local_extrema_total",
        "gradient_stability_raw",
        "fragmentation_raw",
    }
    missing = sorted(required - set(raw_table.columns))
    if missing:
        raise ValueError(f"Missing RSCI input columns: {missing}")
    result = raw_table.copy()
    if "model" in result.columns:
        unsupported = sorted(set(result["model"].astype(str).str.upper()) - set(MODEL_FAMILIES))
        if unsupported:
            raise ValueError(f"RSCI normalisation includes unsupported model families: {unsupported}")
    if "variant" in result.columns:
        unsupported = sorted(set(result["variant"].astype(str).str.upper()) - set(MODEL_VARIANTS))
        if unsupported:
            raise ValueError(f"RSCI normalisation includes unsupported variants: {unsupported}")

    mappings = {
        "smoothness_raw": "smoothness_score",
        "n_local_extrema_total": "extrema_score",
        "gradient_stability_raw": "gradient_stability_score",
        "fragmentation_raw": "fragmentation_score",
    }
    for raw_column, score_column in mappings.items():
        result[score_column] = result.groupby("lithology")[raw_column].transform(inverse_minmax)
    weights = settings.resolved_weights()
    result["RSCI_0_1"] = sum(result[column] * weight for column, weight in weights.items())
    result["RSCI_0_100"] = 100.0 * result["RSCI_0_1"]
    result["RSCI_rank_within_lithology"] = result.groupby("lithology")["RSCI_0_100"].rank(
        ascending=False, method="min"
    )
    return result
