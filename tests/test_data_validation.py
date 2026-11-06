import pandas as pd
import pytest

from lithology_thermal_rsci.data_validation import InputValidationError, validate_and_prepare


def _valid_rows():
    rows = []
    for lithology in ("sand", "silt", "clayey_soil", "clay"):
        for index in range(10):
            rows.append(
                {
                    "observation_id": f"{lithology}-{index}",
                    "material_id": f"{lithology}-sample-{index}",
                    "parent_material_id": f"{lithology}-material-{index // 2}",
                    "lithology": lithology,
                    "water_content_pct": 5 + index,
                    "bulk_density_mg_m3": 1.4 + index * 0.01,
                    "thermal_conductivity_w_mk": 1.0 + index * 0.05,
                    "source": "synthetic",
                    "data_origin": "demonstration",
                }
            )
    return rows


def test_validation_accepts_required_schema():
    prepared, report = validate_and_prepare(pd.DataFrame(_valid_rows()))
    assert len(prepared) == 40
    assert report.n_input_observations == 40
    assert report.n_valid_observations == 40


def test_validation_rejects_negative_water_content():
    rows = _valid_rows()
    rows[0]["water_content_pct"] = -1
    with pytest.raises(InputValidationError, match="water_content_pct"):
        validate_and_prepare(pd.DataFrame(rows))


def test_non_numeric_required_value_is_not_silently_removed():
    rows = _valid_rows()
    rows[0]["water_content_pct"] = "not-a-number"
    with pytest.raises(InputValidationError, match="non-numeric"):
        validate_and_prepare(pd.DataFrame(rows))


def test_duplicate_observation_id_is_rejected():
    rows = _valid_rows()
    rows[1]["observation_id"] = rows[0]["observation_id"]
    with pytest.raises(InputValidationError, match="Duplicate observation_id"):
        validate_and_prepare(pd.DataFrame(rows))


def test_unknown_lithology_is_rejected():
    rows = _valid_rows()
    rows[0]["lithology"] = "unknown"
    with pytest.raises(InputValidationError, match="Unknown lithology"):
        validate_and_prepare(pd.DataFrame(rows))


def test_optional_density_identity_is_checked():
    table = pd.DataFrame(_valid_rows())
    table["dry_density_mg_m3"] = (
        table["bulk_density_mg_m3"] / (1 + table["water_content_pct"] / 100)
    )
    prepared, report = validate_and_prepare(table)
    assert "dry_density_mg_m3" in prepared
    assert report.optional_columns_present == ("dry_density_mg_m3",)
    table.loc[0, "dry_density_mg_m3"] = 0.8
    with pytest.raises(InputValidationError, match="density identity"):
        validate_and_prepare(table)
