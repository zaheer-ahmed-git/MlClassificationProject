# AHS Baseline and Model Experiment: `ahs-baselines-models-v1`

## Status and claim boundary

This fixed comparison uses the public AHS proxy task `future_routine_cost_proxy_v1`,
release `public-corpus-v0.2.0-ahs`, split `ahs-grouped-temporal-v1`, and frozen features
from `ahs-training-fold-v1`. It is **not WAPDA data**, not a validated WASC/WAPDA
forecast, and not an operational model. RHFS labels were not merged and NYC HPD was not
opened. Row-level predictions and fitted artifacts remain `local-analysis-only`.

The experiment was run on 2026-08-10 and its independent artifact audit passed all 11
checks. No hyperparameter search or model selection was performed, so this result does not
promote a winning model.

## Fixed fit and evaluation contract

- Fit rows: the 13,871 training rows only. Validation and test labels are used only to
  calculate metrics after prediction.
- Evaluation rows: 15,400 validation rows and 56,854 test rows in the primary view. The
  pre-2023-cap sensitivity view has the same 15,400 validation rows and 37,401 test rows.
- Inputs: the same 205 frozen `ahs-training-fold-v1` columns for all trained models.
- Outcome: later-wave nominal-USD AHS `MAINTAMT`, without target imputation or clipping.
- Primary metric: MAE. Additional metrics: RMSE and high-cost precision, recall, and F1.
- High cost: actual or predicted value at least USD 1,428. This threshold is the frozen
  nearest-rank 80th percentile of training labels; validation and test quantiles are never
  used.
- Prediction clipping: none. Sample weighting: none. Random seed: `20260810`.

The declarative contract and complete estimator parameters are in
`configs/experiments/ahs_baselines_models_v1.toml`; the artifact contract is summarized in
`configs/schemas/ahs_experiment_v1.json`.

## Baseline rules

Baselines run before the fitted regressors and learn label summaries from training rows
only:

1. **Training median:** predict the training-label median, USD 497, for every row.
2. **Type median:** predict the training-label median for the row's earlier-wave
   `building_type_code`. A missing or category unseen during training falls back to the
   global training median of USD 497.
3. **Prior cost:** use the unscaled earlier-wave `prior_routine_maintenance_usd` when it is
   present. Missing prior cost falls back to the global training median of USD 497. The
   later-wave label is never substituted for a missing prior value.

## Fixed models

- Ordinary least-squares linear regression with an intercept.
- Random Forest with 200 trees, maximum depth 14, minimum leaf size 5, all features
  considered at each split, and single-threaded deterministic prediction.
- Histogram gradient boosting with learning rate 0.05, 200 maximum iterations, 31 maximum
  leaf nodes, minimum leaf size 20, and L2 regularization 1.0.

## Results

All cost metrics are nominal USD. `--` means precision or F1 is undefined because the
baseline never predicts a value at or above USD 1,428. Validation is identical in both
views because no validation row has a 2023 label.

### Primary view — validation

| System | MAE | RMSE | High-cost precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|
| Training median | 832.16 | 1,546.63 | -- | 0.000 | -- |
| Type median | **827.95** | 1,549.36 | -- | 0.000 | -- |
| Prior cost | 952.44 | 1,682.96 | 0.424 | **0.339** | **0.377** |
| Linear regression | 849.50 | 1,370.12 | 0.475 | 0.278 | 0.351 |
| Random Forest | 850.27 | 1,370.85 | 0.444 | 0.303 | 0.360 |
| Gradient boosting | 843.34 | **1,369.70** | **0.487** | 0.247 | 0.328 |

### Primary view — test

| System | MAE | RMSE | High-cost precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|
| Training median | 965.85 | 2,360.09 | -- | 0.000 | -- |
| Type median | 962.81 | 2,361.65 | -- | 0.000 | -- |
| Prior cost | 1,058.25 | 2,358.81 | 0.456 | **0.373** | **0.410** |
| Linear regression | 950.91 | **2,182.90** | **0.508** | 0.309 | 0.384 |
| Random Forest | 956.54 | 2,188.13 | 0.476 | 0.340 | 0.397 |
| Gradient boosting | **949.15** | 2,188.68 | 0.501 | 0.276 | 0.356 |

### Pre-2023-cap sensitivity — test

| System | MAE | RMSE | High-cost precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|
| Training median | 828.69 | 1,528.56 | -- | 0.000 | -- |
| Type median | **824.82** | 1,529.88 | -- | 0.000 | -- |
| Prior cost | 936.53 | 1,630.49 | 0.437 | **0.367** | **0.399** |
| Linear regression | 833.34 | **1,334.46** | **0.490** | 0.306 | 0.377 |
| Random Forest | 837.78 | 1,339.19 | 0.458 | 0.338 | 0.389 |
| Gradient boosting | 829.68 | 1,336.06 | 0.487 | 0.276 | 0.352 |

## Interpretation and limitations

The type-median baseline has the lowest validation MAE. Gradient boosting has the lowest
primary-test MAE, improving on the type median by USD 13.66 (about 1.42%), but it is USD
4.86 worse than that baseline in the pre-2023-cap test view. Linear regression has the
lowest test RMSE in both views. The prior-cost baseline has the highest held-out high-cost
F1. These differing rankings and the absence of tuning are reasons not to select or promote
a model from this run.

The primary test RMSE is materially higher than the pre-2023-cap result, consistent with
the changed 2023 response range being important to interpretation. Because predictions are
not silently clipped, linear regression produces 186 negative predictions; those values are
retained as model diagnostics rather than rewritten. Survey weights were not used during fitting, subgroup performance and uncertainty were not
evaluated in the experiment artifact itself, and the proxy remains a later-wave,
self-reported U.S. typical-year routine-maintenance amount rather than WAPDA's exact
next-12-month operational target. Those diagnostic gaps are addressed separately in
`Documentation/AHSDiagnosticReview.md`, which still does not authorize promotion or tuning.

## Reproduction and artifacts

Create an isolated modeling environment, then train and audit from the repository root:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-modeling.txt
PYTHONPATH=src .venv/bin/python -m caip_maintenance.data train-ahs-experiment --release public-corpus-v0.2.0-ahs --split ahs-grouped-temporal-v1 --preprocessor ahs-training-fold-v1 --experiment ahs-baselines-models-v1
PYTHONPATH=src .venv/bin/python -m caip_maintenance.data audit-experiment --release public-corpus-v0.2.0-ahs --split ahs-grouped-temporal-v1 --preprocessor ahs-training-fold-v1 --experiment ahs-baselines-models-v1
```

The immutable, ignored artifact is under
`artifacts/experiments/public-corpus-v0.2.0-ahs/ahs-grouped-temporal-v1/ahs-training-fold-v1/ahs-baselines-models-v1/`.
The training command refuses to overwrite that path when it already exists.
It contains baseline parameters, three serialized estimators, row-level predictions,
aggregate metrics, and a manifest with source/output hashes, training-row digests, software
versions, parameters, and claim-boundary flags. Serialized models are loaded only after
their recorded checksums pass.

Selection of a reported primary estimator is governed by
`Documentation/AHSSelectionPolicy.md`. Under that policy, this experiment does **not**
promote a fitted model; report `type_median` as the primary estimator and `prior_cost` as
the high-cost reference, with sensitivity MAE and high-cost F1 as required secondary reports.

A parallel fixed target-representation check with the same systems and splits is documented in
`Documentation/AHSBaselineModelLog1pExperiment.md`.
