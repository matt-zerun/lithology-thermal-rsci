from pathlib import Path

import pandas as pd

from lithology_thermal_rsci.pipeline import run_pipeline


def test_demo_pipeline_with_all_four_families(tmp_path):
    outputs = run_pipeline(
        "data/synthetic_example.csv",
        tmp_path,
        families=("SVR", "GAM", "RF", "XGB"),
        variants=("BASE",),
        grid_size=20,
    )
    for path in outputs.values():
        assert Path(path).exists()
    prepared = pd.read_csv(outputs["prepared_observations"])
    states = pd.read_csv(outputs["material_states"])
    accuracy = pd.read_csv(outputs["accuracy"])
    fold_metrics = pd.read_csv(outputs["fold_metrics"])
    oof = pd.read_csv(outputs["oof_predictions"])
    fold_audit = pd.read_csv(outputs["fold_audit"])
    assignments = pd.read_csv(outputs["fold_assignments"])
    rsci = pd.read_csv(outputs["rsci"])
    assert len(prepared) == 256
    assert len(states) == 192
    assert len(accuracy) == 16
    assert len(fold_metrics) == 80
    assert len(rsci) == 16
    assert set(accuracy["model"]) == {"SVR", "GAM", "RF", "XGB"}
    assert {"R2_OOF", "RMSE_OOF", "MAE_OOF", "MBE_OOF"} <= set(accuracy.columns)
    assert "prediction_error_predicted_minus_observed_w_mk" in oof.columns
    assert set(rsci["lithology"]) == {"sand", "silt", "clayey_soil", "clay"}
    assert (fold_audit["n_overlapping_parent_materials"] == 0).all()
    assert assignments["material_state_id"].is_unique
    assert oof.groupby(["lithology", "model", "variant"])["material_state_id"].nunique().sum() == len(oof)
    profiles = list(Path(outputs["response_profiles"]).glob("*.csv"))
    assert len(profiles) == 32
