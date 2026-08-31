# AHS next-steps execution summary

This document records execution of `Documentation/next_steps.md` on 2026-08-23.

## Step 1 — Feature audit (complete)

Command:

```bash
PYTHONPATH=src .venv/bin/python -m caip_maintenance.data audit-ahs-features \
  --release public-corpus-v0.2.0-ahs \
  --split ahs-grouped-temporal-v1 \
  --preprocessor ahs-training-fold-v1
```

Artifacts:

`artifacts/reviews/public-corpus-v0.2.0-ahs/ahs-grouped-temporal-v1/ahs-training-fold-v1/ahs-feature-audit-v1/`

Findings on 13,871 training rows:

- 26 harmonized candidates expand to 205 model matrix columns (excluding `snapshot_id`)
- `roof_leak_code` excluded from value representation (>40% training missingness); missing indicator kept
- No continuous floor-area field; `prior_maintenance_per_sqft` is not directly available
- `survey_weight` flagged as survey-design only, not WAPDA-operational

## Step 2 — Derived features + Experiment 3 (complete)

New preprocessor `ahs-feature-engineering-v1` adds five cutoff-safe derived numerics:

| Feature | Definition |
|---|---|
| `property_age_years` | `source_wave_year - year_built` |
| `log_prior_routine_maintenance_usd` | `log1p(prior_routine_maintenance_usd)` |
| `prior_cost_per_room` | `prior / max(total_rooms, 1)` |
| `rooms_per_bedroom` | `total_rooms / max(bedrooms, 1)` |
| `condition_defect_count` | count of condition codes with value ≥ 2 |

Preprocessor: 215 model columns. Preprocessing audit: 11/11 passed.

Experiment `ahs-feature-engineering-v1` audit: 11/11 passed.

Primary test MAE vs raw baseline (`ahs-baselines-models-v1`):

| System | Raw | Engineered |
|---|---:|---:|
| Type median | 962.81 | 962.81 |
| Gradient boosting | 949.15 | 950.42 |

Engineering alone did not materially beat the raw-target baseline on primary-test MAE.

## Step 3 — Model-specific preprocessing (verified)

Both preprocessors fit imputers/encoders/scalers and the USD 1,428 threshold on training rows only. Linear regression consumes standardized numerics; tree models receive the same encoded matrix without extra scaling at model fit time.

## Step 4 — Validation-only tuning (complete)

Experiment `ahs-model-tuning-v1` selects RF/GB hyperparameters on validation primary MAE only, then refits on training.

Primary test MAE:

| System | Fixed engineered | Tuned |
|---|---:|---:|
| Linear regression | 954.55 | 954.55 |
| Random Forest | 957.83 | 946.57 |
| Gradient boosting | 950.42 | 945.27 |

Tuning improved tree models; gradient boosting is best tuned primary-test MAE among LR/RF/GB.

## Step 5 — Robust loss (complete)

`HistGradientBoostingRegressor` in the pinned stack does not expose Huber loss; Huber uses `GradientBoostingRegressor` while squared/absolute remain histogram GB.

Primary test MAE:

| Loss | MAE |
|---|---:|
| Squared | 950.42 |
| Absolute | 899.84 |
| Huber (classic GB) | 905.91 |

Absolute error loss gave the largest primary-test MAE gain in this sequence.

## Step 6 — Inflation sensitivity (deferred)

Documented in `Documentation/AHSInflationSensitivityPlan.md`. Not run as a main experiment because 2023 cap change dominates nominal-USD drift.

## Step 7 — Feature ablation (complete)

Experiment `ahs-feature-ablation-v1` fits gradient boosting on feature groups.

Primary test MAE (GB configs):

| Configuration | MAE |
|---|---:|
| All features | 947.79 |
| Structural + prior | 952.65 |
| All except prior | 979.67 |
| Structural only | 989.71 |
| Structural + socioeconomic | 986.88 |

Prior maintenance features matter: dropping them raises MAE by about USD 32 versus the full engineered set.

## Commands added

```bash
audit-ahs-features
train-ahs-tuning / audit-ahs-tuning
train-ahs-robust-loss / audit-ahs-robust-loss
train-ahs-ablation / audit-ahs-ablation
preprocess-ahs --preprocessor ahs-feature-engineering-v1
train-ahs-experiment --preprocessor ahs-feature-engineering-v1 --experiment ahs-feature-engineering-v1
```

## Interpretation

The sequence supports the next-steps thesis: target transforms were not the main lever; feature engineering plus validation-only tuning and robust loss did more. Absolute-error gradient boosting on engineered features reached primary-test MAE 899.84 versus 949.15 for the original fixed GB baseline. No model is promoted; selection policy still applies to the frozen raw-target comparison for reporting.
