"""Checks remaining valid when archived reference tables are excluded."""
from pathlib import Path
import subprocess
import sys

from lithology_thermal_rsci.config import load_json
from lithology_thermal_rsci.constants import LITHOLOGIES
from lithology_thermal_rsci.data_validation import read_table, validate_and_prepare
from lithology_thermal_rsci.state_aggregation import aggregate_material_states

ROOT = Path(__file__).resolve().parents[1]


def test_grouped_validation_and_rsci_configuration_are_canonical():
    tuning = load_json('config/tuning_search_spaces.json')
    assert tuning['outer_cross_validation_folds'] == 5
    assert tuning['inner_cross_validation_folds'] == 3
    assert tuning['tuning_criterion'] == 'RMSE'
    rsci = load_json('config/rsci_definition.json')
    assert rsci['weights'] == {
        'bounds_score': 0.20, 'smoothness_score': 0.25,
        'extrema_score': 0.20, 'gradient_stability_score': 0.20,
        'fragmentation_score': 0.15,
    }
    assert rsci['output_scale'] == [0, 100]


def test_synthetic_data_exercises_measurement_state_sample_group_hierarchy():
    observations, _ = validate_and_prepare(read_table(ROOT / 'data/synthetic_example.csv'))
    states, report = aggregate_material_states(observations)
    assert len(observations) == 256
    assert len(states) == 192
    assert states['material_id'].nunique() == 96
    assert states['parent_material_id'].nunique() == 48
    assert report.measurement_count_distribution == {1: 128, 2: 64}
    groups = states.groupby('lithology')['parent_material_id'].nunique()
    assert groups.reindex(LITHOLOGIES).to_dict() == {lit: 12 for lit in LITHOLOGIES}


def test_public_code_only_boundary_validator_passes():
    result = subprocess.run([sys.executable, 'scripts/14_verify_release_boundary.py'],
                            cwd=ROOT, check=False, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr


def test_archival_results_are_not_bundled():
    assert not (ROOT / 'reference_outputs').exists()
    assert not (ROOT / 'src/lithology_thermal_rsci/publication_figures.py').exists()
