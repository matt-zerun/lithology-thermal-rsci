from __future__ import annotations

from typing import Any

from sklearn.ensemble import RandomForestRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR
from xgboost import XGBRegressor

from .constants import MODEL_FAMILIES, MODEL_VARIANTS, RANDOM_STATE


class OptionalDependencyError(ImportError):
    """Raised when the required pyGAM dependency is unavailable."""


def _make_gam(parameters: dict[str, Any]):
    try:
        from pygam import LinearGAM, s
    except ImportError as exc:
        raise OptionalDependencyError(
            "pyGAM is required for GAM models. Install the project dependencies before running the four-family workflow."
        ) from exc
    n_splines = int(parameters.get("n_splines", 20))
    lam = float(parameters.get("lam", 0.6))
    if n_splines < 4:
        raise ValueError("GAM n_splines must be at least 4.")
    if lam < 0:
        raise ValueError("GAM lam must be non-negative.")
    return LinearGAM(
        s(0, n_splines=n_splines) + s(1, n_splines=n_splines),
        lam=lam,
        verbose=False,
    )


def build_model(
    family: str,
    variant: str,
    settings: dict[str, Any],
    tuned_parameters: dict[str, Any] | None = None,
):
    family = family.upper()
    variant = variant.upper()
    if family not in MODEL_FAMILIES:
        raise ValueError(f"Unsupported model family: {family}")
    if variant not in MODEL_VARIANTS:
        raise ValueError(f"Unsupported model variant: {variant}")

    if variant == "TUNED":
        if tuned_parameters is None:
            raise ValueError("TUNED variants require lithology-specific tuned parameters.")
        parameters = dict(tuned_parameters)
    else:
        try:
            parameters = dict(settings[family][variant])
        except KeyError as exc:
            raise KeyError(f"Missing settings for {family} {variant}.") from exc

    if family == "SVR":
        return Pipeline(
            [
                ("scaler", StandardScaler()),
                ("model", SVR(**parameters)),
            ]
        )
    if family == "GAM":
        return _make_gam(parameters)
    if family == "RF":
        parameters.setdefault("random_state", RANDOM_STATE)
        parameters.setdefault("n_jobs", 1)
        return RandomForestRegressor(**parameters)
    if family == "XGB":
        parameters.setdefault("objective", "reg:squarederror")
        parameters.setdefault("random_state", RANDOM_STATE)
        parameters.setdefault("n_jobs", 1)
        parameters.setdefault("verbosity", 0)
        return XGBRegressor(**parameters)
    raise AssertionError("Unreachable model-family branch")
