# Inflation sensitivity plan (deferred)

This note records Step 6 from `Documentation/next_steps.md`. Inflation adjustment is **not**
the next main experiment. It stays a later sensitivity check after feature engineering,
validation-only tuning, robust-loss comparison, and feature ablation.

## Why defer

The AHS proxy target is nominal USD across 2015–2023 waves, but the 2023 deterioration is not
explained by inflation alone. The harmonized release documents a response-cap change from about
USD 9,998 to USD 99,998. CPI normalization would not repair that structural measurement shift.

Any inflation study must separate:

1. General price inflation
2. Survey response-cap / measurement change
3. Actual maintenance-cost distribution change

## Planned sensitivity scope (not yet implemented)

When authorized, run a controlled sensitivity experiment that:

- Keeps the frozen split and evaluation policy unchanged
- Applies a documented CPI or construction-cost index by label wave only for sensitivity rows
- Reports both nominal-USD and inflation-adjusted metrics side by side
- Does not replace the primary nominal-USD experiments or selection policy

## Current primary line

Continue with:

- `ahs-feature-engineering-v1`
- `ahs-model-tuning-v1`
- `ahs-robust-loss-v1`
- `ahs-feature-ablation-v1`

All use raw nominal USD targets and the existing high-cost threshold fit on training labels.
