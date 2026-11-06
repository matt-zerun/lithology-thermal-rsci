from __future__ import annotations

from itertools import product
from typing import Any
import warnings

import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error
from sklearn.model_selection import GroupKFold, ParameterGrid, RandomizedSearchCV
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR
from xgboost import XGBRegressor

from .constants import RANDOM_STATE
from .model_factory import OptionalDependencyError


def _python_scalar(value: Any) -> Any:
    return value.item() if isinstance(value, np.generic) else value


def _randomised_search(
    estimator,
    parameter_distributions: dict[str, list[Any]],
    X,
    y,
    groups,
    cv: GroupKFold,
    n_iter: int,
):
    maximum_combinations = len(ParameterGrid(parameter_distributions))
    effective_iterations = min(int(n_iter), maximum_combinations)
    search = RandomizedSearchCV(
        estimator=estimator,
        param_distributions=parameter_distributions,
        n_iter=effective_iterations,
        scoring="neg_root_mean_squared_error",
        cv=cv,
        random_state=RANDOM_STATE,
        n_jobs=-1,
        refit=True,
        error_score="raise",
    )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        search.fit(X, y, groups=groups)
    return (
        {_key: _python_scalar(_value) for _key, _value in search.best_params_.items()},
        float(-search.best_score_),
    )


def tune_model(
    family: str,
    X,
    y,
    groups,
    search_space: dict[str, list[Any]],
    cv_folds: int = 5,
    random_search_iterations: int = 25,
) -> tuple[dict[str, Any], float]:
    """Tune one model family by material-series-grouped RMSE CV."""
    family = family.upper()
    if cv_folds < 2:
        raise ValueError("cv_folds must be at least 2.")
    groups_array = np.asarray(groups)
    if len(groups_array) != len(y):
        raise ValueError("groups must have the same length as the training target.")
    if len(np.unique(groups_array)) < cv_folds:
        raise ValueError(
            f"At least {cv_folds} unique material groups are required for grouped CV."
        )
    cv = GroupKFold(n_splits=cv_folds)

    if family == "SVR":
        estimator = Pipeline([("scaler", StandardScaler()), ("model", SVR(kernel="rbf"))])
        distributions = {f"model__{key}": values for key, values in search_space.items()}
        best, score = _randomised_search(
            estimator,
            distributions,
            X,
            y,
            groups_array,
            cv,
            random_search_iterations,
        )
        parameters = {key.removeprefix("model__"): value for key, value in best.items()}
        parameters["kernel"] = "rbf"
        return parameters, score

    if family == "RF":
        estimator = RandomForestRegressor(random_state=RANDOM_STATE, n_jobs=1)
        return _randomised_search(
            estimator,
            search_space,
            X,
            y,
            groups_array,
            cv,
            random_search_iterations,
        )

    if family == "XGB":
        estimator = XGBRegressor(
            objective="reg:squarederror",
            random_state=RANDOM_STATE,
            n_jobs=1,
            verbosity=0,
        )
        parameters, score = _randomised_search(
            estimator,
            search_space,
            X,
            y,
            groups_array,
            cv,
            random_search_iterations,
        )
        parameters["objective"] = "reg:squarederror"
        return parameters, score

    if family == "GAM":
        try:
            from pygam import LinearGAM, s
        except ImportError as exc:
            raise OptionalDependencyError("pyGAM is required for GAM tuning.") from exc

        X_array = np.asarray(X, dtype=float)
        y_array = np.asarray(y, dtype=float)
        best_score = np.inf
        best_params: dict[str, Any] | None = None
        for lam, n_splines in product(search_space["lam"], search_space["n_splines"]):
            fold_scores: list[float] = []
            for train_index, validation_index in cv.split(
                X_array,
                y_array,
                groups=groups_array,
            ):
                model = LinearGAM(
                    s(0, n_splines=int(n_splines)) + s(1, n_splines=int(n_splines)),
                    lam=float(lam),
                    verbose=False,
                )
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    model.fit(X_array[train_index], y_array[train_index])
                prediction = model.predict(X_array[validation_index])
                fold_scores.append(
                    float(
                        np.sqrt(
                            mean_squared_error(
                                y_array[validation_index], prediction
                            )
                        )
                    )
                )
            mean_score = float(np.mean(fold_scores))
            if mean_score < best_score:
                best_score = mean_score
                best_params = {"lam": float(lam), "n_splines": int(n_splines)}
        if best_params is None:
            raise RuntimeError("GAM tuning produced no valid candidate.")
        return best_params, best_score

    raise ValueError(f"Unsupported model family: {family}")
