# Testing

## Current verification state

The package has executable registry, raw-integrity, AHS gate, harmonization, release-audit,
grouped temporal-split, training-fold-only preprocessing, a fixed AHS proxy experiment, and
an AHS residual/subgroup/weight/utility diagnostic review. The modeling tests cover
hand-calculated metrics, training-only fit boundaries, held-out label perturbation,
persistence, reload prediction equality, checksum drift, and artifact auditing. Diagnostic
review tests cover unweighted and survey-weighted metric helpers. There is still no
promoted-model or application test suite.

## Strategy

The future suite should follow risk rather than a numeric coverage target:

- Unit tests for money arithmetic, dates, mappings, controlled values, target eligibility,
  allocation, and feature windows.
- Contract tests for every source adapter and model-ready table.
- Integration tests from de-identified staging fixtures through snapshots and labels.
- Leakage tests for time boundaries and training-fold-only transforms.
- Model tests for baselines, reproducibility, artifact compatibility, and metric calculations.
- Application tests for input validation, missing data, explanations, disclosure, and loading.
- A small end-to-end smoke test using unmistakably synthetic, test-only records.

## Mandatory data-quality gates

### Inventory and keys

- Active residential inventory reconciles to 101 units and category counts
  `1/4/16/24/16/40` for A-F unless an approved scope version changes it.
- Property, building, work-order, invoice, and snapshot keys are unique where required.
- Every label-eligible direct work order resolves to one valid property.
- Shared work resolves to a valid building and approved property allocations.

### Dates and coverage

- Feature events occur on or before `as_of_date`.
- Label costs occur within the open/closed boundaries defined by the target contract.
- Construction and component dates are not after the cutoff.
- Complaint, inspection/start, completion, invoice, and payment sequences are plausible.
- A zero label requires an explicit complete-coverage status.
- Censored or incomplete labels never enter ordinary supervised evaluation.

### Money and allocation

- Eligible work-order total equals verified cost lines within an approved tolerance.
- Linked ledger amounts do not exceed transaction or work-order totals.
- Reversals and year-closing entries net as expected and remain target-ineligible.
- Allocation weights sum to 1 and allocated amounts sum to eligible shared cost.
- Major renovation cost remains separate from the primary target.

### Values, scope, and privacy

- Condition scores are integers 1-5; unknown is null, never zero.
- Units and area conversions reconcile or raise a source conflict.
- Residential labels exclude unrelated asset classes and revenue/book-value records.
- Analytical exports contain no resident name, CNIC, telephone, designation, family detail,
  unredacted narration, or direct invoice/contractor identifier.
- Duplicate workbooks, sheets, transactions, invoices, and work orders do not inflate counts.

## Leakage tests

Leakage checks are release-blocking:

- Features and labels respect the cutoff and label interval.
- High-cost thresholds, imputers, scalers, and encoders are fitted on training data only.
- Public-harmonized training labels carry lineage and `label_origin`; they are never asserted
  as observed WAPDA operational outcomes.
- AHS snapshots use an earlier wave than their labels; every transition for one tokenized
  housing unit remains in one split based on its terminal eligible label wave.
- AHS releases contain only `future_routine_cost_proxy_v1`, preserve the source response
  maximum, and mark the 2023 cap-change regime without silently clipping values.
- The primary AHS evaluation flag includes every eligible row; the sensitivity flag excludes
  only labels from the 2023 wave.
- RHFS and AHS labels are never stacked under one target identity.

- No feature timestamp exceeds its snapshot cutoff.
- Rolling features use the intended left/right interval boundaries.
- Future completion, complaint, cost, weather, or price information is unavailable to the
  feature builder.
- Imputers, encoders, scalers, feature selectors, and models are fitted on training rows only.
- Experimental high-cost thresholds are calculated from the training fold only.
- Split intervals do not place overlapping history from the same label window on both sides
  of a boundary.
- Group holdouts remain disjoint when measuring transfer to a new property or colony.

## Model evaluation tests

- MAE and RMSE match hand-calculated small fixtures.
- The historical baseline uses no future cost information.
- All compared models receive the same eligible rows, target version, features, and split.
- Fixed seeds reproduce stochastic results within documented library/platform tolerances.
- Saved and reloaded pipelines produce equivalent predictions and explanations.
- Subgroup metrics include sample counts and are suppressed or qualified when too small.
- High-cost precision/recall uses the approved fixed threshold or a training-derived top-k
  rule, never validation/test quantiles.
- Prediction intervals, if presented, have a documented calibration method and empirical
  coverage evaluation.

## Application tests

- Valid anonymized property selection returns a typed, finite prediction.
- Unknown IDs, incomplete features, incompatible artifacts, and stale schemas fail safely.
- Output includes cutoff, nominal PKR unit, artifact version, coverage status, and disclaimer.
- Feature explanations use human-readable names and correspond to the loaded pipeline.
- No response, log, screenshot, or downloadable table includes PII or raw narration.
- Aggregate views cannot reveal an individual through very small groups.

## Fixtures

Use small, deterministic, synthetic fixtures for logic and UI tests. Store them under
`tests/fixtures/synthetic/` and label them as non-WAPDA data. De-identified samples derived
from real structure require approval, a source/derivation record, and a re-identification
review. Never use real resident names or copy raw spreadsheet rows into tests.

## Implemented commands

Run from the repository root:

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m compileall -q src scripts tests
PYTHONPATH=src python3 -m caip_maintenance.data register-sources
PYTHONPATH=src python3 -m caip_maintenance.data validate-raw --source rhfs_2024
PYTHONPATH=src python3 -m caip_maintenance.data audit-release --release public-corpus-v0.1.0-rhfs
PYTHONPATH=src python3 -m caip_maintenance.data validate-raw --source ahs_2015_2023
PYTHONPATH=src python3 -m caip_maintenance.data assess-ahs
PYTHONPATH=src python3 -m caip_maintenance.data audit-release --release public-corpus-v0.2.0-ahs
PYTHONPATH=src python3 -m caip_maintenance.data audit-split --release public-corpus-v0.2.0-ahs --split ahs-grouped-temporal-v1
PYTHONPATH=src python3 -m caip_maintenance.data audit-preprocessing --release public-corpus-v0.2.0-ahs --split ahs-grouped-temporal-v1 --preprocessor ahs-training-fold-v1
PYTHONPATH=src .venv/bin/python -m caip_maintenance.data train-ahs-experiment --release public-corpus-v0.2.0-ahs --split ahs-grouped-temporal-v1 --preprocessor ahs-training-fold-v1 --experiment ahs-baselines-models-v1
PYTHONPATH=src .venv/bin/python -m caip_maintenance.data audit-experiment --release public-corpus-v0.2.0-ahs --split ahs-grouped-temporal-v1 --preprocessor ahs-training-fold-v1 --experiment ahs-baselines-models-v1
PYTHONPATH=src .venv/bin/python -m caip_maintenance.data train-ahs-experiment --release public-corpus-v0.2.0-ahs --split ahs-grouped-temporal-v1 --preprocessor ahs-training-fold-v1 --experiment ahs-baselines-models-log1p-v1
PYTHONPATH=src .venv/bin/python -m caip_maintenance.data audit-experiment --release public-corpus-v0.2.0-ahs --split ahs-grouped-temporal-v1 --preprocessor ahs-training-fold-v1 --experiment ahs-baselines-models-log1p-v1
PYTHONPATH=src python3 -m caip_maintenance.data review-ahs-diagnostics --release public-corpus-v0.2.0-ahs --split ahs-grouped-temporal-v1 --preprocessor ahs-training-fold-v1 --experiment ahs-baselines-models-v1 --review ahs-diagnostic-review-v1
PYTHONPATH=src python3 -m caip_maintenance.data audit-diagnostic-review --release public-corpus-v0.2.0-ahs --split ahs-grouped-temporal-v1 --preprocessor ahs-training-fold-v1 --experiment ahs-baselines-models-v1 --review ahs-diagnostic-review-v1
```

The test suite uses unmistakably test-only generated fixtures in temporary directories. It
checks registry bounds, mapping/code agreement, sentinel and zero handling, public-origin
flags, identifier removal, deterministic hashes, release immutability, checksum drift, the
AHS gate contract, task isolation, response-cap metadata, and release audits. Audit commands
require already built ignored releases/splits. The AHS split checks assignment completeness,
unit isolation, terminal-wave cohorts, semantic/source checksum pins, cap-sensitivity flags,
prohibited fields, and immutability. The preprocessing checks fit on training assignments,
then deliberately change held-out categories, distributions, missingness, and labels and
verify that learned parameters and the high-cost threshold do not change. They also verify
missingness indicators, unknown-category handling, exact target/cap preservation, no target
imputation or clipping, preprocessing-output immutability, and separation of fitted models.
The experiment tests change every held-out label and verify predictions and baseline
parameters remain identical while metrics change. They also verify the log1p experiment
inverts predictions with `expm1` before USD metrics. The audit independently recomputes all
metrics and reloads each checksum-verified model to require exact saved-prediction equality.
Formatting, lint, static type checking, tuning/model-selection, and web POC commands remain
unavailable.

## Regression policy

Every confirmed defect in target eligibility, cutoff logic, cost arithmetic, allocation,
privacy, artifact compatibility, or reported metrics should receive a focused regression test.
If a test is infeasible, document the manual evidence, reason, residual risk, and follow-up.
