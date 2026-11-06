from pathlib import Path

from lithology_thermal_rsci.constants import (
    FEATURES,
    LITHOLOGIES,
    MATERIAL_ID_COLUMN,
    MATERIAL_STATE_ID_COLUMN,
    MODEL_FAMILIES,
    MODEL_VARIANTS,
    PARENT_MATERIAL_ID_COLUMN,
    TARGET,
)


ROOT = Path(__file__).resolve().parents[1]


def test_public_vocabulary():
    assert MODEL_FAMILIES == ("SVR", "GAM", "RF", "XGB")
    assert LITHOLOGIES == ("sand", "silt", "clayey_soil", "clay")
    assert MODEL_VARIANTS == ("BASE", "SMOOTH", "INTERMEDIATE", "TUNED")
    assert FEATURES == ("water_content_pct", "bulk_density_mg_m3")
    assert TARGET == "thermal_conductivity_w_mk"
    assert MATERIAL_ID_COLUMN == "material_id"
    assert MATERIAL_STATE_ID_COLUMN == "material_state_id"
    assert PARENT_MATERIAL_ID_COLUMN == "parent_material_id"


def test_repository_contains_no_legacy_model_or_lithology_names():
    forbidden = (
        "GP" + "R",
        "Physical" + " Consistency Index",
        "P" + "CI_0_",
        "P" + "CI-based",
    )
    suffixes = {".py", ".json", ".md", ".csv", ".toml", ".txt", ".cff"}
    excluded = {"MANIFEST.sha256"}
    for path in ROOT.rglob("*"):
        relative = path.relative_to(ROOT)
        if any(part.startswith(".") for part in relative.parts):
            continue
        if not path.is_file() or path.suffix.lower() not in suffixes or path.name in excluded:
            continue
        content = path.read_text(encoding="utf-8", errors="ignore")
        for term in forbidden:
            assert term not in content, f"Forbidden legacy term {term!r} found in {relative}"


def test_public_text_contains_no_internal_working_labels():
    forbidden = (
        "R" + "3",
        "A" + "01",
        "A" + "06",
        "A" + "11",
        "A" + "12",
        "re" + "run",
        "provision" + "al",
        "Chat" + "GPT",
    )
    suffixes = {".py", ".json", ".md", ".csv", ".toml", ".txt", ".cff"}
    for path in ROOT.rglob("*"):
        relative = path.relative_to(ROOT)
        if any(part.startswith(".") for part in relative.parts):
            continue
        if not path.is_file() or path.suffix.lower() not in suffixes:
            continue
        content = path.read_text(encoding="utf-8", errors="ignore").lower()
        for term in forbidden:
            assert term.lower() not in content, (
                f"Internal working label {term!r} found in {relative}"
            )
