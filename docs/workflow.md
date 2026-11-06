# Canonical scientific workflow retained in v2.0.0

Version 1.1.1 changes publication-figure generation only. The modelling,
grouped-validation, response-surface, RSCI, and model-role workflow below is
unchanged from v1.1.0.

## 1. Dataset construction

1. Apply source-specific inclusion and exclusion rules before modelling.
2. Treat gravimetric water content on a dry-mass basis and measured wet bulk
   density as mathematically coupled but nonredundant descriptors of achieved
   material state.
3. Aggregate source observations to unique material states defined by
   `material_id`, lithology, water content, and measured wet bulk density.
4. Use the arithmetic mean when multiple conductivity measurements map to the
   same state; retain measurement count, standard deviation, minimum, and
   maximum for audit.
5. Assign every state to one parent material or parent-material series through
   `parent_material_id`.

The archived reference analysis contains 2,242 source observations, 703 unique
material states, and 235 parent-material groups. These are verification
checkpoints, not hard-coded requirements of the software.

## 2. Predictive validation

For each lithology separately:

1. Construct five deterministic outer `GroupKFold` partitions using
   `parent_material_id`.
2. Keep every state from a parent-material group entirely in training or
   validation within each fold.
3. Fit BASE, SMOOTH, and INTERMEDIATE configurations using their prespecified
   settings.
4. For each TUNED candidate, optimise hyperparameters only within the current
   outer-training portion using three-fold grouped inner cross-validation and
   mean RMSE.
5. Fit all preprocessing, including SVR scaling, only on the applicable
   training subset.
6. Store one group-withheld prediction per state and candidate.
7. Calculate pooled R², RMSE, MAE, and MBE directly from the complete set of
   group-withheld predictions. MBE is mean(predicted − observed).
8. Retain fold-level metrics as stability diagnostics; do not substitute their
   arithmetic mean for the pooled metrics.

The final integrity audit contains 64 candidates, 320 outer-fold metric rows,
11,248 group-withheld predictions, 96 grouped tuning runs, 288 inner-fold audit
records, and zero parent-material-group overlap in every outer and inner split.

## 3. Full-data reconstruction and geometry

Only after grouped predictive validation is complete:

1. Refit each BASE, SMOOTH, and INTERMEDIATE candidate to all material states
   of its lithology.
2. Tune the final TUNED candidate using grouped cross-validation on all states
   of the lithology, then refit it to all states.
3. Generate an 80 × 80 response grid for each candidate.
4. Mask nodes outside the state-level convex hull.
5. Calculate raw RSCI diagnostics and normalise the relative components within
   lithology across the complete 16-candidate set.
6. Review grouped predictive performance, RSCI, response geometry,
   cross-family agreement, occupancy, and profile behaviour jointly.
7. Extract response profiles at the 25th, 50th, and 75th percentiles calculated
   from unique material states for each lithology, retaining only cross-section
   segments inside the convex hull.

The convex hull distinguishes interpolation from unconstrained extrapolation.
It is not a physical boundary and does not imply uniform observational support
inside the hull. No hard local-support mask is imposed.

Predictive validation and full-data response-surface geometry are separate
stages. Predictions from the final full-data fits never enter R², RMSE, MAE, or
MBE.

## 4. Authorised-data execution and output audit

`scripts/10_run_analysis_pipeline.py` runs the complete workflow from a
screened schema-compliant CSV or XLSX table. It writes the validated
`prepared_observations.csv` and aggregated `material_states.csv` alongside the
grouped-validation tables, candidate models, response surfaces, and two
directional profile tables per candidate. These identifier-bearing run outputs
are local analysis products and must not be added to the public source archive.

`scripts/11_audit_workflow_outputs.py` verifies candidate-key consistency,
group separation, one group-withheld prediction per state and candidate,
reconstructed metrics, finite values, and the complete model, surface, profile,
and tuning-file sets.
