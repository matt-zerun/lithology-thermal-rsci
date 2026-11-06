from pathlib import Path

import yaml

from lithology_thermal_rsci.cli import run_from_config


def test_configuration_driven_entry_point(tmp_path):
    config = {
        "input": {"path": "data/synthetic_example.csv"},
        "output": {"directory": tmp_path.as_posix()},
        "validation": {
            "min_records_per_lithology": 10,
            "density_identity_abs_tolerance_mg_m3": 0.02,
            "density_identity_rel_tolerance": 0.02,
        },
        "analysis": {
            "families": ["SVR", "GAM", "RF", "XGB"],
            "variants": ["BASE"],
            "include_tuned": False,
            "tune_missing": True,
            "grid_size": 12,
        },
    }
    config_path = tmp_path / "run.yml"
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
    outputs = run_from_config(config_path)
    assert outputs["validation"].is_file()
    assert outputs["material_states"].is_file()
    assert outputs["review"].is_file()
    assert len(list(Path(outputs["response_surfaces"]).glob("*.csv"))) == 16
