import joblib
import numpy as np
import pandas as pd

from lithology_thermal_rsci.config import load_json
from lithology_thermal_rsci.model_factory import build_model


def _example_xy():
    water = np.linspace(1.0, 25.0, 48)
    density = np.linspace(1.2, 2.2, 48)
    X = pd.DataFrame({"water_content_pct": water, "bulk_density_mg_m3": density})
    y = pd.Series(0.4 + 0.03 * water + 0.8 * density)
    return X, y


def test_all_model_families_build_fit_and_predict(tmp_path):
    settings = load_json("config/model_variants.json")["settings"]
    X, y = _example_xy()
    for family in ("SVR", "GAM", "RF", "XGB"):
        model = build_model(family, "BASE", settings)
        model.fit(X, y)
        prediction = np.asarray(model.predict(X.iloc[:5]), dtype=float)
        assert prediction.shape == (5,)
        assert np.isfinite(prediction).all()
        path = tmp_path / f"{family}.joblib"
        joblib.dump(model, path)
        restored = joblib.load(path)
        restored_prediction = np.asarray(restored.predict(X.iloc[:5]), dtype=float)
        assert np.allclose(prediction, restored_prediction)


def test_gam_controlled_variants_build():
    settings = load_json("config/model_variants.json")["settings"]
    X, y = _example_xy()
    for variant in ("BASE", "SMOOTH", "INTERMEDIATE"):
        model = build_model("GAM", variant, settings)
        model.fit(X, y)
        assert np.isfinite(model.predict(X.iloc[:3])).all()
