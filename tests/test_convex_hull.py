import numpy as np

from lithology_thermal_rsci.convex_hull import inside_convex_hull


def test_convex_hull_mask():
    observed = np.array([[0, 0], [1, 0], [0, 1], [1, 1]], dtype=float)
    query = np.array([[0.5, 0.5], [2.0, 2.0]], dtype=float)
    mask = inside_convex_hull(observed, query)
    assert mask.tolist() == [True, False]
