from __future__ import annotations

import numpy as np
from scipy.spatial import Delaunay, QhullError


def inside_convex_hull(observed_points: np.ndarray, query_points: np.ndarray) -> np.ndarray:
    observed = np.asarray(observed_points, dtype=float)
    query = np.asarray(query_points, dtype=float)
    if observed.ndim != 2 or observed.shape[1] != 2:
        raise ValueError("observed_points must have shape (n, 2)")
    if query.ndim != 2 or query.shape[1] != 2:
        raise ValueError("query_points must have shape (m, 2)")
    if len(observed) < 3:
        raise ValueError("At least three observed points are required to construct a convex hull.")
    try:
        triangulation = Delaunay(observed)
    except QhullError as exc:
        raise ValueError("Observed predictor points do not define a valid two-dimensional convex hull.") from exc
    return triangulation.find_simplex(query) >= 0
