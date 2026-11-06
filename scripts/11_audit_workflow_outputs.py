from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from lithology_thermal_rsci.model_evaluation import regression_metrics


KEYS = ["lithology", "model", "variant"]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit completeness and internal consistency of a workflow output directory."
    )
    parser.add_argument("output_dir")
    parser.add_argument("--report")
    arguments = parser.parse_args()
    root = Path(arguments.output_dir)
    if not root.is_dir():
        raise FileNotFoundError(root)

    summary = pd.read_csv(root / "grouped_cv_summary.csv")
    folds = pd.read_csv(root / "grouped_cv_fold_metrics.csv")
    oof = pd.read_csv(root / "oof_predictions.csv")
    fold_audit = pd.read_csv(root / "outer_fold_audit.csv")
    assignments = pd.read_csv(root / "outer_fold_assignments.csv")
    final_models = pd.read_csv(root / "final_model_manifest.csv")
    raw_rsci = pd.read_csv(root / "rsci_raw_components.csv")
    rsci = pd.read_csv(root / "rsci_scores.csv")
    review = pd.read_csv(root / "model_review_summary.csv")

    tables_with_candidate_keys = {
        "summary": summary,
        "final_models": final_models,
        "raw_rsci": raw_rsci,
        "rsci": rsci,
        "review": review,
    }
    expected_candidates = set(map(tuple, summary[KEYS].itertuples(index=False, name=None)))
    if len(expected_candidates) != len(summary):
        raise AssertionError("Grouped-CV summary contains duplicate candidates.")
    for name, table in tables_with_candidate_keys.items():
        keys = set(map(tuple, table[KEYS].itertuples(index=False, name=None)))
        if keys != expected_candidates:
            raise AssertionError(f"Candidate keys in {name} do not match grouped-CV summary.")

    if assignments["material_state_id"].duplicated().any():
        raise AssertionError("Outer-fold assignments contain duplicate material_state_id values.")
    if (fold_audit["n_overlapping_parent_materials"] != 0).any():
        raise AssertionError(
            "At least one outer fold contains overlapping parent_material_id values."
        )
    assignment_lookup = assignments.set_index(["lithology", "material_state_id"])["outer_fold"]
    candidate_state_duplicates = oof.duplicated([*KEYS, "material_state_id"])
    if candidate_state_duplicates.any():
        raise AssertionError("OOF predictions contain duplicate candidate-state pairs.")
    expected_oof_rows = sum(
        len(group) * int((summary["lithology"] == lithology).sum())
        for lithology, group in assignments.groupby("lithology")
    )
    if len(oof) != expected_oof_rows:
        raise AssertionError(
            f"Unexpected OOF row count: {len(oof)}; expected {expected_oof_rows}."
        )
    joined_fold = oof.apply(
        lambda row: assignment_lookup.loc[(row["lithology"], row["material_state_id"])],
        axis=1,
    )
    if not np.array_equal(joined_fold.to_numpy(), oof["outer_fold"].to_numpy()):
        raise AssertionError("OOF prediction fold does not match the fold assignment table.")
    prediction_error_identity = np.abs(
        oof["predicted_thermal_conductivity_w_mk"]
        - oof["observed_thermal_conductivity_w_mk"]
        - oof["prediction_error_predicted_minus_observed_w_mk"]
    )
    if float(prediction_error_identity.max()) > 1e-12:
        raise AssertionError("OOF prediction-error identity check failed.")

    for candidate, group in oof.groupby(KEYS, sort=False):
        row = summary.loc[
            (summary["lithology"] == candidate[0])
            & (summary["model"] == candidate[1])
            & (summary["variant"] == candidate[2])
        ].iloc[0]
        metrics = regression_metrics(group["observed_thermal_conductivity_w_mk"], group["predicted_thermal_conductivity_w_mk"])
        for metric, value in metrics.items():
            if not np.isclose(row[f"{metric}_OOF"], value, rtol=0, atol=1e-12):
                raise AssertionError(f"OOF {metric} mismatch for candidate {candidate}.")

    if not np.isfinite(summary.select_dtypes(include="number").to_numpy()).all():
        raise AssertionError("Grouped-CV summary contains non-finite numerical values.")
    if not np.isfinite(folds.select_dtypes(include="number").to_numpy()).all():
        raise AssertionError("Fold metrics contain non-finite numerical values.")
    if not np.isfinite(rsci["RSCI_0_100"]).all():
        raise AssertionError("RSCI table contains non-finite scores.")
    if not rsci["RSCI_0_100"].between(0, 100).all():
        raise AssertionError("RSCI scores fall outside the declared 0–100 interval.")

    model_files = list((root / "models").glob("*.joblib"))
    surface_files = list((root / "response_surfaces").glob("*.csv"))
    profile_files = list((root / "response_profiles").glob("*.csv"))
    expected_surface_names = {
        f"{row.lithology}_{row.model}_{row.variant}.csv"
        for row in summary[KEYS].itertuples(index=False)
    }
    expected_profile_names = {
        f"{row.lithology}_{row.model}_{row.variant}_lambda_by_{direction}.csv"
        for row in summary[KEYS].itertuples(index=False)
        for direction in ("water", "density")
    }
    if len(model_files) != len(summary):
        raise AssertionError("Final model file count is incomplete.")
    if {path.name for path in surface_files} != expected_surface_names:
        raise AssertionError("Response-surface file set is incomplete or unexpected.")
    if {path.name for path in profile_files} != expected_profile_names:
        raise AssertionError("Response-profile file set is incomplete or unexpected.")

    tuned_candidates = summary.loc[summary["variant"] == "TUNED", KEYS]
    tuning_files = list((root / "tuned_parameters").glob("*.json"))
    expected_tuning_files = len(tuned_candidates) * (int(summary["outer_parent_material_folds"].max()) + 1)
    if len(tuning_files) != expected_tuning_files:
        raise AssertionError(
            f"Unexpected nested-tuning file count: {len(tuning_files)}; "
            f"expected {expected_tuning_files}."
        )

    report = {
        "status": "passed",
        "n_candidates": len(summary),
        "n_outer_fold_metric_rows": len(folds),
        "n_material_states": len(assignments),
        "n_oof_predictions": len(oof),
        "n_final_models": len(model_files),
        "n_response_surfaces": len(surface_files),
        "n_response_profiles": len(profile_files),
        "n_nested_tuning_files": len(tuning_files),
        "maximum_prediction_error_identity_error": float(
            prediction_error_identity.max()
        ),
        "parent_material_overlap_across_outer_folds": int(
            fold_audit["n_overlapping_parent_materials"].sum()
        ),
    }
    target = (
        Path(arguments.report)
        if arguments.report
        else root / "workflow_output_audit.json"
    )
    target.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(target)


if __name__ == "__main__":
    main()
