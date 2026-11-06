import numpy as np
import pandas as pd

from lithology_thermal_rsci.grouped_evaluation import (
    build_grouped_fold_plan,
    evaluate_candidate_grouped_cv,
    fit_final_candidate,
)


def _material_states(n_samples=20, states_per_sample=2):
    rng = np.random.default_rng(42)
    rows = []
    for sample_index in range(n_samples):
        for state_index in range(states_per_sample):
            water = 2 + sample_index * 0.4 + state_index * 0.1
            density = 1.25 + sample_index * 0.025 + state_index * 0.01
            rows.append(
                {
                    "material_state_id": f"state-{sample_index}-{state_index}",
                    "material_id": f"sample-{sample_index}",
                    "parent_material_id": f"material-{sample_index // 2}",
                    "lithology": "sand",
                    "water_content_pct": water,
                    "bulk_density_mg_m3": density,
                    "thermal_conductivity_w_mk": (
                        0.4 + 0.04 * water + 0.8 * density + rng.normal(0, 0.02)
                    ),
                }
            )
    return pd.DataFrame(rows)


SETTINGS = {
    "SVR": {
        "BASE": {"kernel": "rbf", "C": 1.0, "gamma": "scale", "epsilon": 0.1},
        "SMOOTH": {"kernel": "rbf", "C": 1.0, "gamma": 0.01, "epsilon": 0.1},
        "INTERMEDIATE": {"kernel": "rbf", "C": 10.0, "gamma": 0.1, "epsilon": 0.05},
    }
}


def _tuning_config():
    return {
        "outer_cross_validation_folds": 3,
        "inner_cross_validation_folds": 3,
        "random_search_iterations": 2,
        "SVR": {"C": [1.0, 10.0], "epsilon": [0.05], "gamma": ["scale"]},
    }


def test_outer_grouped_folds_cover_each_state_once_without_material_group_overlap():
    states = _material_states()
    plan = build_grouped_fold_plan(states, n_splits=5)
    assert len(plan.folds) == 5
    assert len(plan.assignments) == len(states)
    assert plan.assignments["material_state_id"].is_unique
    assert (plan.audit["n_overlapping_parent_materials"] == 0).all()
    assert (
        plan.assignments.groupby("parent_material_id")["outer_fold"]
        .nunique()
        .eq(1)
        .all()
    )


def test_fixed_candidate_generates_one_oof_prediction_per_state():
    states = _material_states()
    plan = build_grouped_fold_plan(states, n_splits=5)
    result = evaluate_candidate_grouped_cv(
        states,
        plan,
        "SVR",
        "BASE",
        SETTINGS,
        _tuning_config(),
    )
    assert len(result.fold_metrics) == 5
    assert len(result.oof_predictions) == len(states)
    assert result.oof_predictions["material_state_id"].is_unique
    assert np.isfinite(result.summary["R2_OOF"])
    assert np.isfinite(result.summary["MBE_OOF"])
    assert np.isclose(
        result.summary["MBE_OOF"],
        result.oof_predictions["prediction_error_predicted_minus_observed_w_mk"].mean(),
    )
    assert result.tuning_records == ()


def test_tuned_candidate_uses_nested_grouped_cv_and_final_full_fit(tmp_path):
    states = _material_states(n_samples=18)
    plan = build_grouped_fold_plan(states, n_splits=3)
    config = _tuning_config()
    result = evaluate_candidate_grouped_cv(
        states,
        plan,
        "SVR",
        "TUNED",
        SETTINGS,
        config,
        tuning_cache_dir=tmp_path,
    )
    assert len(result.tuning_records) == 3
    assert all(
        record["protocol"].endswith("groupkfold_rmse_v2")
        for record in result.tuning_records
    )
    assert all(record["tuning_criterion"] == "RMSE" for record in result.tuning_records)
    assert all("inner_CV_RMSE_mean" in record for record in result.tuning_records)
    model, final_tuning = fit_final_candidate(
        states,
        "SVR",
        "TUNED",
        SETTINGS,
        config,
        tuning_cache_dir=tmp_path,
    )
    prediction = model.predict(states[["water_content_pct", "bulk_density_mg_m3"]])
    assert len(prediction) == len(states)
    assert final_tuning["scope"] == "final_all_material_states"
    assert len(list(tmp_path.glob("*.json"))) == 4
