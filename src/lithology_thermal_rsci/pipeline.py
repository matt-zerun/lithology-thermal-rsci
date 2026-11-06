from __future__ import annotations

import importlib.metadata
import json
from dataclasses import asdict
from pathlib import Path
from typing import Iterable

import joblib
import pandas as pd

from .config import load_json
from .constants import FEATURES, LITHOLOGIES, MODEL_FAMILIES, MODEL_VARIANTS
from .data_validation import read_table, validate_and_prepare
from .grouped_evaluation import (
    NESTED_CV_PROTOCOL,
    build_grouped_fold_plan,
    evaluate_candidate_grouped_cv,
    fit_final_candidate,
)
from .pareto import mark_pareto_front
from .predictor_correlation import predictor_correlation_table
from .response_profiles import extract_profiles
from .response_surfaces import generate_response_surface
from .rsci import RSCISettings, normalise_and_score, raw_components
from .state_aggregation import aggregate_material_states


def _software_versions() -> dict[str, str]:
    packages = [
        "lithology-thermal-rsci",
        "numpy",
        "pandas",
        "scipy",
        "scikit-learn",
        "xgboost",
        "pygam",
        "matplotlib",
        "pillow",
        "joblib",
        "openpyxl",
    ]
    versions: dict[str, str] = {}
    for package in packages:
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            if package == "lithology-thermal-rsci":
                from . import __version__

                versions[package] = __version__
            elif package == "pygam":
                try:
                    import pygam

                    versions[package] = getattr(pygam, "__version__", "source checkout")
                except ImportError:
                    versions[package] = "not installed"
            else:
                versions[package] = "not installed"
    return versions


def run_pipeline(
    input_path: str | Path,
    output_dir: str | Path,
    families: Iterable[str] = MODEL_FAMILIES,
    include_tuned: bool = False,
    tune_missing: bool = True,
    variants: Iterable[str] | None = None,
    grid_size: int | None = None,
    validation_options: dict[str, object] | None = None,
) -> dict[str, Path]:
    """Run the end-to-end workflow on a validated dataset."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    observations, validation_report = validate_and_prepare(
        read_table(input_path), **(validation_options or {})
    )
    data, state_report = aggregate_material_states(observations)
    correlations = predictor_correlation_table(observations, data)
    variants_config = load_json("config/model_variants.json")
    tuning_config = load_json("config/tuning_search_spaces.json")
    rsci_config = load_json("config/rsci_definition.json")
    rsci_settings = RSCISettings.from_mapping(rsci_config)
    rsci_settings.validate()
    settings = variants_config["settings"]

    requested_families = tuple(str(family).upper() for family in families)
    unsupported = sorted(set(requested_families) - set(MODEL_FAMILIES))
    if unsupported:
        raise ValueError(f"Unsupported requested model families: {unsupported}")
    if not requested_families:
        raise ValueError("At least one model family must be requested.")

    requested_variants = ["BASE", "SMOOTH", "INTERMEDIATE"] if variants is None else [str(item).upper() for item in variants]
    if include_tuned and "TUNED" not in requested_variants:
        requested_variants.append("TUNED")
    unsupported_variants = sorted(set(requested_variants) - set(MODEL_VARIANTS))
    if unsupported_variants:
        raise ValueError(f"Unsupported requested model variants: {unsupported_variants}")
    if not requested_variants:
        raise ValueError("At least one model variant must be requested.")
    resolved_grid_size = int(variants_config["grid_size"] if grid_size is None else grid_size)

    accuracy_rows: list[dict[str, object]] = []
    fold_metric_tables: list[pd.DataFrame] = []
    oof_prediction_tables: list[pd.DataFrame] = []
    fold_audit_tables: list[pd.DataFrame] = []
    fold_assignment_tables: list[pd.DataFrame] = []
    final_model_rows: list[dict[str, object]] = []
    raw_rows: list[dict[str, object]] = []
    model_dir = output_dir / "models"
    surface_dir = output_dir / "response_surfaces"
    profile_dir = output_dir / "response_profiles"
    tuned_dir = output_dir / "tuned_parameters"
    model_dir.mkdir(exist_ok=True)
    surface_dir.mkdir(exist_ok=True)
    profile_dir.mkdir(exist_ok=True)
    tuned_dir.mkdir(exist_ok=True)

    for lithology in LITHOLOGIES:
        subset = data.loc[data["lithology"] == lithology].reset_index(drop=True)
        fold_plan = build_grouped_fold_plan(
            subset,
            n_splits=int(tuning_config["outer_cross_validation_folds"]),
        )
        fold_audit_tables.append(fold_plan.audit)
        fold_assignment_tables.append(fold_plan.assignments)
        observed_X = subset.loc[:, list(FEATURES)]
        fixed_density_levels = observed_X["bulk_density_mg_m3"].quantile(
            [0.25, 0.50, 0.75]
        ).tolist()
        fixed_water_levels = observed_X["water_content_pct"].quantile(
            [0.25, 0.50, 0.75]
        ).tolist()
        for family in requested_families:
            for variant in requested_variants:
                evaluation = evaluate_candidate_grouped_cv(
                    subset,
                    fold_plan,
                    family,
                    variant,
                    settings,
                    tuning_config,
                    tuning_cache_dir=tuned_dir,
                    tune_missing=tune_missing,
                )
                accuracy_rows.append(evaluation.summary)
                fold_metric_tables.append(evaluation.fold_metrics)
                oof_prediction_tables.append(evaluation.oof_predictions)
                model, final_tuning = fit_final_candidate(
                    subset,
                    family,
                    variant,
                    settings,
                    tuning_config,
                    tuning_cache_dir=tuned_dir,
                    tune_missing=tune_missing,
                )
                parameters = (
                    final_tuning["parameters"]
                    if final_tuning is not None
                    else settings[family][variant]
                )
                final_model_rows.append(
                    {
                        "lithology": lithology,
                        "model": family,
                        "variant": variant,
                        "fit_scope": "all_material_states",
                        "n_material_states": len(subset),
                        "n_unique_materials": int(subset["material_id"].nunique()),
                        "n_parent_materials": int(
                            subset["parent_material_id"].nunique()
                        ),
                        "parameters_json": json.dumps(parameters, sort_keys=True),
                    }
                )
                joblib.dump(model, model_dir / f"{lithology}_{family}_{variant}.joblib")
                surface = generate_response_surface(
                    model,
                    observed_X,
                    grid_size=resolved_grid_size,
                )
                surface.table.to_csv(surface_dir / f"{lithology}_{family}_{variant}.csv", index=False)
                water_profiles, density_profiles = extract_profiles(
                    model,
                    observed_X,
                    fixed_density_levels,
                    fixed_water_levels,
                )
                water_profiles.to_csv(
                    profile_dir
                    / f"{lithology}_{family}_{variant}_lambda_by_water.csv",
                    index=False,
                )
                density_profiles.to_csv(
                    profile_dir
                    / f"{lithology}_{family}_{variant}_lambda_by_density.csv",
                    index=False,
                )
                raw_rows.append(
                    {
                        "lithology": lithology,
                        "model": family,
                        "variant": variant,
                        **raw_components(
                            surface.predicted_grid,
                            surface.water_values,
                            surface.density_values,
                            rsci_settings,
                        ),
                    }
                )

    accuracy = pd.DataFrame(accuracy_rows)
    fold_metrics = pd.concat(fold_metric_tables, ignore_index=True)
    oof_predictions = pd.concat(oof_prediction_tables, ignore_index=True)
    fold_audit = pd.concat(fold_audit_tables, ignore_index=True)
    fold_assignments = pd.concat(fold_assignment_tables, ignore_index=True)
    final_models = pd.DataFrame(final_model_rows)
    raw = pd.DataFrame(raw_rows)
    scored = normalise_and_score(raw, rsci_settings)
    results = mark_pareto_front(
        scored.merge(accuracy, on=["lithology", "model", "variant"], validate="one_to_one"),
        accuracy_column="R2_OOF",
    )

    observations_path = output_dir / "prepared_observations.csv"
    states_path = output_dir / "material_states.csv"
    accuracy_path = output_dir / "grouped_cv_summary.csv"
    fold_metrics_path = output_dir / "grouped_cv_fold_metrics.csv"
    oof_predictions_path = output_dir / "oof_predictions.csv"
    fold_audit_path = output_dir / "outer_fold_audit.csv"
    fold_assignments_path = output_dir / "outer_fold_assignments.csv"
    final_models_path = output_dir / "final_model_manifest.csv"
    raw_path = output_dir / "rsci_raw_components.csv"
    score_path = output_dir / "rsci_scores.csv"
    results_path = output_dir / "model_review_summary.csv"
    correlations_path = output_dir / "predictor_correlations.csv"
    validation_path = output_dir / "validation_report.json"
    versions_path = output_dir / "software_versions.json"
    observations.to_csv(observations_path, index=False)
    data.to_csv(states_path, index=False)
    accuracy.to_csv(accuracy_path, index=False)
    fold_metrics.to_csv(fold_metrics_path, index=False)
    oof_predictions.to_csv(oof_predictions_path, index=False)
    fold_audit.to_csv(fold_audit_path, index=False)
    fold_assignments.to_csv(fold_assignments_path, index=False)
    final_models.to_csv(final_models_path, index=False)
    raw.to_csv(raw_path, index=False)
    scored.to_csv(score_path, index=False)
    results.to_csv(results_path, index=False)
    correlations.to_csv(correlations_path, index=False)
    validation_path.write_text(
        json.dumps(
            {
                "observation_validation": asdict(validation_report),
                "material_state_aggregation": asdict(state_report),
                "analysis_unit": "unique material state",
                "state_definition": [
                    "material_id",
                    "lithology",
                    "water_content_pct",
                    "bulk_density_mg_m3",
                ],
                "target_aggregation": (
                    "arithmetic mean of thermal-conductivity measurements mapped "
                    "to the same material state"
                ),
                "evaluation_protocol": NESTED_CV_PROTOCOL,
                "outer_evaluation": (
                    f"{int(tuning_config['outer_cross_validation_folds'])}-fold "
                    "GroupKFold by parent_material_id with one held-group prediction "
                    "per material state"
                ),
                "inner_tuning": (
                    f"{int(tuning_config['inner_cross_validation_folds'])}-fold "
                    "GroupKFold by parent_material_id within each outer training subset; "
                    "hyperparameters selected by RMSE"
                ),
                "final_model_fit": "all lithology-specific material states after evaluation",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    versions_path.write_text(json.dumps(_software_versions(), indent=2), encoding="utf-8")
    return {
        "prepared_observations": observations_path,
        "material_states": states_path,
        "validation": validation_path,
        "versions": versions_path,
        "accuracy": accuracy_path,
        "fold_metrics": fold_metrics_path,
        "oof_predictions": oof_predictions_path,
        "fold_audit": fold_audit_path,
        "fold_assignments": fold_assignments_path,
        "final_models": final_models_path,
        "raw_rsci": raw_path,
        "rsci": score_path,
        "review": results_path,
        "correlations": correlations_path,
        "models": model_dir,
        "response_surfaces": surface_dir,
        "response_profiles": profile_dir,
    }
