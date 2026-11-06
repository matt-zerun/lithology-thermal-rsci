import numpy as np
import pandas as pd

from lithology_thermal_rsci.model_tuning import tune_model


def _training_data():
    rng = np.random.default_rng(42)
    water = rng.uniform(1, 25, 60)
    density = rng.uniform(1.2, 2.2, 60)
    X = pd.DataFrame({"water_content_pct": water, "bulk_density_mg_m3": density})
    y = pd.Series(0.5 + 0.025 * water + 0.9 * density + rng.normal(0, 0.03, 60))
    groups = pd.Series([f"sample-{index // 2}" for index in range(60)])
    return X, y, groups


def test_gam_tuning_returns_supported_parameters():
    X, y, groups = _training_data()
    parameters, score = tune_model(
        "GAM",
        X,
        y,
        groups,
        {"lam": [1.0, 10.0], "n_splines": [10]},
        cv_folds=3,
        random_search_iterations=2,
    )
    assert set(parameters) == {"lam", "n_splines"}
    assert parameters["n_splines"] == 10
    assert np.isfinite(score)


def test_svr_randomised_tuning_returns_rbf_parameters():
    X, y, groups = _training_data()
    parameters, score = tune_model(
        "SVR",
        X,
        y,
        groups,
        {"C": [1.0, 10.0], "epsilon": [0.05], "gamma": ["scale", 0.1]},
        cv_folds=3,
        random_search_iterations=3,
    )
    assert parameters["kernel"] == "rbf"
    assert np.isfinite(score)
