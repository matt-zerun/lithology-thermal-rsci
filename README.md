# Lithology-specific thermal-conductivity response surfaces and RSCI diagnostics

**Version 2.0.1 — computational code-only repository.**

This repository provides an installable Python workflow for modelling the thermal
conductivity of mineral soils using gravimetric water content and measured wet
bulk density. The workflow evaluates lithology-specific machine-learning
response surfaces and their **Response-Surface Consistency Index (RSCI)**.
It contains source code, analysis configurations, schema documentation,
synthetic example data, and automated tests. This is a curated **code-only
subset** of the complete Zenodo 2.0.1 archive, **not** a byte-identical copy
of the archived release.

## Scientific scope

- Unique material-state aggregation, with parent-material provenance.
- Separate five-fold outer `GroupKFold` validation within each lithology;
  `parent_material_id` prevents material-series leakage.
- Nested three-fold group-aware tuning with RMSE for `TUNED` candidates.
- SVR, GAM, random-forest (RF), and extreme gradient boosting (XGB) models;
  BASE, SMOOTH, INTERMEDIATE, and TUNED variants.
- Pooled group-withheld R², RMSE, MAE, and signed MBE;
  independent full-data fitting for geometric analysis.
- Response surfaces interpreted only within the state-level convex hull;
  RSCI and 25/50/75-percentile directional profiles.

These are empirical analytical reconstructions, **not** constitutive material
laws, causal models, or independent effects of water content and density.
RSCI measures relative geometric regularity; high RSCI does not establish
predictive reliability or physical validity.

## Repository contents

| Location | Contents |
| --- | --- |
| `src/lithology_thermal_rsci/` | Core computational package |
| `config/` | Model variants, search spaces, RSCI and run settings |
| `data/` | Synthetic observations, input schema, blank template |
| `scripts/` | Validation, tuning, modelling, RSCI, profiles and audits |
| `tests/` | Unit, synthetic-workflow and data-boundary tests |
| `docs/` | Workflow, data availability and RSCI definitions |

The following **are deliberately not included**: published/reference tables,
reference response grids, selected reference profiles, article/supplement
figures, publication figure generators, reference-output builders, restricted
laboratory data, source data harmonisation, fitted reference models, or
record-level reference-analysis predictions.

## Installation

Python 3.11–3.14 is specified by the package metadata. On Windows (Anaconda
Prompt or a terminal in a suitable environment), install as follows:

```powershell
conda create -n rsci python=3.11 -y
conda activate rsci
python -m pip install -e ".[test]"
```

Or recreate the frozen **2.0.0 reference dependency version set** used for
archival verification (Python environment compatibility must be checked):

```powershell
python -m pip install -r requirements-lock.txt
python -m pip install -e .
```

The lock file is a list of pinned distributions, not a fully transitive
platform lock. `pyGAM` is required for GAM models; it is **not replaced** by an
alternative implementation. XLSX input uses `openpyxl`.
`matplotlib` and `pillow` are not required for this code-only distribution.

## Quick start — deterministic fictional data

```powershell
python scripts/00_validate_environment.py
python scripts/14_verify_release_boundary.py
python -m pytest
python run_analysis.py --config config/example_config.yml
```

The first command checks runtime dependencies, settings, and the synthetic
hierarchy; `--strict-lock` additionally requires every version in the frozen
reference set. The output of the synthetic demo is written to
`outputs/synthetic_example/`, which is ignored by Git.

The default example includes SVR, GAM, RF and XGB with fixed BASE, SMOOTH,
and INTERMEDIATE configurations. Running all families and variants can take
substantially longer; restrict families and variants during exploratory tests.

To run only SVR as a short calculation after installation, see:

```powershell
python scripts/10_run_analysis_pipeline.py data/synthetic_example.csv demo_outputs --models SVR --variants BASE --grid-size 12
```

## Own-data analysis

Submit an authorised, screened, schema-compliant CSV or XLSX table. See
[`DATA_SCHEMA.md`](DATA_SCHEMA.md) and
[`data/templates/rsci_canonical_observations_template.csv`](data/templates/rsci_canonical_observations_template.csv).

```powershell
python scripts/10_run_analysis_pipeline.py AUTHORISED_SCREENED_OBSERVATIONS.csv analysis_outputs --include-tuned
python scripts/11_audit_workflow_outputs.py analysis_outputs --report analysis_outputs/workflow_output_audit.json
```

Only the software implementation and fictitious data are public. Derived
record-level outputs from any real input (including group splits, predictions,
intermediate states, and fitted estimators) must remain local and be handled
according to the data provider's authorisations. See
[`docs/data_availability.md`](docs/data_availability.md).

## Reproducibility boundary

The Zenodo archive of this software series has **concept DOI
[10.5281/zenodo.21682909](https://doi.org/10.5281/zenodo.21682909)**.
The complete archived release provides frozen aggregated reference tables,
selected grids/profiles and publication artefacts, which are intentionally
absent here. The original restricted record-level experimental and harmonised
observations are not publicly distributed in either location. Consequently,
this repository supports running and testing the implementation on the
synthetic data or other authorised datasets, **not** reconstructing the exact
published reference results from public record-level inputs.

This code-only snapshot was prepared on **2026-11-06** from the 2.0.1 archive.
Its numerical/scientific core files and configuration are preserved
unchanged; non-scientific documentation, dependency lists, archival boundary
checks and metadata tests have been tailored to the GitHub scope. The original
Zenodo record's current publication status must be checked separately before
claiming a corresponding version DOI.

## Citation, authorship and rights

Software: **Mateusz Żeruń** (2026), *Lithology-specific thermal-conductivity
response surfaces and RSCI diagnostics*, version 2.0.1. For formal citation,
use the Zenodo concept DOI and the appropriate published version DOI when
available. The project [`CITATION.cff`](CITATION.cff) supplies attribution.

Copyright (c) 2026 Mateusz Żeruń. MIT License — see [`LICENSE`](LICENSE).
Polish Geological Institute – National Research Institute (PGI-NRI / PIG-PIB)
is the author's scientific affiliation. Rights metadata reflect the author's
stated attribution and do not replace an institutional legal determination.
