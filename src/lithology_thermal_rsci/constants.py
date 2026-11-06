from __future__ import annotations

FEATURES = ("water_content_pct", "bulk_density_mg_m3")
TARGET = "thermal_conductivity_w_mk"
OBSERVATION_ID_COLUMN = "observation_id"
MATERIAL_ID_COLUMN = "material_id"
PARENT_MATERIAL_ID_COLUMN = "parent_material_id"
# Kept as the grouped-evaluation alias for modules that operate on CV groups.
GROUP_COLUMN = PARENT_MATERIAL_ID_COLUMN
MATERIAL_STATE_ID_COLUMN = "material_state_id"
LITHOLOGY_COLUMN = "lithology"
WATER_CONTENT_COLUMN = "water_content_pct"
BULK_DENSITY_COLUMN = "bulk_density_mg_m3"
DRY_DENSITY_COLUMN = "dry_density_mg_m3"
PARTICLE_DENSITY_COLUMN = "particle_density_mg_m3"
MEASUREMENT_TEMPERATURE_COLUMN = "measurement_temperature_c"
LITHOLOGIES = ("sand", "silt", "clayey_soil", "clay")
MODEL_FAMILIES = ("SVR", "GAM", "RF", "XGB")
MODEL_VARIANTS = ("BASE", "SMOOTH", "INTERMEDIATE", "TUNED")
REQUIRED_COLUMNS = (
    OBSERVATION_ID_COLUMN,
    MATERIAL_ID_COLUMN,
    PARENT_MATERIAL_ID_COLUMN,
    LITHOLOGY_COLUMN,
    WATER_CONTENT_COLUMN,
    BULK_DENSITY_COLUMN,
    TARGET,
    "source",
    "data_origin",
)
OPTIONAL_COLUMNS = (
    DRY_DENSITY_COLUMN,
    PARTICLE_DENSITY_COLUMN,
    MEASUREMENT_TEMPERATURE_COLUMN,
)
RANDOM_STATE = 42
