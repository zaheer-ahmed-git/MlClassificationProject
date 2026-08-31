# AHS Log1p Target Experiment: `ahs-baselines-models-log1p-v1`

## Status and claim boundary

This fixed comparison uses the same public AHS proxy task, release, split, and frozen
features as `ahs-baselines-models-v1`. It is **not WAPDA data**, not a validated WASC/WAPDA
forecast, and not an operational model. RHFS labels were not merged and NYC HPD was not
opened. Row-level predictions and fitted artifacts remain `local-analysis-only`.

The only intentional change is the target representation for the three fitted regressors:
they train on `log1p(USD)` and store predictions after `expm1` so that every reported metric
is in original USD. Baselines stay on raw USD label summaries so the A/B contrast isolates
the model target transform. No hyperparameter search or model selection was performed.

## Fixed fit and evaluation contract

- Fit rows, evaluation rows, features, high-cost threshold (USD 1,428), seed (`20260810`),
  and system set match `ahs-baselines-models-v1`.
- Model target transform: `y' = log(1 + y)` on training labels only.
- Prediction inverse: `pred_usd = expm1(model.predict(X))`.
- Metrics: MAE, RMSE, and high-cost precision/recall/F1 on original USD after inverse.
  Median absolute error (MedAE) is reported below from `predictions.csv` for interpretation;
  it is not part of the frozen metrics artifact schema shared with the raw-target run.
- Prediction clipping: none. Sample weighting: none.
- Config: `configs/experiments/ahs_baselines_models_log1p_v1.toml`.
- Schema summary: `configs/schemas/ahs_experiment_log1p_v1.json`.

## Results versus `ahs-baselines-models-v1`

Baselines are identical across both experiments (raw USD rules). Differences appear only for
linear regression, Random Forest, and gradient boosting.

### Primary view — validation (USD)

| System | MAE raw | MAE log1p | RMSE raw | RMSE log1p |
|---|---:|---:|---:|---:|
| Training median | 832.16 | 832.16 | 1,546.63 | 1,546.63 |
| Type median | 827.95 | 827.95 | 1,549.36 | 1,549.36 |
| Prior cost | 952.44 | 952.44 | 1,682.96 | 1,682.96 |
| Linear regression | 849.50 | 870.42 | 1,370.12 | 2,094.53 |
| Random Forest | 850.27 | 837.40 | 1,370.85 | 1,565.89 |
| Gradient boosting | 843.34 | 836.71 | 1,369.70 | 1,570.75 |

### Primary view — test (USD)

| System | MAE raw | MAE log1p | RMSE raw | RMSE log1p | High-cost F1 raw | High-cost F1 log1p |
|---|---:|---:|---:|---:|---:|---:|
| Training median | 965.85 | 965.85 | 2,360.09 | 2,360.09 | -- | -- |
| Type median | 962.81 | 962.81 | 2,361.65 | 2,361.65 | -- | -- |
| Prior cost | 1,058.25 | 1,058.25 | 2,358.81 | 2,358.81 | 0.410 | 0.410 |
| Linear regression | 950.91 | 1,001.19 | 2,182.90 | 3,081.81 | 0.384 | 0.125 |
| Random Forest | 956.54 | 965.27 | 2,188.13 | 2,362.41 | 0.397 | 0.032 |
| Gradient boosting | 949.15 | 967.45 | 2,188.68 | 2,369.28 | 0.356 | 0.008 |

### Pre-2023-cap sensitivity — test (USD)

| System | MAE raw | MAE log1p | RMSE raw | RMSE log1p |
|---|---:|---:|---:|---:|
| Type median | 824.82 | 824.82 | 1,529.88 | 1,529.88 |
| Linear regression | 833.34 | 873.06 | 1,334.46 | 2,847.94 |
| Random Forest | 837.78 | 826.49 | 1,339.19 | 1,531.06 |
| Gradient boosting | 829.68 | 828.44 | 1,336.06 | 1,541.31 |

### MedAE on primary test (from predictions; USD)

| System | MedAE raw | MedAE log1p |
|---|---:|---:|
| Linear regression | 581.00 | 359.22 |
| Random Forest | 574.53 | 365.68 |
| Gradient boosting | 568.36 | 357.28 |

## Interpretation

On primary-test MAE and RMSE in dollars, log1p training did not beat the raw-target models.
Tree models gained a little validation MAE and pre-2023-cap test MAE, and MedAE fell for all
three fitted models, but RMSE rose and high-cost F1 collapsed because log-space fits
under-predict the USD 1,428 tail after `expm1`. Linear regression was the worst hit on RMSE.
Log1p removed the 186 negative linear-regression predictions seen in the raw run.

Under `ahs-selection-policy-v1`, this run still does not promote a fitted model. Keep
reporting `type_median` / `prior_cost` from the raw-target experiment unless a later written
authorization changes the selection policy.

## Reproduction and artifacts

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-modeling.txt
PYTHONPATH=src .venv/bin/python -m caip_maintenance.data train-ahs-experiment --release public-corpus-v0.2.0-ahs --split ahs-grouped-temporal-v1 --preprocessor ahs-training-fold-v1 --experiment ahs-baselines-models-log1p-v1
PYTHONPATH=src .venv/bin/python -m caip_maintenance.data audit-experiment --release public-corpus-v0.2.0-ahs --split ahs-grouped-temporal-v1 --preprocessor ahs-training-fold-v1 --experiment ahs-baselines-models-log1p-v1
```

Immutable ignored artifacts:
`artifacts/experiments/public-corpus-v0.2.0-ahs/ahs-grouped-temporal-v1/ahs-training-fold-v1/ahs-baselines-models-log1p-v1/`.
The independent artifact audit passed all 11 checks on 2026-08-20.
