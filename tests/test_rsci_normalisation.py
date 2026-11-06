import pandas as pd

from lithology_thermal_rsci.rsci import normalise_and_score


def test_normalisation_is_within_lithology():
    table = pd.DataFrame([
        {"lithology": "sand", "bounds_score": 1.0, "smoothness_raw": 1.0, "n_local_extrema_total": 1, "gradient_stability_raw": 1.0, "fragmentation_raw": 1.0},
        {"lithology": "sand", "bounds_score": 1.0, "smoothness_raw": 2.0, "n_local_extrema_total": 2, "gradient_stability_raw": 2.0, "fragmentation_raw": 2.0},
        {"lithology": "clay", "bounds_score": 1.0, "smoothness_raw": 100.0, "n_local_extrema_total": 10, "gradient_stability_raw": 50.0, "fragmentation_raw": 5.0},
        {"lithology": "clay", "bounds_score": 1.0, "smoothness_raw": 200.0, "n_local_extrema_total": 20, "gradient_stability_raw": 100.0, "fragmentation_raw": 10.0},
    ])
    result = normalise_and_score(table)
    assert result.groupby("lithology")["RSCI_0_100"].max().eq(100.0).all()
    assert result.groupby("lithology")["RSCI_0_100"].min().eq(20.0).all()
