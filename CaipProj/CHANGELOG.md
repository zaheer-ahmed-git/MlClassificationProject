# Changelog

All material changes to project scope, data and target contracts, architecture, security,
workflows, and user-visible behavior are recorded here. This file is not a Git log.

## [Unreleased]

### Changed

- GitHub publication adds this project as `CaipProj/` inside
  `zaheer-ahmed-git/MlClassificationProject`, leaving the existing classification
  files in place. Raw data, `DatasetOfCAIP/`, artifacts, and local environments
  stay gitignored.

### Added

- Minimal Streamlit decision-support demo (`scripts/streamlit_app.py`) with single-row
  inference via `src/caip_maintenance/app/` and `features/ahs_inference.py`. Loads
  `ahs-feature-engineering-v1` preprocessing and `ahs-xgboost-tuning-v1` artifacts;
  scores type median, prior cost, training median, and tuned XGBoost with high-cost flags.
  Dependencies in `requirements-app.txt`; tests in `tests/test_app_inference.py`.
- CAIP final submission package under `reports/submission/`: 7-page PDF report with
  charts (`caip_final_report.pdf`), code annex zip, separate examiner source
  `caip_final_source.py`, and email draft. The report frames the training corpus as
  built on the WAPDA residential data model and populated from mapped AHS public-use
  records; it does not present those rows as observed WAPDA invoices.
- Fixed AHS comparison `ahs-xgboost-v1`: frozen baselines plus `xgboost.XGBRegressor` on the
  audited preprocessing artifact, with `train-ahs-xgboost` / `audit-ahs-xgboost` CLI commands,
  contract tests, and `xgboost==2.0.3` in `requirements-modeling.txt`.
- Feature audit (`audit-ahs-features`), preprocessor `ahs-feature-engineering-v1`, and
  experiments `ahs-feature-engineering-v1`, `ahs-model-tuning-v1`, `ahs-robust-loss-v1`, and
  `ahs-feature-ablation-v1` implementing the next-steps modeling sequence.
- Fixed AHS comparison `ahs-baselines-models-log1p-v1`: same split, features, baselines, and
  estimators as `ahs-baselines-models-v1`, but fitted models train on `log1p(USD)` and all
  stored predictions/metrics use `expm1` back to original USD. Declarative config, schema,
  modeling-path support, tests, and `Documentation/AHSBaselineModelLog1pExperiment.md`.
- Shared agent guidance and explicit required/important/contextual file tiers.
- Target architecture for governed ingestion, cutoff-safe features, model evaluation, and a
  decision-support web POC.
- Contribution, coding, workflow, testing, review, and security policies.
- Conservative Cursor and Codex project configuration.
- Portable code-change verification and documentation-sync skills.
- Repository ignore and editor-consistency rules.
- Stakeholder-approved target, allocation, high-cost, privacy, and conflict adjudications in
  `Documentation/DatasetPolicy.md` and `Documentation/CodexFindings.md`.
- Initial standard-library package and CLI for public-source registration, acquisition,
  raw-integrity validation, RHFS harmonization, and release auditing.
- A 10-source governance register, complete 34-feature RHFS mapping, v0.1 machine-readable
  schema, thin build script, contract tests, and public-corpus dataset card.
- Local ignored release `public-corpus-v0.1.0-rhfs`: 4,425 authentic RHFS properties, 1,488
  eligible public annual-cost proxy labels, deterministic lineage, and 16 passing QA gates.
- Official AHS 2015–2023 artifact registration with 28 hash/size-pinned PUF and codebook
  files, plus a reproducible pre-adapter longitudinal gate.
- Separate local ignored release `public-corpus-v0.2.0-ahs` for
  `future_routine_cost_proxy_v1`: 36,623 linked units, 86,125 eligible adjacent-wave pairs,
  294,998 lineage records, and 21 passing release checks.
- AHS mapping/schema contracts, gate and adapter tests, and
  `Documentation/AHSGateDecision.md` documenting official linkage/cost semantics, the 2023
  response-cap change, eligibility, counts, and interpretation limits.
- Frozen `Documentation/AHSSemanticLicenseDecision.md`, separating approved local PUF
  analysis from the still-blocked redistribution of row-level source and derived artifacts.
- Declarative `ahs-grouped-temporal-v1` split/schema, CLI build and audit commands, and
  contract tests for grouping, terminal-wave cohorts, cap sensitivity, checksum pins,
  prohibited fields, and immutability.
- Local ignored AHS split assignment covering all 86,125 transitions: 10,103 units in
  training, 7,067 in validation, and 19,453 in test; all 16 split checks pass with zero unit
  leakage. The pre-2023-cap sensitivity view retains 66,672 rows without clipping targets.
- `Documentation/AHSPublicCorpusDatasetCard.md`, publishing the AHS source hashes, label and
  feature rules, table/lineage counts, frozen split, cap-sensitivity views, claim limits,
  distribution hold, and rebuild/audit commands.
- Declarative `ahs-baselines-models-v1` experiment and artifact schema, an exact pinned
  modeling environment, three training-only baselines, linear regression, Random Forest,
  histogram gradient boosting, aggregate metrics, manifests, and immutable artifact audits.
- Modeling regression tests for hand-calculated metrics, held-out-label perturbation,
  training-only fits, output drift, and exact predictions after checksum-verified reload.
- `Documentation/AHSBaselineModelExperiment.md` with exact baseline fallbacks, fixed model
  settings, primary and pre-2023-cap results, and public-proxy claim limits.
- Declarative `ahs-diagnostic-review-v1`, residual/subgroup/weight/utility review CLI, ten
  audit checks, and `Documentation/AHSDiagnosticReview.md`. Promotion and hyperparameter
  search remain unauthorized; type-median and prior-cost stay complementary references.
- Frozen `ahs-selection-policy-v1` (`Documentation/AHSSelectionPolicy.md` and
  `configs/selection/ahs_selection_policy_v1.toml`): validation MAE primary; sensitivity MAE
  and high-cost F1 required secondaries; fitted-model promotion only with validation win plus
  sensitivity guardrail. Applied outcome: no fitted-model promotion; report type-median and
  prior-cost.
- `reports/CAIPMethodsResults.md`, initially added with report-ready AHS methodology and
  aggregate results applying the frozen selection policy: type-median for cost-level
  reporting and prior cost for high-cost triage, with explicit public-proxy and
  no-WAPDA-validation boundaries. It is now expanded as recorded under Changed below.

### Changed

- Expanded `reports/CAIPMethodsResults.md` from methods/results material into a complete
  CAIP final-report draft with title-page placeholders, a 150–200-word abstract,
  introduction, reproducible workflow, discussion, conclusion, IEEE-style references, and
  submission notes. The frozen baseline-only AHS outcome remains unchanged and no modeling
  or evaluation was rerun.
- Documented that WASC seed evidence supports descriptive account-level analysis but is not
  sufficient for property-level supervised training from observed WAPDA work orders.
- Revised dataset strategy: because WAPDA operational extracts are blocked under privacy and
  authorization rules, train on a harmonized public multi-source corpus (>500 properties)
  with lineage, while keeping WASC files as private framing seed—not arbitrary invented labels
  and not claims that public labels are WAPDA outcomes.
- At the first-source construction checkpoint, moved repository status beyond
  dataset-construction planning; modeling, temporal forecasting, and the web POC were then
  unimplemented.
- Recorded the AHS gate as GO while preserving RHFS/AHS task isolation and
  `local-analysis-only` redistribution status; the NYC HPD fallback is not opened by this
  decision.
- Marked the AHS proxy release eligible for dataset-card and later task-specific baseline
  work after freezing its semantics and split; no preprocessing or model was introduced.
- At the dataset-card checkpoint, closed that gate and authorized training-fold-only
  preprocessing followed by baselines on `future_routine_cost_proxy_v1` alone; that
  documentation-only change did not itself add preprocessing or a model.
- Implemented `ahs-training-fold-v1` with training-only imputers, encoders, scalers,
  missingness-based value retention, explicit missingness indicators, and a training-only
  top-20% high-cost threshold. Original targets and response-cap metadata remain unclipped
  and unimputed; the artifact contains no model.
- Built and audited the local preprocessing artifact: 13,871 fit rows, 86,125 transformed
  rows, a USD 1,428 high-cost threshold, and all 11 preprocessing checks passing.
- Built and audited the local AHS baseline/model artifact over the same 86,125 rows and 205
  frozen features; all 11 experiment audit checks passed. No model was promoted and no
  WAPDA/WASC validation claim was made.

### Fixed

- Made the thin corpus script runnable from an uninstalled checkout and extended processed
  checksum auditing to flag missing manifest-listed files as drift.
- Corrected canonical documentation links after the files were organized under
  `Documentation/`.
- Replaced repeated release-audit set construction with precomputed key sets so the larger
  AHS lineage audit completes in linear passes rather than quadratic scans.
