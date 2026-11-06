import numpy as np
import pandas as pd
import pytest

from lithology_thermal_rsci.state_aggregation import aggregate_material_states


def _observations():
    return pd.DataFrame(
        [
            {
                "observation_id": "obs-1",
                "material_id": "sample-a",
                "parent_material_id": "material-a",
                "lithology": "sand",
                "water_content_pct": 5.0,
                "bulk_density_mg_m3": 1.7,
                "thermal_conductivity_w_mk": 1.0,
                "source": "laboratory",
                "data_origin": "experimental",
            },
            {
                "observation_id": "obs-2",
                "material_id": "sample-a",
                "parent_material_id": "material-a",
                "lithology": "sand",
                "water_content_pct": 5.0,
                "bulk_density_mg_m3": 1.7,
                "thermal_conductivity_w_mk": 1.2,
                "source": "laboratory",
                "data_origin": "experimental",
            },
            {
                "observation_id": "obs-3",
                "material_id": "sample-a",
                "parent_material_id": "material-a",
                "lithology": "sand",
                "water_content_pct": 8.0,
                "bulk_density_mg_m3": 1.75,
                "thermal_conductivity_w_mk": 1.4,
                "source": "laboratory",
                "data_origin": "experimental",
            },
        ]
    )


def test_replicates_are_aggregated_to_unique_material_states():
    states, report = aggregate_material_states(_observations())
    assert len(states) == 2
    assert report.n_observations == 3
    assert report.n_material_states == 2
    assert report.n_unique_materials == 1
    assert report.n_parent_materials == 1
    first = states.loc[states["measurement_count"] == 2].iloc[0]
    assert np.isclose(first["thermal_conductivity_w_mk"], 1.1)
    assert np.isclose(first["thermal_conductivity_sd_w_mk"], np.sqrt(0.02))


def test_sample_identifier_cannot_cross_lithologies():
    observations = _observations()
    observations.loc[2, "lithology"] = "clay"
    with pytest.raises(ValueError, match="material_id must map to one lithology"):
        aggregate_material_states(observations)


def test_sample_identifier_cannot_cross_material_groups():
    observations = _observations()
    observations.loc[2, "parent_material_id"] = "material-b"
    with pytest.raises(ValueError, match="material_id must map to one parent_material_id"):
        aggregate_material_states(observations)
