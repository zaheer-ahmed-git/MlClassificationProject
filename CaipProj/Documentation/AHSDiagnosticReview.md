# AHS Diagnostic Review: `ahs-diagnostic-review-v1`

## Status and claim boundary

This review analyzes the frozen AHS comparison `ahs-baselines-models-v1` without fitting,
tuning, selecting, or promoting any model. It covers residual concentration, subgroup MAE
and high-cost metrics, survey-weighted sensitivity, and decision utility. Results remain
**public-proxy only**: not WAPDA data, not a validated WASC forecast, not an operational
estimator. RHFS labels were not merged and NYC HPD was not opened.

Artifact path:

```text
artifacts/reviews/public-corpus-v0.2.0-ahs/ahs-grouped-temporal-v1/ahs-training-fold-v1/ahs-baselines-models-v1/ahs-diagnostic-review-v1/
```

The review audit passed all 10 checks. Authorization remains:

- `authorize_hyperparameter_search = false`
- `authorize_model_promotion = false`
- MAE reference: `type_median`
- High-cost triage reference: `prior_cost`

## Why this stage existed

The fixed comparison produced conflicting leaders:

| Objective | Leader |
|---|---|
| Validation MAE | type median |
| Primary-test MAE | gradient boosting |
| Pre-2023 sensitivity-test MAE | type median |
| Primary-test high-cost F1 | prior cost |

A single “best model” claim would hide that conflict. This review documents where errors
concentrate and whether survey weights change the story before any tuning is authorized.

## Residual concentration (primary test)

Absolute-error mass is dominated by the high-cost band (`target >= USD 1,428`):

| System | Overall MAE | High-cost band MAE | Below-threshold MAE | Zero-band MAE | Neg. preds |
|---|---:|---:|---:|---:|---:|
| Type median | 962.81 | 2,949.98 | 282.68 | 460.74 | 0 |
| Gradient boosting | 949.15 | 2,234.97 | 472.33 | 800.28 | 0 |
| Linear regression | 950.91 | 2,211.20 | 483.27 | 806.37 | 113 |
| Prior cost | 1,058.25 | 2,434.67 | 618.04 | 562.59 | 0 |

Interpretation:

- Gradient boosting’s small overall MAE gain comes mainly from better high-cost residuals,
  while it is worse than type median on zeros and ordinary positive costs.
- Type median under-predicts high-cost cases systematically (mean residual ≈ −2,950 USD).
- Linear regression retains negative predictions under the no-clipping policy (27
  validation, 113 primary-test).

By label wave, primary-test MAE rises sharply in 2023, consistent with the response-cap
discontinuity:

| Label wave | n | Type-median MAE | Gradient-boosting MAE |
|---:|---:|---:|---:|
| 2017 | 11,047 | 751.53 | 787.52 |
| 2019 | 12,131 | 814.72 | 822.61 |
| 2021 | 14,223 | 890.37 | 868.46 |
| 2023 | 19,453 | 1,228.10 | 1,178.84 |

## Subgroups

Building-type and census-division metrics were reported only for groups with at least 50
rows. On primary test, the largest absolute errors by type-median MAE include building
types `04` and `02`; type `02` dominates sample size (47,777 rows). No subgroup reverses
the broader conclusion that MAE and high-cost F1 select different systems.

## Survey-weight sensitivity

Primary-test survey-weight coverage is 100%. Weighting lowers absolute MAE levels and
changes mid-pack order (`random_forest` vs medians), but **does not change the MAE leader**:
gradient boosting remains first and prior cost remains last. Weighted metrics therefore do
not authorize promotion or discard the unweighted ranking conflict.

## Decision utility

For budgeting / prioritization use of this public proxy:

1. **Cost-level reference:** keep `type_median` as the transparent MAE baseline. It wins
   validation and the pre-2023 sensitivity test; gradient boosting’s primary-test MAE edge
   is only about USD 14 and does not survive the sensitivity view.
2. **High-cost triage reference:** keep `prior_cost`. It leads held-out high-cost F1 even
   though its MAE is worse.
3. **Do not promote gradient boosting, random forest, or linear regression** from this run.
4. **Do not start hyperparameter search yet.** No selection criterion was frozen; searching
   now would invent a post-hoc objective after inspecting held-out patterns.

## Reproduction

```bash
PYTHONPATH=src python3 -m caip_maintenance.data review-ahs-diagnostics \
  --release public-corpus-v0.2.0-ahs \
  --split ahs-grouped-temporal-v1 \
  --preprocessor ahs-training-fold-v1 \
  --experiment ahs-baselines-models-v1 \
  --review ahs-diagnostic-review-v1

PYTHONPATH=src python3 -m caip_maintenance.data audit-diagnostic-review \
  --release public-corpus-v0.2.0-ahs \
  --split ahs-grouped-temporal-v1 \
  --preprocessor ahs-training-fold-v1 \
  --experiment ahs-baselines-models-v1 \
  --review ahs-diagnostic-review-v1
```

The review directory is immutable. Use a new review identifier if the contract changes.

## What this authorizes next

The selection policy is now frozen in `Documentation/AHSSelectionPolicy.md` /
`configs/selection/ahs_selection_policy_v1.toml`.

Applied to this comparison: **no fitted model is promoted**. Report **`type_median`** as the
primary estimator and **`prior_cost`** as the high-cost reference. Sensitivity MAE and
high-cost F1 remain required secondary reports. Hyperparameter search stays closed unless a
later written decision opens it under the same guardrails.

Still out of scope: RHFS/AHS label merge, NYC HPD, WASC/WAPDA validation claims, and web POC
promotion of a fitted model.
