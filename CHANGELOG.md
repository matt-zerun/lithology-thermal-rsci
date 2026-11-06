# Changelog

## GitHub code-only snapshot — 2026-11-06 (based on 2.0.1)

- Published a curated code-only source tree excluding archive results, article
  figures, figure generators and source-specific reference-output builders.
- Preserved unchanged all retained core scientific Python modules, configuration
  JSON/YAML and synthetic input CSV files.
- Updated the README, data-availability notes, Git ignore rules, dependency
  declarations, environment/boundary validators and source-metadata tests.
- Retained software version 2.0.1 and the Zenodo concept DOI; this snapshot is
  not a substitute for the complete archived release.
- Full four-family runtime tests require pyGAM and scientific dependencies.


## 2.0.1 — 2026-11-05 — author and rights metadata alignment

- Unified creator, copyright holder, and Zenodo rights holder as Mateusz Żeruń.
- Retained PIG-PIB exclusively as the author's scientific affiliation.
- Retained MIT licensing and the existing Zenodo concept DOI.
- Updated release metadata, version identifiers, licensing documentation,
  and the corresponding non-scientific release-metadata tests.
- Preserved the validated 2.0.0 scientific implementation, numerical inputs,
  synthetic demonstration, reference outputs, and figures byte-for-byte.
- Synchronized release-date metadata to 2026-11-05 in `.zenodo.json` and `CITATION.cff`.
- The Zenodo record date must be checked against the actual publication date.


## 2.0.0 — 2026-09-16 — canonical public-schema release

- Adopted the shared workflow-level physical vocabulary and identifier
  ontology without changing the scientific workflow.
- Renamed the public observation, material-state, grouped-validation, surface,
  profile, and identifier-free reference-output columns.
- Added strict actionable validation, optional dry/particle-density fields,
  likely-unit checks, and the configurable wet/dry-density identity check.
- Added a blank input template, `DATA_SCHEMA.md`, `COMMON_DATA_MODEL.md`,
  `METHODS_MAPPING.md`, and `MIGRATION_NOTES.md`.
- Added `run_analysis.py --config config/example_config.yml` and the installed
  `lithology-thermal-run` command.
- Preserved all v1.1.1 model settings, folds, seeds, metrics, RSCI settings,
  predictions, model roles, and publication figures.

## 1.1.1 — publication-figure export maintenance release

- Preserved the validated v1.1.0 modelling, grouped-validation, RSCI, model-role,
  and numerical-result logic without change.
- Standardised all publication raster output and raster elements embedded in
  vector files at 600 dpi by default.
- Added PDF TrueType font embedding, editable SVG text, opaque white figure
  backgrounds, and LZW-compressed TIFF export.
- Added current Supplement Figure S2 source-versus-state distributions and
  Figure S3 source-versus-state occupancy comparisons.
- Updated all-family SMOOTH profile output for current Supplement Figures
  S8a–S8d.
- Renumbered data-driven Supplement outputs to the current S5–S7 designations;
  static conceptual/workflow Figures 1, S1, and S4 remain external to the
  data-driven generator.
- Added selectable `main`, `core`, and `full` figure sets and explicit source-
  observation input for the full set.
- Added automated checks of raster dimensions, stored DPI, transparency, and
  optional format completeness.
- Added a generic authorised-data runner, persisted the prepared observation
  and material-state tables in each workflow output, generated response
  profiles for every fitted candidate, and extended workflow auditing to the
  complete profile file set.
- Added an input preflight that stops figure generation before any partial
  output is written when candidate, role, surface, or profile inputs are
  incomplete.
- Updated the frozen figure directory and reference-output mapping to the
  archived report and supplementary structure.

## 1.1.0 — grouped-validation and response-surface release

- Changed the primary modelling unit from individual source observations to
  unique material states defined by sample/material identity, lithology,
  gravimetric water content, and measured wet bulk density.
- Aggregated all conductivity measurements mapping to the same state using the
  arithmetic mean while retaining contributing-measurement count, standard
  deviation, minimum, and maximum for audit.
- Added the required `parent_material_id` field for parent materials or
  parent-material series.
- Replaced the historical random holdout and sample-level validation with
  five-fold outer `GroupKFold` by `parent_material_id` within each lithology.
- Changed TUNED optimisation to three-fold grouped inner cross-validation
  restricted to each outer-training portion, with RMSE as the criterion.
- Added inner- and outer-fold group-overlap audits and the protocol identifier
  `material_series_nested_groupkfold_rmse_v2`.
- Kept fit-dependent preprocessing inside the corresponding training fold;
  SVR uses a fold-fitted `StandardScaler` pipeline.
- Retained pooled R², RMSE, MAE, and MBE, with
  `MBE = mean(predicted − observed)`.
- Separated grouped predictive evaluation from post-validation full-data
  fitting used for response-surface geometry.
- Retained BASE, SMOOTH, INTERMEDIATE, and TUNED as non-ordinal candidate
  configurations; TUNED has no automatic preference.
- Adopted the canonical RSCI implementation and the lithology-specific
  predictive and interpretive model roles.
- Rebuilt the public reference outputs from the final 2,242 → 703 → 235
  and added exact aggregate tables, selected grids, selected profile data, and
  final publication figures.
- Replaced the public synthetic example with a hierarchical demonstration that
  exercises state aggregation and parent-material grouping.
- Excluded restricted source observations, state tables, identifier mappings,
  fold assignments, group-withheld record-level predictions, detailed inner
  tuning records, and fitted reference-analysis estimators.
- Added release-boundary, metadata, reference-output, and scientific-checkpoint
  tests.

## 1.0.0 — historical public software release

- Released the initial publication-oriented four-family workflow for SVR, GAM,
  RF, and XGB under the MIT License.
- Implemented convex-hull-restricted response grids and the five-component
  Response-Surface Consistency Index.
- Added synthetic demonstration data, tests, citation metadata, and aggregate
  reference outputs.

Version 1.0.0 remains an immutable historical snapshot. Its validation logic
and model-dependent results are superseded by version 1.1.0.
