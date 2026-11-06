import numpy as np

from lithology_thermal_rsci.rsci import raw_components


def test_smooth_plane_has_finite_components():
    water = np.linspace(0, 20, 20)
    density = np.linspace(1.2, 2.2, 20)
    W, RHO = np.meshgrid(water, density)
    values = 0.5 + 0.03 * W + 0.8 * RHO
    result = raw_components(values, water, density)
    assert result["bounds_score"] == 1.0
    assert result["smoothness_raw"] >= 0
    assert result["gradient_stability_raw"] >= 0
    assert result["fragmentation_raw"] >= 0
