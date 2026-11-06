from __future__ import annotations

import argparse
from pathlib import Path

import joblib
import pandas as pd

from lithology_thermal_rsci.config import load_json
from lithology_thermal_rsci.constants import LITHOLOGIES, MODEL_FAMILIES
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
            "Evaluate TUNED candidates by nested material-series-grouped CV and fit their "
            "final versions to all material states."
        )
    )
    parser.add_argument("input")
    parser.add_argument("--output", default="workflow_outputs/tuned_parameters")
    parser.add_argument("--models-output", default="workflow_outputs/models")
    parser.add_argument(
        "--summary-output",
        default="workflow_outputs/tuned_grouped_cv_summary.csv",
    )
    parser.add_argument(
        "--fold-output",
        default="workflow_outputs/tuned_grouped_cv_fold_metrics.csv",
    )
    parser.add_argument(
        "--oof-output",
        default="workflow_outputs/tuned_oof_predictions.csv",
    )
    parser.add_argument("--models", nargs="+", default=list(MODEL_FAMILIES))
    parser.add_argument(
        "--reuse-only",
        action="store_true",
        help="Require existing nested-tuning JSON files instead of calculating missing files.",
    )
    arguments = parser.parse_args()

    observations, _ = validate_and_prepare(read_table(arguments.input))
    states, _ = aggregate_material_states(observations)
    tuning_config = load_json("config/tuning_search_spaces.json")
    settings = load_json("config/model_variants.json")["settings"]
    tuning_dir = Path(arguments.output)
    model_dir = Path(arguments.models_output)
    tuning_dir.mkdir(parents=True, exist_ok=True)
    model_dir.mkdir(parents=True, exist_ok=True)
    requested = [str(family).upper() for family in arguments.models]
    unsupported = sorted(set(requested) - set(MODEL_FAMILIES))
    if unsupported:
        raise ValueError(f"Unsupported model families: {unsupported}")

    summaries = []
    fold_tables = []
    oof_tables = []
    for lithology in LITHOLOGIES:
        subset = states.loc[states["lithology"] == lithology].reset_index(drop=True)
        plan = build_grouped_fold_plan(
            subset,
            n_splits=int(tuning_config["outer_cross_validation_folds"]),
        )
        for family in requested:
            result = evaluate_candidate_grouped_cv(
                subset,
                plan,
                family,
                "TUNED",
                settings,
                tuning_config,
                tuning_cache_dir=tuning_dir,
                tune_missing=not arguments.reuse_only,
            )
            summaries.append(result.summary)
            fold_tables.append(result.fold_metrics)
            oof_tables.append(result.oof_predictions)
            model, _ = fit_final_candidate(
                subset,
                family,
                "TUNED",
                settings,
                tuning_config,
                tuning_cache_dir=tuning_dir,
                tune_missing=not arguments.reuse_only,
            )
            target = model_dir / f"{lithology}_{family}_TUNED.joblib"
            joblib.dump(model, target)
            print(target)

    targets = {
        "summary": Path(arguments.summary_output),
        "folds": Path(arguments.fold_output),
        "oof": Path(arguments.oof_output),
    }
    for target in targets.values():
        target.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(summaries).to_csv(targets["summary"], index=False)
    pd.concat(fold_tables, ignore_index=True).to_csv(targets["folds"], index=False)
    pd.concat(oof_tables, ignore_index=True).to_csv(targets["oof"], index=False)
    for target in targets.values():
        print(target)


if __name__ == "__main__":
    main()
