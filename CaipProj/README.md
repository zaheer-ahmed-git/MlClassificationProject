# WAPDA Staff-Colony Maintenance Cost Prediction

This CAIP capstone is a public-sector decision-support project that aims to estimate
the maintenance cost of an individual WAPDA staff-colony house or apartment during the
next 12 months. The intended system compares transparent baselines and classical
machine-learning regressors, identifies likely high-cost properties, and exposes the
result through an explainable web proof of concept for budgeting and prioritization.

On GitHub this project lives as the `CaipProj/` folder inside
`zaheer-ahmed-git/MlClassificationProject`. Raw sources, processed tables, and
trained artifacts stay on the workstation.

## Current status

The project is in **public-proxy experimentation**, not WAPDA model validation.
WASC seed files establish a 101-unit residential inventory and an account-level ledger, but
most costs are not linked to properties or completed work orders. WAPDA operational extracts
(work orders, invoices, linked costs) are **not currently available** under privacy and
authorization rules.

Approved training path: build a **harmonized public multi-source corpus** (>500 properties)
aligned to the project schema, while keeping WASC material as private seed evidence for
framing and descriptive analysis. See `Documentation/CodexFindings.md` and
`Documentation/DatasetPolicy.md`. Do not treat ledger debits as property-level labels, and
do not present public-harmonized labels as observed WAPDA outcomes.

The first implemented slice, `public-corpus-v0.1.0-rhfs`, uses the official 2024 RHFS
public-use release. It contains 4,425 authentic rental-property records and 1,488 usable
annual maintenance-and-repair labels after documented eligibility checks. All 18 release
audits pass. This slice is a cross-sectional U.S. annual-cost proxy, not the final
multi-source corpus or a future WAPDA forecasting dataset. See
`Documentation/PublicCorpusDatasetCard.md`.

The AHS longitudinal gate also passed. Official 2015–2023 national PUFs yield 36,623
distinct linked housing units and 86,125 eligible adjacent-wave feature-to-label pairs.
The separate local release `public-corpus-v0.2.0-ahs` implements
`future_routine_cost_proxy_v1`; all 21 release audits pass. It is a biennial U.S. survey
proxy, not an observed WAPDA outcome, and it is never stacked with the RHFS label. See
`Documentation/AHSGateDecision.md`. Its frozen semantics, lineage, and
`ahs-grouped-temporal-v1` assignment are published in
`Documentation/AHSPublicCorpusDatasetCard.md`. The fixed AHS-only comparison
`ahs-baselines-models-v1` evaluates three documented baselines, linear regression,
Random Forest, and gradient boosting against the audited preprocessing artifact. Its
independent artifact audit passes all 11 checks. A second fixed comparison,
`ahs-baselines-models-log1p-v1`, uses the same split and estimators with models trained on
`log1p` of the USD label and scored after `expm1` in original USD; see
`Documentation/AHSBaselineModelLog1pExperiment.md`. Neither run promotes a final model.
The complete final-report draft applies `ahs-selection-policy-v1` to the raw-target run:
`type_median` is the primary cost estimator and `prior_cost` is the high-cost reference,
with no WAPDA/WASC validation claim. See `reports/CAIPMethodsResults.md`.

## CAIP alignment

- **Applied AI:** property-level cost forecasting and prioritization.
- **Two capability areas:** machine learning plus responsible AI/data governance. A minimal
  Streamlit decision-support demo exists; it loads audited local artifacts only and does
  not claim a validated WAPDA deployment.
- **Real dataset:** WASC seed inventory/ledger for framing, plus a harmonized corpus built
  from multiple real public maintenance/housing sources (not invented labels).
- **Evaluation:** MAE, RMSE, and high-cost identification, with subgroup analysis where
  sample size permits.
- **Industry/governance relevance:** maintenance budgeting, preventive action, procurement
  planning, and accountable prioritization.
- **Required submission:** a 5-8 page PDF report, code annex, and separate Python source
  file as described in `CAIP_Final_Project_Instructions.pdf`.

## Project file tiers

The repository follows the separation recommended in
`codex_cursor_english_translation.pdf`: shared instructions at the center, tool-specific
configuration at the edges, and contextual evidence loaded only when relevant.

### Required and tool-native

| Path | Role |
|---|---|
| `AGENTS.md` | Canonical, durable instructions shared by coding agents. |
| `.cursor/rules/core.mdc` | Small always-on Cursor rule that points back to `AGENTS.md`. |
| `.codex/config.toml` | Conservative project-level Codex permissions and context settings. |
| `.cursorignore` | Prevents Cursor access to secrets and raw sensitive material. |
| `.cursorindexingignore` | Excludes binary sources and generated outputs from indexing. |
| `.agents/skills/*/SKILL.md` | Portable workflows, currently verification and documentation sync. |

### Important and versioned

| Path | Role |
|---|---|
| `Documentation/Projectproposal.md` | Canonical problem statement and intended deliverable. |
| `Documentation/CodexFindings.md` | Source audit, sufficiency, conflicts, and approved collection strategy. |
| `Documentation/DatasetPolicy.md` | Dataset strategy, approved policies, and build plan. |
| `Documentation/DataStructureProposed.md` | Candidate data dictionary and minimum POC fields. |
| `Documentation/AHSGateDecision.md` | Evidence and counts for the completed AHS longitudinal gate. |
| `Documentation/AHSSemanticLicenseDecision.md` | Frozen AHS outcome semantics, claim limits, and distribution hold. |
| `Documentation/AHSPublicCorpusDatasetCard.md` | Canonical AHS release, lineage, split, use, and fidelity documentation. |
| `Documentation/AHSSelectionPolicy.md` | Frozen AHS reporting and promotion policy. |
| `reports/CAIPMethodsResults.md` | Working markdown report draft; prefer the PDF under `reports/submission/`. |
| `reports/submission/caip_final_report.pdf` | Formatted CAIP final report (text, charts, analysis). |
| `reports/submission/wapda_project_walkthrough.pdf` | Plain-language full project journey (data prep through Phase~2). |
| `reports/submission/caip_code_annex.zip` | Code annex for email submission (no raw data). |
| `reports/submission/caip_final_source.py` | Separate Python source for examiner testing. |
| `reports/submission/README.md` | Submission package notes and email checklist. |
| `ARCHITECTURE.md` | Target system boundaries, flows, and dependency rules. |
| `CONTRIBUTING.md` | Contribution and review expectations. |
| `CODING-STANDARDS.md` | Python, data, and ML implementation conventions. |
| `WORKFLOWS.md` | Repeated project procedures. |
| `TESTING.md` | Data, model, application, and documentation verification strategy. |
| `CODE_REVIEW.md` | Risk-focused review checklist. |
| `SECURITY.md` | Privacy, secrets, source-data, and reporting policy. |
| `CHANGELOG.md` | Human-readable history of material repository changes. |

### Contextual and load on demand

| Path | Role |
|---|---|
| `CAIP_Final_Project_Instructions.pdf` | Authoritative course and submission requirements. |
| `codex_cursor_english_translation.pdf` | Repository and agent-configuration guidance. |
| `Documentation/ProjectDomain.md` | Earlier domain comparison and selection rationale. |
| `DatasetOfCAIP/` | Immutable raw evidence; restricted because some files contain PII. |
| `Documentation/serverdetails.md` | Legacy notes for an unrelated clinical ResearchModule; not applicable here. |

### Deferred intentionally

`CODEOWNERS` is present but inactive until a real GitHub user or team is known. A
`LICENSE` must wait for an explicit ownership and redistribution decision because the
repository includes non-public WAPDA material. `CITATION.cff` must wait for the authors'
names and preferred citation. `PLANS.md`, an agent-skill catalog, Cursor hooks, and
specialized agents should be added only when the corresponding workflow is real and
stable.

## Prediction contract

The model-ready grain is one property at one historical cutoff. The recommended cutoff is
June 30, with a July 1 through June 30 label period.

```text
maintenance_cost_next_12_months_pkr
  = eligible direct routine/corrective/emergency maintenance
  + approved share of eligible building-level maintenance
```

Major renovations and reconstruction remain separate. Land values, revenue, closing
entries, unreconciled advances, and non-residential assets are excluded. Features must be
available by the cutoff date, and all learned preprocessing must be fitted inside the
training fold.

## Data readiness gate

Target and allocation policies for the WASC framing inventory are approved
(equal-per-active-unit shared costs; major renovation by cost/scope/time/approval type;
high-cost = top 20% within each training fold). The AHS source, linkage, sample-volume,
mapping, lineage, future-proxy, split, dataset-card, preprocessing, fixed-comparison,
diagnostic-review, selection-policy, and reporting gates are now met.
The AHS reporting decision is integrated into the complete report draft at
`reports/CAIPMethodsResults.md`. The formatted submission package is under
`reports/submission/`:

1. Email `caip_final_report.pdf`, `caip_code_annex.zip`, and `caip_final_source.py`
   to lab.tech@ncai.nust.edu.pk (CC rmeo@ncai.nust.edu.pk) with subject
   `CAIP Final Project Batch 8` by 25 August 2026, 23:59. Use
   `reports/submission/EMAIL_DRAFT.txt` and confirm the author name on the PDF
   title page before sending.
2. Do not attach raw WASC documents, AHS microdata, processed row-level tables,
   secrets, or trained model weights.
3. If separately authorized, add a short RHFS baseline table as a distinct, unmerged
   estimation view with its different outcome scope.
4. Under `ahs-selection-policy-v1`, report type-median for cost-level MAE and
   prior-cost for high-cost triage. Among fitted squared-error models on the
   primary test, validation-tuned XGBoost is the strongest balanced system; do
   not present absolute-loss MAE leaders as operational winners when high-cost
   F1 collapses.

The frozen split assigns all transitions for one tokenized unit together, based on that
unit's terminal eligible label wave: 10,103 units / 13,871 rows in training; 7,067 units /
15,400 rows in validation; and 19,453 units / 56,854 rows in test. All 16 split audits pass
with zero unit leakage. The primary view keeps all 86,125 labels without clipping; the
pre-2023-cap sensitivity view keeps 66,672 and excludes the 19,453 labels from 2023.

`ahs-training-fold-v1` fits its imputers, category vocabulary, scalers, feature-retention
rule, and USD 1,428 high-cost threshold on the 13,871 training rows only. It then transforms
all 86,125 rows, retains explicit missingness indicators, preserves the original target and
response-cap metadata without target imputation or clipping, and passes all 11 preprocessing
audits. The preprocessing artifact records `model_fitted=false`; fitted estimators live only
in the separate, ignored experiment artifact.

`ahs-baselines-models-v1` fits all baseline summaries and models on training rows only,
uses the frozen USD 1,428 threshold, and evaluates MAE, RMSE, precision, recall, and F1 on
validation/test primary and pre-2023-cap views. Later runs add feature engineering,
validation-only tuning, robust-loss checks, and XGBoost. Under the frozen selection
policy, type median remains the primary cost estimator and prior cost the high-cost
reference; among fitted squared-error models, validation-tuned XGBoost is strongest on
the primary-test MAE/RMSE/F1 balance.

The AHS GO decision satisfies the requested >500-unit future-proxy volume gate; it does
not authorize a CAIP final model or convert the proxy into the exact WAPDA target.

Arbitrary invented labels without public-source lineage remain prohibited. Harmonizing real
public datasets into the project schema is the approved path. Small synthetic rows may be used
only in isolated UI tests and must be stored separately from analytical data.

## Repository layout

The source registry, RHFS and AHS adapters, task-specific schemas, release/split audits,
AHS training-fold-only preprocessing, a fixed AHS-only baseline/model comparison, tests,
and thin CLI entry point now exist. A minimal Streamlit inference demo lives under
`scripts/streamlit_app.py`. Model promotion and a production web deployment remain planned.

```text
configs/                    declarative ingestion, feature, and experiment settings
data/                       ignored raw/interim/processed data layers
src/caip_maintenance/
  data/                     source adapters, normalization, lineage, validation
  domain/                   target eligibility, allocation, and controlled values
  features/                 cutoff-safe snapshots, labels, and fitted preprocessing
  modeling/                 baselines, regressors, persistence, explanations
  evaluation/               temporal splits, metrics, subgroup analysis
  app/                      thin decision-support web adapter
tests/                      unit, integration, leakage, and UI tests
scripts/                    thin reproducible entry points
reports/                    report source, approved aggregate tables, and figures
artifacts/                  generated experiments and models; ignored by default
```

The supplied `DatasetOfCAIP/` directory remains an immutable source inbox until a governed
ingestion workflow copies approved, hashed inputs into the data layers.

## Working with the repository

The data package uses Python 3.11+. The modeling command additionally uses the exact pinned
packages in `requirements-modeling.txt`. From the repository root:

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
.venv/bin/python -m pip install -r requirements-app.txt
PYTHONPATH=src .venv/bin/streamlit run scripts/streamlit_app.py
```

The same data commands are available before installation through
`python3 scripts/build_public_corpus.py COMMAND [OPTIONS]`.

`harmonize` refuses to overwrite an existing release. Raw and processed row-level files are
gitignored. For current work:

1. Read `AGENTS.md` and the documents relevant to the task.
2. Do not mutate files in `DatasetOfCAIP/`.
3. Keep derived row-level data and PII out of version control.
4. Record source hashes, locators, transformations, and unresolved conflicts.
5. Run the source, contract, release-audit, and documentation checks described in `TESTING.md`.

## Documentation map

- `ARCHITECTURE.md`: system view and target module contracts
- `CONTRIBUTING.md`: change process and required evidence
- `CODING-STANDARDS.md`: implementation conventions
- `WORKFLOWS.md`: data, model, application, and report procedures
- `TESTING.md`: verification strategy and quality gates
- `CODE_REVIEW.md`: review checklist
- `SECURITY.md`: privacy and security policy
- `Documentation/PublicCorpusDatasetCard.md`: RHFS release card
- `Documentation/AHSPublicCorpusDatasetCard.md`: AHS release and frozen split card
- `Documentation/AHSBaselineModelExperiment.md`: fixed AHS proxy comparison and metrics
- `Documentation/AHSBaselineModelLog1pExperiment.md`: same systems with log1p target / USD metrics
- `Documentation/AHSDiagnosticReview.md`: residual/subgroup/weight/utility review; no promotion
- `Documentation/AHSSelectionPolicy.md`: frozen validation-MAE selection rule and fallback reporting
- `reports/CAIPMethodsResults.md`: complete CAIP report draft with the frozen AHS outcome

No open-source license is granted by this repository at present.
