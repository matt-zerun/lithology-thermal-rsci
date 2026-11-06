from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import pandas as pd

from lithology_thermal_rsci.config import load_json
from lithology_thermal_rsci.constants import LITHOLOGIES, MODEL_FAMILIES, MODEL_VARIANTS
from lithology_thermal_rsci.data_validation import read_table, validate_and_prepare
from lithology_thermal_rsci.grouped_evaluation import (
    build_grouped_fold_plan,
    evaluate_candidate_grouped_cv,
    fit_final_candidate,
)
from lithology_thermal_rsci.state_aggregation import aggregate_material_states


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate controlled candidates by material-series-grouped CV and fit final "
            "models to all material states."
        )
    )
    parser.add_argument("input")
    parser.add_argument("--output", default="workflow_outputs/models")
    parser.add_argument(
        "--summary-output",
        default="workflow_outputs/grouped_cv_summary.csv",
    )
    parser.add_argument(
        "--fold-output",
        default="workflow_outputs/grouped_cv_fold_metrics.csv",
    )
    parser.add_argument(
        "--oof-output",
        default="workflow_outputs/oof_predictions.csv",
    )
    parser.add_argument(
        "--manifest-output",
        default="workflow_outputs/final_model_manifest.csv",
    )
    parser.add_argument(
        "--fold-audit-output",
        default="workflow_outputs/outer_fold_audit.csv",
    )
    parser.add_argument(
        "--fold-assignment-output",
        default="workflow_outputs/outer_fold_assignments.csv",
    )
    parser.add_argument("--tuned-parameters", default="workflow_outputs/tuned_parameters")
    parser.add_argument("--models", nargs="+", default=list(MODEL_FAMILIES))
    parser.add_argument("--variants", nargs="+", default=list(MODEL_VARIANTS))
    parser.add_argument(
        "--reuse-only",
        action="store_true",
        help="Require existing nested-tuning JSON files for TUNED candidates.",
    )
    arguments = parser.parse_args()

    observations, _ = validate_and_prepare(read_table(arguments.input))
    states, _ = aggregate_material_states(observations)
    tuning_config = load_json("config/tuning_search_spaces.json")
    settings = load_json("config/model_variants.json")["settings"]
    model_dir = Path(arguments.output)
    tuned_dir = Path(arguments.tuned_parameters)
    model_dir.mkdir(parents=True, exist_ok=True)
    tuned_dir.mkdir(parents=True, exist_ok=True)
    families = [str(name).upper() for name in arguments.models]
    variants = [str(name).upper() for name in arguments.variants]
    unsupported_families = sorted(set(families) - set(MODEL_FAMILIES))
    unsupported_variants = sorted(set(variants) - set(MODEL_VARIANTS))
    if unsupported_families:
        raise ValueError(f"Unsupported model families: {unsupported_families}")
    if unsupported_variants:
        raise ValueError(f"Unsupported model variants: {unsupported_variants}")

    summaries = []
    fold_tables = []
    oof_tables = []
    manifest_rows = []
    fold_audit_tables = []
    fold_assignment_tables = []
    for lithology in LITHOLOGIES:
        subset = states.loc[states["lithology"] == lithology].reset_index(drop=True)
        plan = build_grouped_fold_plan(
            subset,
            n_splits=int(tuning_config["outer_cross_validation_folds"]),
        )
        fold_audit_tables.append(plan.audit)
        fold_assignment_tables.append(plan.assignments)
        for family in families:
            for variant in variants:
                result = evaluate_candidate_grouped_cv(
                    subset,
                    plan,
                    family,
                    variant,
                    settings,
                    tuning_config,
                    tuning_cache_dir=tuned_dir,
                    tune_missing=not arguments.reuse_only,
                )
                summaries.append(result.summary)
                fold_tables.append(result.fold_metrics)
                oof_tables.append(result.oof_predictions)
                model, final_tuning = fit_final_candidate(
                    subset,
                    family,
                    variant,
                    settings,
                    tuning_config,
                    tuning_cache_dir=tuned_dir,
                    tune_missing=not arguments.reuse_only,
                )
                parameters = (
                    final_tuning["parameters"]
                    if final_tuning is not None
                    else settings[family][variant]
                )
                target = model_dir / f"{lithology}_{family}_{variant}.joblib"
                joblib.dump(model, target)
                manifest_rows.append(
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
                print(target)

    targets = {
        "summary": Path(arguments.summary_output),
        "folds": Path(arguments.fold_output),
        "oof": Path(arguments.oof_output),
        "manifest": Path(arguments.manifest_output),
        "fold_audit": Path(arguments.fold_audit_output),
        "fold_assignments": Path(arguments.fold_assignment_output),
    }
    for target in targets.values():
        target.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(summaries).to_csv(targets["summary"], index=False)
    pd.concat(fold_tables, ignore_index=True).to_csv(targets["folds"], index=False)
    pd.concat(oof_tables, ignore_index=True).to_csv(targets["oof"], index=False)
    pd.DataFrame(manifest_rows).to_csv(targets["manifest"], index=False)
    pd.concat(fold_audit_tables, ignore_index=True).to_csv(
        targets["fold_audit"], index=False
    )
    pd.concat(fold_assignment_tables, ignore_index=True).to_csv(
        targets["fold_assignments"], index=False
    )
    for target in targets.values():
        print(target)


if __name__ == "__main__":
    main()
