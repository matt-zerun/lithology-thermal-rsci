import numpy as np

from lithology_thermal_rsci.model_evaluation import regression_metrics


def test_mbe_sign_is_positive_for_overprediction():
    metrics = regression_metrics(
        np.array([1.0, 2.0, 3.0]),
        np.array([1.2, 2.1, 3.3]),
    )
    assert np.isclose(metrics["MBE"], 0.2)


def test_mbe_sign_is_negative_for_underprediction():
    metrics = regression_metrics(
        np.array([1.0, 2.0, 3.0]),
        np.array([0.8, 1.9, 2.7]),
    )
    assert np.isclose(metrics["MBE"], -0.2)
