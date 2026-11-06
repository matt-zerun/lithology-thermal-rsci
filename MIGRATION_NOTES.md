# Migration from lithology-thermal-rsci 1.1.1

Version 2.0.0 is a breaking public-schema release. It preserves the validated
v1.1.1 scientific calculations and publication values.

## Entry points and architecture

| Old path / command | New path / command | Reason |
|---|---|---|
| `scripts/00_run_demo_pipeline.py` | `python run_analysis.py --config config/example_config.yml` | common configuration-driven entry point |
| `scripts/10_run_analysis_pipeline.py INPUT OUTPUT ...` | retained for advanced/authorised runs | stable explicit CLI remains useful |
| no blank user template | `data/templates/rsci_canonical_observations_template.csv` | prepare input without reading source code |
| `data/input_schema.csv` with four metadata columns | expanded dictionary plus `DATA_SCHEMA.md` | units, types, examples, requiredness, and QC are explicit |
| `docs/manuscript_mapping.md` | `docs/reference_output_mapping.md` and `METHODS_MAPPING.md` | separate content-based workflow and archived-output documentation |

Scripts 01–09 remain supported stage-level tools. Scripts 11–16 remain audit,
reference-output, figure, and packaging tools. They are not unused development
residue.

## Canonical identifier names

| Version 1.1.1 | Version 2.0 | Meaning |
|---|---|---|
| `sample_id` | `material_id` | physical sample or material member |
| `state_id` | `material_state_id` | aggregated achieved state |
| `material_group_id` | `parent_material_id` | group withheld intact in outer and inner CV |
| `n_replicates` | `measurement_count` | contributing conductivity measurements; not necessarily technical replicates |

## Canonical physical names

| Version 1.1.1 | Version 2.0 |
|---|---|
| `lithology_group` | `lithology` |
| `water_content` | `water_content_pct` |
| `bulk_density` | `bulk_density_mg_m3` |
| `thermal_conductivity` | `thermal_conductivity_w_mk` |
| `predicted_lambda` | `predicted_thermal_conductivity_w_mk` |
| `measurement_temperature` | `measurement_temperature_c` |
| `thermal_conductivity_sd/min/max` | `thermal_conductivity_sd/min/max_w_mk` |

Profile filenames retain the familiar mathematical `lambda_by_water` and
`lambda_by_density` wording for backward compatibility, while every
CSV column uses the canonical explicit vocabulary.

## Public reference outputs

Identifier-free aggregate tables, selected surface/profile tables, and source
data now use canonical column headers. Their row order and numeric cells are
unchanged. Frozen raster figures are retained unchanged because the visualised
scientific values and archived reference numbering did not change.

## Removed or development-only material

No scientific stage script was removed. The original `MANIFEST.sha256` is
regenerated for the final release. Test caches, compiled files, local
environments, build artefacts, and generated workflow directories are excluded
from the public archive.

## Frozen scientific content

Unchanged: observation-to-state grouping logic; arithmetic-mean target;
five-fold outer `GroupKFold`; three-fold grouped inner tuning by RMSE; all
model families, variants, settings, search spaces, and seeds; fold-safe
preprocessing; pooled and fold metrics; full-data refits; 80x80 convex-hull
surfaces; RSCI definition and weights; profile quantiles; and explicit model
roles. Regression checks compare old and new synthetic runs after semantic
column mapping.
