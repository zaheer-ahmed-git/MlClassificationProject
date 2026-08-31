# Repository Agent Guide

## Repository overview

This repository is the planning and data-assessment workspace for a CAIP capstone:
predicting the next 12 months of maintenance cost for WAPDA staff-colony houses and
apartments. The intended deliverables are a leakage-safe machine-learning comparison,
an explainable decision-support web proof of concept, and a 5-8 page final report.

The repository is currently in the public-proxy experimentation phase. It contains a Python
data/modeling package, declarative registry/mapping/schema/experiment files, and contract
tests for separate RHFS and AHS releases. The AHS longitudinal volume, preprocessing, and
fixed baseline/model experiment gates passed. The experiment is local-only and no model was
selected or promoted; no application exists. Do not describe a validated WAPDA model,
promoted artifact, or application as implemented until each exists and is verified.

## Read first

Use the following order for substantial work:

1. `README.md` for status, file tiers, and navigation.
2. `Documentation/Projectproposal.md` for the approved problem framing.
3. `Documentation/CodexFindings.md` for evidence, conflicts, and collection strategy.
4. `Documentation/DatasetPolicy.md` for approved policies and hybrid dataset strategy.
5. `Documentation/DataStructureProposed.md` for candidate fields and minimum POC dataset.
6. `ARCHITECTURE.md` for target boundaries and dependency direction.
7. `WORKFLOWS.md`, `TESTING.md`, and `CODE_REVIEW.md` before implementation.

`CAIP_Final_Project_Instructions.pdf` is the authoritative submission brief.
`serverdetails.md` describes an unrelated clinical ResearchModule environment and is
not authoritative for this WAPDA project.

## Project invariants

- The prediction unit is one residential property at one historical cutoff.
- The primary target is eligible direct maintenance plus an approved allocation of
  shared-building maintenance during the following 12 months, in nominal PKR.
- Routine, corrective, and emergency building maintenance are eligible. Major
  renovation, reconstruction, land values, revenue, closing entries, and unrelated
  asset classes are excluded from the primary target.
- Features must be known on or before `as_of_date`. Fit imputers, encoders, scalers,
  thresholds, and models on training data only.
- Prefer fiscal-year snapshots: June 30 cutoff, followed by a July 1-June 30 label
  interval. Use time-based validation; do not randomly split overlapping property
  histories.
- A zero target is valid only when complete coverage proves no eligible maintenance.
  Missing coverage is not zero cost.
- Current WASC residential framing scope reconciles to 101 units in categories A-F
  with counts 1, 4, 16, 24, 16, and 40. Non-residential assets stay out.
- Shared building costs allocate equal per active unit; high-cost uses top 20% within
  each training fold; personal appliances are always excluded.
- WAPDA operational work-order/cost extracts are not currently available. Train on a
  harmonized public multi-source corpus (>500 properties) per `DatasetPolicy.md`.
  Do not invent undocumented labels, and do not present public-harmonized labels as
  observed WAPDA outcomes. Synthetic fixtures are for isolated application tests only.
- AHS 2015–2023 is an approved separate modeling view for
  `future_routine_cost_proxy_v1`: 36,623 distinct linked units and 86,125 eligible
  adjacent-wave pairs. Keep it separate from RHFS, preserve the 2023 response-cap marker,
  and keep redistribution `local-analysis-only` pending license review.
- The WASC ledger supports descriptive account-level analysis only. See
  `Documentation/CodexFindings.md`.

## Data and security rules

- Treat `DatasetOfCAIP/` as immutable raw source material. Never overwrite, normalize,
  or rename a source file in place.
- Raw documents may contain names, designations, employers, free-text remarks, invoice
  references, or other sensitive information. Do not copy these into tests, logs,
  examples, screenshots, reports, prompts, or analytical exports.
- Use anonymized property identifiers and tokenized contractor/invoice identifiers.
  Do not retain resident name, CNIC, telephone, salary, family details, or unredacted
  narration.
- Store lineage for every derived record. Preserve source locators, transformations,
  verification status, and unresolved conflicts.
- Keep secrets and machine-specific paths in ignored local files. Never commit `.env`
  files, credentials, raw data, processed row-level data, or trained artifacts that may
  disclose source records.

## Target architecture

Continue using the installable Python package under `src/caip_maintenance/`, tests under
`tests/`, declarative settings under `configs/`, and thin entry points under `scripts/`.
Keep ingestion, validation, feature generation,
modeling, evaluation, and application adapters separate. Domain and feature logic must
not depend on the web UI.

Follow `CODING-STANDARDS.md`. Add a dependency only when its role is documented and
the standard library or existing stack is insufficient. Keep random seeds, cutoff
dates, source hashes, feature lists, split definitions, metrics, and model parameters
with each experiment.

## Working rules

- Inspect existing files before changing them and keep edits narrowly scoped.
- Start with a written plan for multi-file code, schema, or target-definition changes.
- Preserve raw evidence and quarantine conflicts rather than silently choosing a value.
- Update tests and affected documentation with each behavior or contract change.
- Do not edit generated reports, figures, processed data, or model artifacts manually.
- Use the smallest relevant verification first, then broader checks for shared changes.
- Distinguish pre-existing failures from regressions and report both clearly.
- Do not add Cursor hooks, specialized agents, networked services, or deployment
  automation until the underlying workflow is stable and reviewable.

## Commands

The implemented data-slice commands, run from the repository root, are:

```bash
PYTHONPATH=src python3 -m caip_maintenance.data register-sources
PYTHONPATH=src python3 -m caip_maintenance.data validate-raw --source rhfs_2024
PYTHONPATH=src python3 -m caip_maintenance.data harmonize --release public-corpus-v0.1.0-rhfs
PYTHONPATH=src python3 -m caip_maintenance.data audit-release --release public-corpus-v0.1.0-rhfs
PYTHONPATH=src python3 -m caip_maintenance.data validate-raw --source ahs_2015_2023
PYTHONPATH=src python3 -m caip_maintenance.data assess-ahs
PYTHONPATH=src python3 -m caip_maintenance.data harmonize --release public-corpus-v0.2.0-ahs
PYTHONPATH=src python3 -m caip_maintenance.data audit-release --release public-corpus-v0.2.0-ahs
PYTHONPATH=src python3 -m caip_maintenance.data assign-splits --release public-corpus-v0.2.0-ahs --split ahs-grouped-temporal-v1
PYTHONPATH=src python3 -m caip_maintenance.data audit-split --release public-corpus-v0.2.0-ahs --split ahs-grouped-temporal-v1
PYTHONPATH=src python3 -m caip_maintenance.data preprocess-ahs --release public-corpus-v0.2.0-ahs --split ahs-grouped-temporal-v1 --preprocessor ahs-training-fold-v1
PYTHONPATH=src python3 -m caip_maintenance.data audit-preprocessing --release public-corpus-v0.2.0-ahs --split ahs-grouped-temporal-v1 --preprocessor ahs-training-fold-v1
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-modeling.txt
PYTHONPATH=src .venv/bin/python -m caip_maintenance.data train-ahs-experiment --release public-corpus-v0.2.0-ahs --split ahs-grouped-temporal-v1 --preprocessor ahs-training-fold-v1 --experiment ahs-baselines-models-v1
PYTHONPATH=src .venv/bin/python -m caip_maintenance.data audit-experiment --release public-corpus-v0.2.0-ahs --split ahs-grouped-temporal-v1 --preprocessor ahs-training-fold-v1 --experiment ahs-baselines-models-v1
PYTHONPATH=src .venv/bin/python -m caip_maintenance.data train-ahs-experiment --release public-corpus-v0.2.0-ahs --split ahs-grouped-temporal-v1 --preprocessor ahs-training-fold-v1 --experiment ahs-baselines-models-log1p-v1
PYTHONPATH=src .venv/bin/python -m caip_maintenance.data audit-experiment --release public-corpus-v0.2.0-ahs --split ahs-grouped-temporal-v1 --preprocessor ahs-training-fold-v1 --experiment ahs-baselines-models-log1p-v1
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m compileall -q src scripts tests
```

The harmonization command creates an immutable ignored release and therefore succeeds only
for a new release identifier. The experiment command runs the fixed AHS comparisons
(`ahs-baselines-models-v1` and `ahs-baselines-models-log1p-v1`);
no model-selection, promoted-model, standalone evaluation, or application command exists yet.

Never invent a passing command or test result.

## Definition of done

- The requested behavior or documentation is complete and consistent with the target
  and privacy contracts.
- Relevant checks have been run and their results reported.
- No future information, raw PII, or undocumented invented labels entered an analytical
  surface; public-harmonized labels carry lineage and origin flags.
- Source files remain unchanged and derived outputs are reproducible from documented
  inputs.
- Architecture, testing, workflow, security, and changelog documents are updated when
  their contracts change.
- The final diff or changed-file set has been reviewed for correctness, leakage,
  security, scope, and missing tests.
