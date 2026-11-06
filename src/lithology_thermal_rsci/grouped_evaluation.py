from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any
import warnings

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold

from .constants import (
    FEATURES,
    GROUP_COLUMN,
    MATERIAL_ID_COLUMN,
    MATERIAL_STATE_ID_COLUMN,
    TARGET,
)
from .model_evaluation import regression_metrics
from .model_factory import build_model
from .model_tuning import tune_model


NESTED_CV_PROTOCOL = "material_series_nested_groupkfold_rmse_v2"


@dataclass(frozen=True)
class GroupedFold:
    number: int
    train_indices: np.ndarray
    test_indices: np.ndarray


@dataclass(frozen=True)
class GroupedFoldPlan:
    folds: tuple[GroupedFold, ...]
    assignments: pd.DataFrame
    audit: pd.DataFrame


@dataclass(frozen=True)
class CandidateEvaluation:
    summary: dict[str, object]
    fold_metrics: pd.DataFrame
    oof_predictions: pd.DataFrame
    tuning_records: tuple[dict[str, object], ...]


def build_grouped_fold_plan(
    material_states: pd.DataFrame,
    n_splits: int = 5,
) -> GroupedFoldPlan:
    """Create deterministic outer folds with zero parent-material overlap."""
    required = {
        MATERIAL_STATE_ID_COLUMN,
        MATERIAL_ID_COLUMN,
        GROUP_COLUMN,
        "lithology",
        *FEATURES,
        TARGET,
    }
    missing = sorted(required - set(material_states.columns))
    if missing:
        raise ValueError(f"Material-state table is missing grouped-CV columns: {missing}")
    if material_states.empty:
        raise ValueError("Cannot build grouped folds for an empty material-state table.")
    lithologies = material_states["lithology"].astype(str).unique()
    if len(lithologies) != 1:
        raise ValueError("A grouped fold plan must contain exactly one lithological group.")
    if n_splits < 2:
        raise ValueError("n_splits must be at least 2.")

    groups = material_states[GROUP_COLUMN].astype(str).reset_index(drop=True)
    state_ids = material_states[MATERIAL_STATE_ID_COLUMN].astype(str).reset_index(drop=True)
    if groups.nunique() < n_splits:
        raise ValueError(
            f"At least {n_splits} unique parent_material_id values are required for grouped CV."
        )
    X = material_states.loc[:, list(FEATURES)].reset_index(drop=True)
    y = material_states[TARGET].reset_index(drop=True)
    splitter = GroupKFold(n_splits=n_splits)
    coverage = np.zeros(len(material_states), dtype=int)
    fold_objects: list[GroupedFold] = []
    assignment_rows: list[dict[str, object]] = []
    audit_rows: list[dict[str, object]] = []

    for fold_number, (train_indices, test_indices) in enumerate(
        splitter.split(X, y, groups=groups),
        start=1,
    ):
        train_groups = groups.iloc[train_indices]
        test_groups = groups.iloc[test_indices]
        overlap = set(train_groups) & set(test_groups)
        if overlap:
            raise AssertionError(
                "Parent-material leakage detected in outer fold "
                f"{fold_number}: {sorted(overlap)[:5]}"
            )
        coverage[test_indices] += 1
        fold_objects.append(
            GroupedFold(
                number=fold_number,
                train_indices=np.asarray(train_indices, dtype=int),
                test_indices=np.asarray(test_indices, dtype=int),
            )
        )
        for index in test_indices:
            assignment_rows.append(
                {
                    "lithology": str(lithologies[0]),
                    MATERIAL_STATE_ID_COLUMN: state_ids.iloc[index],
                    GROUP_COLUMN: groups.iloc[index],
                    MATERIAL_ID_COLUMN: str(
                        material_states.iloc[index][MATERIAL_ID_COLUMN]
                    ),
                    "outer_fold": fold_number,
                }
            )
        audit_rows.append(
            {
                "lithology": str(lithologies[0]),
                "outer_fold": fold_number,
                "n_train_states": len(train_indices),
                "n_validation_states": len(test_indices),
                "n_train_parent_materials": int(train_groups.nunique()),
                "n_validation_parent_materials": int(test_groups.nunique()),
                "n_overlapping_parent_materials": len(overlap),
            }
        )

    if not np.all(coverage == 1):
        raise AssertionError("Each material state must occur in exactly one outer validation fold.")
    assignments = pd.DataFrame(assignment_rows).sort_values(MATERIAL_STATE_ID_COLUMN).reset_index(drop=True)
    if assignments[MATERIAL_STATE_ID_COLUMN].duplicated().any():
        raise AssertionError("A material state was assigned to more than one outer fold.")
    return GroupedFoldPlan(
        folds=tuple(fold_objects),
        assignments=assignments,
        audit=pd.DataFrame(audit_rows),
    )


def _read_or_tune_parameters(
    *,
    cache_file: Path | None,
    tune_missing: bool,
    family: str,
    lithology: str,
    scope: str,
    X_train: pd.DataFrame,
    y_train: pd.Series,
    groups_train: pd.Series,
    search_space: dict[str, list[Any]],
    inner_folds: int,
    random_search_iterations: int,
) -> tuple[dict[str, Any], float, dict[str, object]]:
    if cache_file is not None and cache_file.exists():
        payload = json.loads(cache_file.read_text(encoding="utf-8"))
        expected = {
            "protocol": NESTED_CV_PROTOCOL,
            "lithology": lithology,
            "model": family,
            "scope": scope,
            "tuning_criterion": "RMSE",
        }
        mismatches = {
            key: (payload.get(key), value)
            for key, value in expected.items()
            if payload.get(key) != value
        }
        if mismatches:
            raise ValueError(
                f"Cached tuning metadata do not match the requested analysis: {mismatches}"
            )
        return payload["parameters"], float(payload["inner_CV_RMSE_mean"]), payload
    if not tune_missing:
        raise FileNotFoundError(f"Missing nested-CV tuning file: {cache_file}")

    groups_for_audit = pd.Series(groups_train, dtype="string").reset_index(drop=True)
    audit_splitter = GroupKFold(n_splits=inner_folds)
    inner_fold_audit: list[dict[str, int]] = []
    dummy_X = np.zeros((len(groups_for_audit), 1), dtype=float)
    for fold_number, (train_index, validation_index) in enumerate(
        audit_splitter.split(dummy_X, groups=groups_for_audit), start=1
    ):
        train_groups = set(groups_for_audit.iloc[train_index])
        validation_groups = set(groups_for_audit.iloc[validation_index])
        inner_fold_audit.append(
            {
                "inner_fold": fold_number,
                "n_train_parent_materials": len(train_groups),
                "n_validation_parent_materials": len(validation_groups),
                "n_overlapping_parent_materials": len(
                    train_groups & validation_groups
                ),
            }
        )

    parameters, cv_rmse = tune_model(
        family,
        X_train,
        y_train,
        groups_train,
        search_space,
        cv_folds=inner_folds,
        random_search_iterations=random_search_iterations,
    )
    payload = {
        "protocol": NESTED_CV_PROTOCOL,
        "lithology": lithology,
        "model": family,
        "scope": scope,
        "tuning_criterion": "RMSE",
        "parameters": parameters,
        "inner_CV_RMSE_mean": cv_rmse,
        "n_training_states": len(X_train),
        "n_training_parent_materials": int(pd.Series(groups_train).nunique()),
        "inner_group_folds": inner_folds,
        "group_column": GROUP_COLUMN,
        "inner_fold_group_overlap_audit": inner_fold_audit,
    }
    if cache_file is not None:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return parameters, cv_rmse, payload


def evaluate_candidate_grouped_cv(
    material_states: pd.DataFrame,
    fold_plan: GroupedFoldPlan,
    family: str,
    variant: str,
    settings: dict[str, Any],
    tuning_config: dict[str, Any],
    tuning_cache_dir: str | Path | None = None,
    tune_missing: bool = True,
) -> CandidateEvaluation:
    """Evaluate one candidate using outer grouped CV and nested tuning."""
    family = family.upper()
    variant = variant.upper()
    lithologies = material_states["lithology"].astype(str).unique()
    if len(lithologies) != 1:
        raise ValueError("Candidate evaluation requires exactly one lithological group.")
    lithology = str(lithologies[0])
    data = material_states.reset_index(drop=True)
    X = data.loc[:, list(FEATURES)]
    y = data[TARGET]
    groups = data[GROUP_COLUMN].astype(str)
    material_ids = data[MATERIAL_ID_COLUMN].astype(str)
    state_ids = data[MATERIAL_STATE_ID_COLUMN].astype(str)
    inner_folds = int(tuning_config["inner_cross_validation_folds"])
    iterations = int(tuning_config["random_search_iterations"])
    cache_dir = None if tuning_cache_dir is None else Path(tuning_cache_dir)

    oof = np.full(len(data), np.nan, dtype=float)
    fold_rows: list[dict[str, object]] = []
    prediction_rows: list[dict[str, object]] = []
    tuning_records: list[dict[str, object]] = []

    for fold in fold_plan.folds:
        X_train = X.iloc[fold.train_indices]
        X_validation = X.iloc[fold.test_indices]
        y_train = y.iloc[fold.train_indices]
        y_validation = y.iloc[fold.test_indices]
        groups_train = groups.iloc[fold.train_indices]
        groups_validation = groups.iloc[fold.test_indices]
        tuned_parameters = None
        if variant == "TUNED":
            cache_file = None
            if cache_dir is not None:
                cache_file = cache_dir / (
                    f"{lithology}_{family}_outer_fold_{fold.number}.json"
                )
            tuned_parameters, _, payload = _read_or_tune_parameters(
                cache_file=cache_file,
                tune_missing=tune_missing,
                family=family,
                lithology=lithology,
                scope=f"outer_fold_{fold.number}",
                X_train=X_train,
                y_train=y_train,
                groups_train=groups_train,
                search_space=tuning_config[family],
                inner_folds=inner_folds,
                random_search_iterations=iterations,
            )
            tuning_records.append(payload)

        model = build_model(family, variant, settings, tuned_parameters)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            model.fit(X_train, y_train)
        predictions = np.asarray(model.predict(X_validation), dtype=float)
        if len(predictions) != len(fold.test_indices):
            raise ValueError("Model returned an unexpected number of outer-fold predictions.")
        if np.isfinite(oof[fold.test_indices]).any():
            raise AssertionError("An outer-fold prediction was assigned more than once.")
        oof[fold.test_indices] = predictions
        metrics = regression_metrics(y_validation, predictions)
        fold_rows.append(
            {
                "lithology": lithology,
                "model": family,
                "variant": variant,
                "outer_fold": fold.number,
                "n_train_states": len(fold.train_indices),
                "n_validation_states": len(fold.test_indices),
                "n_train_parent_materials": int(groups_train.nunique()),
                "n_validation_parent_materials": int(groups_validation.nunique()),
                **metrics,
            }
        )
        for position, prediction in zip(fold.test_indices, predictions):
            prediction_rows.append(
                {
                    "lithology": lithology,
                    "model": family,
                    "variant": variant,
                    "outer_fold": fold.number,
                    MATERIAL_STATE_ID_COLUMN: state_ids.iloc[position],
                    GROUP_COLUMN: groups.iloc[position],
                    MATERIAL_ID_COLUMN: material_ids.iloc[position],
                    "observed_thermal_conductivity_w_mk": float(y.iloc[position]),
                    "predicted_thermal_conductivity_w_mk": float(prediction),
                    "prediction_error_predicted_minus_observed_w_mk": float(
                        prediction - y.iloc[position]
                    ),
                }
            )

    if not np.isfinite(oof).all():
        raise AssertionError("Grouped CV did not generate one finite prediction per material state.")
    fold_metrics = pd.DataFrame(fold_rows)
    pooled = regression_metrics(y, oof)
    summary: dict[str, object] = {
        "lithology": lithology,
        "model": family,
        "variant": variant,
        "n_material_states": len(data),
        "n_unique_materials": int(material_ids.nunique()),
        "n_parent_materials": int(groups.nunique()),
        "outer_parent_material_folds": len(fold_plan.folds),
        "R2_OOF": pooled["R2"],
        "RMSE_OOF": pooled["RMSE"],
        "MAE_OOF": pooled["MAE"],
        "MBE_OOF": pooled["MBE"],
    }
    for metric in ("R2", "RMSE", "MAE", "MBE"):
        summary[f"{metric}_fold_mean"] = float(fold_metrics[metric].mean())
        summary[f"{metric}_fold_sd"] = float(fold_metrics[metric].std(ddof=1))
        summary[f"{metric}_fold_min"] = float(fold_metrics[metric].min())
        summary[f"{metric}_fold_max"] = float(fold_metrics[metric].max())
    return CandidateEvaluation(
        summary=summary,
        fold_metrics=fold_metrics,
        oof_predictions=pd.DataFrame(prediction_rows),
        tuning_records=tuple(tuning_records),
    )


def fit_final_candidate(
    material_states: pd.DataFrame,
    family: str,
    variant: str,
    settings: dict[str, Any],
    tuning_config: dict[str, Any],
    tuning_cache_dir: str | Path | None = None,
    tune_missing: bool = True,
):
    """Fit one final candidate to all available states of one lithology."""
    family = family.upper()
    variant = variant.upper()
    data = material_states.reset_index(drop=True)
    lithologies = data["lithology"].astype(str).unique()
    if len(lithologies) != 1:
        raise ValueError("Final fitting requires exactly one lithological group.")
    lithology = str(lithologies[0])
    X = data.loc[:, list(FEATURES)]
    y = data[TARGET]
    groups = data[GROUP_COLUMN].astype(str)
    tuned_parameters = None
    tuning_payload = None
    if variant == "TUNED":
        cache_file = None
        if tuning_cache_dir is not None:
            cache_file = Path(tuning_cache_dir) / f"{lithology}_{family}_final.json"
        tuned_parameters, _, tuning_payload = _read_or_tune_parameters(
            cache_file=cache_file,
            tune_missing=tune_missing,
            family=family,
            lithology=lithology,
            scope="final_all_material_states",
            X_train=X,
            y_train=y,
            groups_train=groups,
            search_space=tuning_config[family],
            inner_folds=int(tuning_config["inner_cross_validation_folds"]),
            random_search_iterations=int(tuning_config["random_search_iterations"]),
        )
    model = build_model(family, variant, settings, tuned_parameters)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model.fit(X, y)
    return model, tuning_payload
