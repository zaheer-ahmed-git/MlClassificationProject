# AHS Selection Policy: `ahs-selection-policy-v1`

## Status

**Frozen 2026-08-12** for task `future_routine_cost_proxy_v1`, experiment
`ahs-baselines-models-v1`, split `ahs-grouped-temporal-v1`, and preprocessor
`ahs-training-fold-v1`.

This policy decides whether a system from the fixed comparison may be **reported as the
primary estimator** or **promoted as a fitted-model candidate**. It does not change labels,
features, or the no-clipping prediction rule. Results remain public-proxy only: not WAPDA
data and not a validated WASC forecast. RHFS/AHS label merge and NYC HPD remain closed.

Machine-readable copy: `configs/selection/ahs_selection_policy_v1.toml`.

## Decision rules

1. **Primary objective:** lowest **validation MAE**.
2. **Required secondary reports (never optional):**
   - pre-2023-cap **sensitivity-test MAE**
   - primary-test **high-cost F1** at the frozen USD 1,428 threshold
3. **Sensitivity guardrail for promotion of a fitted model**
   (`linear_regression`, `random_forest`, or `gradient_boosting`):
   - The validation-MAE winner may be promoted only if it is also the leader (or tied for
     leader) on pre-2023-cap sensitivity-test MAE.
   - Primary-test MAE alone never authorizes promotion.
   - High-cost F1 alone never authorizes promotion.
4. **Fallback when promotion fails:**
   - Report **`type_median`** as the primary estimator for cost-level MAE reporting.
   - Report **`prior_cost`** as the high-cost triage reference.
5. **Hyperparameter search** remains unauthorized until a separate written decision opens it.
   Search, if later opened, must target the primary objective and retain the sensitivity
   guardrail and secondary reporting requirements above.

## Application to `ahs-baselines-models-v1`

| Check | Result |
|---|---|
| Validation MAE winner | `type_median` (827.95) |
| Sensitivity-test MAE winner | `type_median` (824.82) |
| Primary-test MAE winner | `gradient_boosting` (949.15) — not the primary objective |
| Primary-test high-cost F1 winner | `prior_cost` (0.410) — secondary only |
| Fitted-model validation-MAE winner? | **No** |
| Promote a fitted model? | **No** |

**Authorized reporting under this policy:**

- Primary estimator: **`type_median`**
- High-cost reference: **`prior_cost`**
- Fitted-model promotion: **denied**
- Hyperparameter search: **still closed**

Gradient boosting’s small primary-test MAE edge does not meet the primary objective and is
not eligible for promotion. Linear regression’s negative predictions remain diagnostic-only
under the no-clipping rule.

## Claim boundary

- Do not describe the reported estimator as a WAPDA or WASC operational forecast.
- Do not omit sensitivity MAE or high-cost F1 when summarizing the comparison.
- Do not promote or tune against primary-test MAE alone.
- Keep RHFS and AHS as separate modeling views.

## What this unblocks

- Canonical reporting language for the completed fixed comparison.
- CAIP write-up of AHS proxy results with an explicit, reproducible selection rule.

## What remains blocked

- Promotion of linear regression, Random Forest, or gradient boosting from this run.
- Hyperparameter search / retuning.
- Web-POC binding to a “winning” fitted model.
- Any WASC/WAPDA validation claim.
