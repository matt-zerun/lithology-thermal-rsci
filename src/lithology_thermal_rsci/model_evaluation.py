from __future__ import annotations

import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


def regression_metrics(y_true, y_pred) -> dict[str, float]:
    """Return regression metrics for one evaluation subset.

    MBE is defined as mean(predicted - observed), so positive values indicate
    systematic overprediction and negative values indicate underprediction.
    """
    prediction_error = np.asarray(y_pred, dtype=float) - np.asarray(y_true, dtype=float)
    return {
        "R2": float(r2_score(y_true, y_pred)),
        "RMSE": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "MAE": float(mean_absolute_error(y_true, y_pred)),
        "MBE": float(np.mean(prediction_error)),
    }
