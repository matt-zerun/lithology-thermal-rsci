# Lithology-specific RSCI workflow: canonical data schema

The public workflow begins with a screened, harmonised observation table. CSV,
XLSX, and XLSM are supported; column names are case-sensitive. Source-specific
database extraction, joins, category translation, exclusions, and identifier
construction occur before this boundary and are not part of the release.

## Observation input

| Column | Unit / values | Type | Meaning | Required | Example | Quality control |
|---|---|---|---|---:|---|---|
| `observation_id` | — | string | Unique measurement/source record | yes | `OBS-000001` | non-empty; unique |
| `material_id` | — | string | Stable physical sample or material member | yes | `MAT-0042` | non-empty; one parent/lithology/provenance mapping |
| `parent_material_id` | — | string | Parent material or series used as the grouped-CV unit | yes | `PARENT-0017` | non-empty; kept wholly within train or validation in each fold |
| `lithology` | controlled category | string | Harmonised mineral-soil class | yes | `sand` | `sand`, `silt`, `clayey_soil`, or `clay` |
| `water_content_pct` | % dry mass | numeric | Gravimetric water content, `100*m_w/m_s` | yes | `12.5` | finite; >=0 |
| `bulk_density_mg_m3` | Mg m^-3 | numeric | Measured wet bulk density | yes | `1.86` | finite; >0; likely-unit and density checks |
| `thermal_conductivity_w_mk` | W m^-1 K^-1 | numeric | Measured thermal conductivity | yes | `1.74` | finite; >0; values >50 trigger a likely-unit error |
| `source` | — | string | Non-sensitive provenance label | yes | `laboratory` | non-empty; stable within `material_id` |
| `data_origin` | — | string | Provenance category | yes | `experimental` | non-empty; stable within `material_id` |
| `dry_density_mg_m3` | Mg m^-3 | numeric | Dry bulk density | no | `1.65` | positive when present; <= wet density; identity checked |
| `particle_density_mg_m3` | Mg m^-3 | numeric | Particle density | no | `2.65` | positive when present; >= wet bulk density |
| `measurement_temperature_c` | deg C | numeric | Measurement-condition metadata; not a predictor | no | `20.0` | finite when present |

`Mg m^-3` and `g cm^-3` are numerically identical. Values in `kg m^-3` must
be converted before validation. Extra source metadata are ignored unless a
future documented workflow explicitly uses them.

## Strict input behaviour

The validator reports the field and example CSV-style row numbers for missing,
non-numeric, infinite, duplicate, empty, unsupported, or physically invalid
values. It does not silently rename legacy columns, convert units, impute data,
or discard malformed records. Every lithology must retain at least ten source
observations by default; this operational precondition does not replace the
much stronger group-count requirements imposed by five-fold outer and
three-fold inner validation.

When dry density is supplied, the validator checks

```text
bulk_density_mg_m3
    = dry_density_mg_m3 * (1 + water_content_pct / 100)
```

using the final 2.0.0 tolerance `0.02 Mg m^-3 + 2% of wet bulk density`. The
tolerance is configurable and accommodates rounded archival values; it is an
input-integrity check rather than an exclusion rule or transformation.

## Unique material-state output

A material state is defined by the exact key

```text
material_id + lithology + water_content_pct + bulk_density_mg_m3
```

All conductivity measurements mapped to a key are aggregated to the arithmetic
mean. The modelling table contains:

| Column | Meaning |
|---|---|
| `material_state_id` | Deterministic unique state identifier |
| `material_id` | Source material/sample identity |
| `parent_material_id` | Grouped-validation identity |
| `lithology` | Harmonised class |
| `water_content_pct` | State water content |
| `bulk_density_mg_m3` | State measured wet bulk density |
| `thermal_conductivity_w_mk` | Arithmetic-mean modelling target |
| `thermal_conductivity_sd_w_mk` | Sample SD of contributing measurements; missing for one measurement |
| `thermal_conductivity_min_w_mk` | Minimum contributing value |
| `thermal_conductivity_max_w_mk` | Maximum contributing value |
| `measurement_count` | Number of contributing conductivity measurements |
| `source`, `data_origin` | Audited provenance inherited from the material |
| `first_observation_id` | Traceability field for authorised local output only |

`measurement_count` does not assert that all contributors are technical
replicates. Identifier-bearing prepared/state tables and fold-level outputs are
local run products and must not be placed in a public archive.

## Files

- Blank template: `data/templates/rsci_canonical_observations_template.csv`
- Machine-readable dictionary: `data/input_schema.csv`
- Fictional demonstration: `data/synthetic_example.csv`

The synthetic data exercise observation-to-state aggregation and
parent-material grouping. They do not reproduce, approximate, or resample the
restricted reference observations and cannot reproduce archived numerical
results.
