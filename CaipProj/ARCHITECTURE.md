# Architecture

## Overview

The target is a small, reproducible analytical system for forecasting the next 12 months
of eligible maintenance expenditure for WAPDA residential properties. It has two product
surfaces:

1. A machine-learning and evaluation pipeline that produces traceable experiments.
2. A decision-support web proof of concept that reads approved artifacts and presents
   estimates, uncertainty or risk, and the main contributing factors.

The current repository implements source/governance and canonical-snapshot slices for two
separate tasks under `src/caip_maintenance/data/`: RHFS annual held-out estimation and AHS
longitudinal future routine-cost proxying. Split assignment is implemented for AHS;
its release and split contract are published in a dataset card. Training-fold-only AHS
preprocessing and one fixed, untuned AHS-only baseline/model comparison are implemented and
audited. An AHS diagnostic review of residuals, subgroups, survey weights, and decision
utility is also implemented; it does not promote a model. A frozen selection policy
(`ahs-selection-policy-v1`) names validation MAE as the primary objective and denies fitted-
model promotion from the current comparison, reporting `type_median` and `prior_cost`
instead. Application binding and reporting automation remain target architecture. A minimal
Streamlit inference demo (`scripts/streamlit_app.py`) loads audited local artifacts for
decision-support what-if scoring; it is not a promoted production deployment.

## System boundaries

### In scope

- Houses and apartments in the approved WASC residential framing inventory (101 units).
- A harmonized public multi-source training corpus designed to match the same prediction
  grain and target contract when WAPDA operational extracts are unavailable.
- Routine, corrective, and emergency building maintenance.
- Equal-per-active-unit allocations of shared apartment-building costs.
- Property attributes, cutoff-safe history, condition, complaints, occupancy aggregates,
  economic indices, and weather context when coverage permits.
- Historical baselines, linear regression, Random Forest, and a gradient-boosting model.
- Temporal evaluation, high-cost ranking, explanations, and aggregate budget views.

### Out of scope for the primary model

- Academic, hostel, office, hospital, mosque, recreation, rest house, mini-WAPDA-house,
  complex, and revenue-generating assets.
- Land acquisition, book values, rent, and revenue.
- Complete reconstruction and major capital renovation in the primary label.
- Personal resident prediction or employee performance decisions.
- Autonomous approval of budgets, procurement, or maintenance work.
- Training on invented maintenance histories that lack documented public-source (or later
  authorized WAPDA) lineage, or presenting public-harmonized labels as observed WAPDA outcomes.

## Architectural layers

### 1. Source and governance layer

Raw WAPDA/WASC documents are immutable seed evidence. Public training extracts land in a
separate immutable raw area. Each ingested source receives a hash, coverage dates, PII flag,
authority rank, and ingestion timestamp. Record-level lineage links every normalized
assertion back to a source locator and records extraction method, confidence, and
verification status.

Conflicting values are quarantined for review. They are not resolved silently. Adjudicated
and open WASC conflicts are documented in `Documentation/CodexFindings.md`. Dataset
construction rules live in `Documentation/DatasetPolicy.md`.

Implemented now: a 10-source TOML register; approved RHFS and AHS artifact manifests with
expected hashes and sizes; deterministic native-key tokenization; immutable raw/release
directories; row-to-document lineage; a frozen AHS semantic decision; and an immutable,
unit-grouped temporal assignment. `Documentation/AHSPublicCorpusDatasetCard.md` publishes
the aggregate release, lineage, split, use, and fidelity contract. AHS passed its
official-field, linkage, sample-volume, documentation, and split-isolation gates but remains
local-analysis-only pending redistribution approval. The other eight entries remain
candidates and cannot contribute rows until their access, field, license, and quality gates
pass.

### 2. Canonical data layer

Normalized relational entities represent sites, buildings, property units, components,
occupancy periods, inspections, complaints, work orders, cost lines, renovation events,
ledger transactions, reconciliations, and shared-cost allocations. Controlled values and
eligibility decisions belong to domain code, not notebook cells or UI code.

The detailed proposed schema is in `Documentation/CodexFindings.md`.
`Documentation/DataStructureProposed.md` remains the candidate feature dictionary and
minimum-data reference. `Documentation/DatasetPolicy.md` is the approved construction
strategy under current access constraints.

The v0.1 RHFS and v0.2 AHS slices implement `source_document`, `source_asset_bridge`,
`annual_cost_observation`, `property_period_snapshot`, `property_period_label`, and
`record_lineage` as deterministic CSV tables governed by task-specific schemas. AHS uses
`configs/schemas/public_corpus_v0.2_ahs.json`; its earlier-wave features and later-wave
labels remain semantically isolated from RHFS. Its separate `split_assignment` is governed
by `configs/schemas/ahs_split_assignment_v1.json` and `configs/splits/ahs_grouped_temporal_v1.toml`.
The remaining canonical entities are planned.

### 3. Snapshot and label layer

Feature generation is intended to create one `property_period_snapshot` per property and cutoff. Every
feature carries an effective time and must use only information available on or before the
cutoff. Label generation creates the following 12-month eligible cost from verified work
orders and approved shared allocations.

The current RHFS adapter emits same-source snapshots and labels but explicitly marks the task
as `cross_sectional_held_out_estimation`; it does not satisfy the future-window contract.
The AHS adapter emits exact-`CONTROL` adjacent-wave pairs for
`future_routine_cost_proxy_v1`, with tokenized unit identity, later-wave ordering, response-cap
metadata, and source lineage. It is a biennial self-reported proxy rather than the exact
12-month WAPDA target. The frozen split assigns all of a unit's transitions together by its
terminal eligible label wave and provides primary/all-wave and pre-2023-cap sensitivity
flags without target clipping.

### 4. Modeling and evaluation layer

Models must consume the same versioned snapshot contract and split definition.
`ahs-training-fold-v1` implements the preprocessing boundary for the AHS task: imputation,
category-vocabulary learning, scaling, missingness-based value retention, and the high-cost
threshold fit on training assignments only. It preserves original targets and response-cap
metadata without clipping or target imputation. The preprocessing artifact explicitly
records that no model is fitted. `ahs-baselines-models-v1` consumes this frozen contract in
a separate local artifact and fits three baselines, linear regression, Random Forest, and
histogram gradient boosting on training rows only. Validation/test labels are metrics-only;
the experiment audit verifies this boundary, stored checksums, model reload predictions,
both cap views, and the fixed USD 1,428 threshold. `ahs-baselines-models-log1p-v1` uses the
same split, features, baselines, and estimators, but fits the three regressors on
`log1p(USD)` and stores/evaluates `expm1` predictions in original USD.

The modeling module currently owns the fixed comparison and its evaluation calculations;
a broader evaluation layer remains planned. Its contract includes:

- Historical and group-average baselines.
- Linear regression, Random Forest, and gradient boosting.
- MAE and RMSE in the task's declared nominal currency (USD for AHS; PKR for an eventual
  exact WAPDA task).
- Precision/recall or retrieval at an approved high-cost budget or top-k.
- Breakdowns by property type, age group, cost band, and colony when statistically honest.
- Prediction residuals, uncertainty where supported, and explanation stability.

No model is promoted merely for having the lowest aggregate error. It must also pass data
coverage, leakage, subgroup, and decision-utility checks.

### 5. Application layer

The web POC is a thin adapter. It loads a versioned, approved model bundle and feature
schema; it does not train models or contain target logic. A user can select an anonymized
property, view relevant non-personal attributes, request an estimate, see the risk category
and main drivers, and inspect aggregate colony summaries.

The application must display the model version, prediction cutoff, data-coverage status,
and a decision-support disclaimer. It must not expose resident details or raw narrations.

### 6. Reporting layer

The CAIP report is generated from approved aggregate experiment outputs. Tables and figures
must trace to an experiment manifest and must not be edited to disagree with recorded
metrics. The report distinguishes observed results, assumptions, limitations, and proposed
future work.

## Main flows

```text
immutable source documents
  -> source registry and PII-aware extraction
  -> normalized entities plus lineage
  -> validation and reconciliation
  -> cutoff-safe snapshots and complete labels
  -> temporal model comparison
  -> reviewed model bundle and aggregate metrics
  -> web POC and CAIP report
```

Prediction flow:

```text
approved property snapshot
  -> stored preprocessing pipeline
  -> stored model
  -> nominal PKR estimate and optional interval/risk
  -> explanation mapped to human-readable feature names
  -> audit-safe UI response
```

## Dependency rules

- `domain` has no dependency on data-source adapters, model libraries, or the UI.
- `data` may depend on `domain` contracts and controlled values.
- `features` depends on canonical data contracts and domain target rules.
- `modeling` and `evaluation` depend on feature contracts, never on raw document formats.
- `app` depends on public prediction and artifact-loading interfaces, not training internals.
- `scripts` are thin orchestration entry points; business logic stays in the package.
- Notebooks, if used for exploration, are disposable clients of package code and never the
  only home of a transformation or reported result.

## Physical layout

```text
src/caip_maintenance/
  domain/       controlled values, target eligibility, allocation policy
  data/         implemented registry, RHFS/AHS normalization and gate, lineage, validation, audit
  features/     snapshot, label, and AHS preprocessing construction
  modeling/     pipelines, baselines, training, artifact bundle
  evaluation/   splits, metrics, subgroup and error analysis
  app/          presentation adapter and view models
configs/        source manifests, mappings, experiment settings
scripts/        CLI entry points that call package APIs
tests/          unit, integration, leakage, contract, and UI tests
reports/        report source and approved aggregate outputs
```

## Persistence and artifacts

Row-level raw, interim, and processed data remain outside version control. Versioned code
and small schemas/configuration describe how to recreate them. Each experiment artifact
includes:

- Source hashes and dataset version.
- Cutoff and coverage policy.
- Feature schema and target policy version.
- Train/validation/test intervals and optional group holdouts.
- Random seeds and package versions.
- Preprocessing and model parameters.
- Aggregate metrics and subgroup counts.
- Creation timestamp and code revision when Git becomes available.

Only approved aggregate, non-identifying tables and figures may enter the report tree.

## Structural decisions

1. **Decision support, not automation.** Engineering and budget owners retain authority.
2. **Property-period regression first.** NLP and deep learning are deferred unless data and
   the CAIP module requirement justify them.
3. **Time-based evaluation.** Random row splits are prohibited for overlapping histories.
4. **Verified actual cost as label.** Ledger account membership alone is insufficient.
5. **Explicit shared-cost policy.** Allocation must be approved, reproducible, and auditable.
6. **Nominal output.** Inflation-adjusted values may be features or model copies, while user
   estimates remain nominal PKR.
7. **Simple deployment.** Choose the smallest web stack that meets the POC once the model
   interface is stable; do not bind domain logic to that framework.

## Sensitive areas

Target eligibility, zero-versus-missing coverage, shared-cost allocation, date cutoffs,
resident de-identification, and experiment splitting have the highest correctness and privacy
risk. Changes to these areas require tests, a review against `CODE_REVIEW.md`, and updates
to the affected data or target documentation.
