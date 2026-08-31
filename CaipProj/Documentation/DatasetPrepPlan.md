# Hybrid Public-Dataset Construction Plan

## 1. Empirical contract

Build a versioned, lineage-preserving corpus of real public records representing at least 500 distinct residential properties or dwellings. Harmonization will mean:

- Vertically stacking compatible, authentic property-period observations.
- Deterministically joining contextual data using valid property, geography, and time keys.
- Maintaining separate modeling views when outcomes measure different concepts.
- Never generating labels, cloning aggregate buildings into fictional units, or randomly attaching features from one property to another.
- Keeping the 101-unit WASC inventory as a separate deployment-reference layer. Public outcomes will be described as public-data estimates or proxies, never observed WAPDA results.

Use two label-fidelity tiers:

1. **Primary public outcome:** real annual maintenance-and-repair expenditure attached to the same public property record.
2. **Transfer and auxiliary outcomes:** longitudinal routine-cost proxies or narrower emergency/enforcement costs, clearly identified by scope.

The intended WASC target remains next-12-month eligible maintenance cost in nominal PKR. No public outcome will be called an exact match unless its period, property grain, appliance exclusion, capital exclusion, and coverage all satisfy that contract.

## 2. Public-source shortlist and permitted roles

Score every candidate from 0–100: label fidelity 30%, property-grain compatibility 20%, temporal suitability 15%, feature breadth 10%, sample size 10%, access/licensing 10%, and geographic relevance 5%. Require at least 70 for a label-bearing source and 55 for a reference source.

| Source | Role in corpus | Relevant evidence | Restrictions |
|---|---|---|---|
| 2024 Rental Housing Finance Survey | Core annual-cost task | Property characteristics, units, income, expenses, and 2023 maintenance-and-repair expense; the survey completed 4,425 properties. [RHFS methodology](https://www.census.gov/programs-surveys/rhfs/technical-documentation/methodology.2024.html), [item booklet](https://www2.census.gov/programs-surveys/rhfs/technical-documentation/glossary/2024/2024-RHFS-Items-Booklet.pdf) | Cross-sectional; expenditure is not a future forecast; appliance separability must be verified and otherwise marked as a proxy. |
| American Housing Survey, 2015–2023 | Longitudinal forecast-proxy task | Repeated housing-unit observations, building and condition features, and routine-maintenance-cost responses. [AHS methodology](https://www.census.gov/programs-surveys/ahs/about/methodology.html), [2023 PUF](https://www.census.gov/programs-surveys/ahs/data/2023/ahs-2023-public-use-file--puf-/ahs-2023-national-public-use-file--puf-.html) | Biennial “typical year” cost is not an exact next-12-month ledger. Account for the 2023 response-cap change documented in [historical changes](https://www2.census.gov/programs-surveys/ahs/2023/2023%20AHS%20Historical%20Changes.pdf). |
| Pakistan HIES | Pakistan context and transfer benchmark | Dwelling, household, regional, and minor-repair expenditure information. [PBS HIES manual](https://www.pbs.gov.pk/wp-content/uploads/2020/07/Manual-of-Instruction-HIES-2024-25.pdf) | Household consumption grain; cannot serve as a WASC property-level forecast label. |
| English Housing Survey | Condition-feature reference and external validation | Detailed physical condition, dwelling, and repair-need information. [Official dataset guidance](https://www.gov.uk/guidance/english-housing-survey-datasets-and-bespoke-analysis) | Registration-gated; modeled repair need cannot be represented as observed maintenance spending. |
| NYC HPD Charges | Auxiliary future emergency-cost task | Real enforcement/emergency repair charges attached to buildings. [HPD Charges documentation](https://data.cityofnewyork.us/api/views/cp6j-7bjj/files/76d14575-c1a4-41e6-9628-ba3c525beb16?download=true&filename=HPD+Charge+Open+Data.pdf) | Covers government intervention, not total private maintenance. |
| NYC HPD Complaints | Prior-event predictors for HPD task | Complaint type, status, building, and dates. [NYC complaints data](https://data.cityofnewyork.us/Housing-Development/Complaints-since-08-01-2015/hy7d-p4qz) | Join only through verified NYC building identifiers and only for dates on or before cutoff. |
| NYC HPD Violations | Prior-condition predictors for HPD task | Violation class, status, dates, and building linkage. [NYC violations data](https://data.cityofnewyork.us/Housing-Development/Housing-Violations/xrru-zj8y) | A violation is a condition/event feature, not a cost label. |
| NYC PLUTO | Building attributes for HPD task | Building age, land use, area, units, and geography. [PLUTO data dictionary](https://data.cityofnewyork.us/api/views/64uk-42ks/files/0a20c848-4af5-417a-b0b9-c136e15b807f?download=true&filename=pluto_datadictionary.pdf) | Preserve vintage and join-key confidence; quarantine ambiguous parcel/building mappings. |
| NASA POWER | Weather context | Reproducible historical daily weather from 1981 onward. [NASA POWER API](https://power.larc.nasa.gov/docs/services/api/temporal/daily/) | Use only trailing weather known by the cutoff; retain downloaded snapshots because upstream archives can change. |
| World Bank WDI | Economic normalization | CPI, purchasing-power parity, and exchange-rate series. [WDI API](https://datahelpdesk.worldbank.org/knowledgebase/articles/889392), [PPP indicator](https://data.worldbank.org/indicator/PA.NUS.PPP) | Conversions are analytical normalization, not observed PKR expenditures. |

If a gated source cannot be lawfully acquired or redistributed, retain its assessment in the source register but exclude its rows. At least five approved sources must remain, including one label-bearing source.

## 3. Dataset structure and interfaces

### Canonical tables

| Table | Principal fields and types | Purpose |
|---|---|---|
| `public_source_register` | `source_id:string PK`, title, publisher, release, URLs, access class, license, geography, native grain, approved role, label fidelity, redistribution flag | Source governance and eligibility |
| `source_document` | `document_id:uuid PK`, `source_id FK`, path, SHA-256, byte size, MIME type, retrieval timestamp, release | Immutable raw-file inventory |
| `record_lineage` | `lineage_id:uuid PK`, target table/key, document FK, source-row locator/hash, source fields JSON, transform version, verification status | Row-level provenance |
| `coverage_period` | source/entity, start/end dates, completeness, zero semantics | Determines whether zero outcomes are valid |
| `data_conflict` | entity, field, competing values JSON, status, resolution | Quarantines unresolved discrepancies |
| `site` | site ID, anonymized geography, area, latitude/longitude precision class | Physical hierarchy |
| `building` | building ID, site FK, type, construction year, floor area, unit count | Building-level assets |
| `property_unit` | unit ID, building FK, category/type, occupancy attributes | Dwelling-level assets where the source genuinely identifies units |
| `source_asset_bridge` | source ID, hashed native asset ID, native grain, analytical asset ID, physical IDs, survey weight | Prevents invented hierarchy and records source-specific identity |
| `occupancy_period` | asset ID, start/end, status, active-unit indicator | Cutoff-safe occupancy |
| `property_inspection` | asset ID, inspection date, component, condition, defect severity | Condition evidence |
| `complaint` / `violation` | asset ID, event date, category, severity/status, closure date | Prior operational predictors |
| `work_order_cost_line` | asset ID, event ID, date, local amount, currency, cost category, eligibility flags | Eligible itemized cost where available |
| `annual_cost_observation` | asset ID, period, local amount/currency, observed-versus-modeled status, capital/appliance separability, scope fidelity, coverage and zero-valid flags | Normalized real source outcomes |
| `weather_site_month` | geography key, month, temperature, precipitation, heating/cooling indicators | Trailing weather |
| `economic_index_year` | country, year, CPI, PPP factor, exchange rate, release | Currency and price normalization |
| `property_period_snapshot` | snapshot ID, asset ID/grain/source, cutoff, structural, condition, occupancy, trailing-event, weather, economic, missingness, and support flags | Leakage-safe feature row |
| `property_period_label` | snapshot FK, task ID, label window, original amount, normalized amount, PKR scenario equivalent, completeness, censor reason, origin, fidelity | Task-specific target |
| `split_assignment` | task, snapshot, asset group, split/fold, threshold version | Reproducible evaluation |

Relationships must enforce `source → document → lineage`, `site → building → genuine unit`, and `asset → snapshots → task labels`. Every modeling row must map to exactly one authentic native source asset. Survey weights are stored as weights and never expanded through row replication.

### Modeling views

1. `annual_cost_estimation_v1`
   - RHFS property records and reported 2023 annual maintenance-and-repair expenditure.
   - Used for held-out cost estimation, not claimed as temporal forecasting.
   - Exclude capital expenditure; mark appliance scope as unseparated unless the codebook proves otherwise.

2. `future_routine_cost_proxy_v1`
   - AHS earlier-wave features linked to the same housing unit’s later-wave routine-maintenance response.
   - Group all waves from one housing unit into the same split.
   - Label explicitly as a biennial future routine-cost proxy.

3. `future_emergency_charge_v1`
   - NYC building snapshot at June 30 with prior complaints, violations, PLUTO attributes, and trailing weather.
   - Label from HPD charges during the following July–June period.
   - A zero means no recorded HPD charge under complete dataset coverage, not no total maintenance.

4. `wasc_scenario_scoring_v1`
   - Separate, unlabeled WASC reference inventory.
   - Preserve the 101-unit A–F scope, H-8/1 area of 10.73 acres, aggregate C–F floor totals, and separate G-8/2 lifecycle dates.
   - Do not distribute aggregate values across fictional units. If verified unit-level attributes are absent, retain category-level records and counts only.

### Implementation interface

The initial package, declarative source/mapping/schema files, thin build script, and tests are
implemented. Available commands are:

```text
PYTHONPATH=src python3 -m caip_maintenance.data register-sources
PYTHONPATH=src python3 -m caip_maintenance.data fetch --source SOURCE_ID --release RELEASE
PYTHONPATH=src python3 -m caip_maintenance.data validate-raw --source SOURCE_ID
PYTHONPATH=src python3 -m caip_maintenance.data assess-ahs
PYTHONPATH=src python3 -m caip_maintenance.data harmonize --release DATASET_RELEASE
PYTHONPATH=src python3 -m caip_maintenance.data audit-release --release DATASET_RELEASE
PYTHONPATH=src python3 -m caip_maintenance.data assign-splits --release public-corpus-v0.2.0-ahs --split ahs-grouped-temporal-v1
PYTHONPATH=src python3 -m caip_maintenance.data audit-split --release public-corpus-v0.2.0-ahs --split ahs-grouped-temporal-v1
PYTHONPATH=src python3 -m caip_maintenance.data preprocess-ahs --release public-corpus-v0.2.0-ahs --split ahs-grouped-temporal-v1 --preprocessor ahs-training-fold-v1
PYTHONPATH=src python3 -m caip_maintenance.data audit-preprocessing --release public-corpus-v0.2.0-ahs --split ahs-grouped-temporal-v1 --preprocessor ahs-training-fold-v1
```

Separate `build-snapshots` and `build-labels` commands remain deferred. RHFS emits both tables
for cross-sectional held-out estimation; AHS now emits earlier-wave snapshots and later-wave
labels for its separate longitudinal proxy task.

Each source configuration must declare native keys, grain, calendar, currency, sentinels, variable mappings, label role, license, and expected artifacts. The AHS field names are pinned from the selected official codebooks; apply the same evidence rule to every later source rather than hard-coding assumed names.

## Current implementation checkpoint — 2026-08-10

Completed:

- Registered the full 10-source shortlist with conservative candidate/approval states.
- Acquired and hash-verified the official RHFS 2024 PUF, codebook, and version document.
- Implemented all 34 retained RHFS feature mappings, explicit sentinel reasons, target
  eligibility, zero evidence, source-edit origin, operating-expense reconciliation, native-ID
  tokenization, row lineage, immutable releases, manifests, and audits.
- Built local release `public-corpus-v0.1.0-rhfs` from 4,425 authentic properties. It has
  1,488 label-bearing properties, 32 explicit valid zeros, 29 source-edited usable labels,
  and zero reconciliation failures.
- Passed 18 RHFS release QA checks and nine automated contract tests overall, including
  deterministic rebuild and deliberate checksum-drift scenarios.
- Documented the release in `PublicCorpusDatasetCard.md`.
- Acquired and hash-verified 28 official AHS artifacts covering the 2015, 2017, 2019,
  2021, and 2023 national PUFs and supporting codebooks/documentation.
- Proved from official documentation that `CONTROL` is the stable sample-case identifier,
  `MAINTAMT` is annual routine-maintenance cost, and the 2023 response maximum increased
  from USD 10,000 to USD 100,000.
- Passed the AHS go/no-go gate with 36,623 distinct linked housing units and 86,125 eligible
  adjacent-wave pairs, then built the separate local release
  `public-corpus-v0.2.0-ahs` for `future_routine_cost_proxy_v1`.
- Passed 21 AHS release checks covering lineage, task isolation, later-wave labels,
  response-cap metadata, identifier removal, and checksums. See `AHSGateDecision.md`.
- Froze `ahs-semantic-license-v1`: local PUF analysis is permitted for this project, outcome
  fidelity and zero semantics are bounded, and row-level redistribution stays blocked until
  artifact-specific approval is recorded.
- Built and passed all 16 checks for `ahs-grouped-temporal-v1`: 10,103 units / 13,871 rows
  training, 7,067 / 15,400 validation, and 19,453 / 56,854 test, with zero cross-split units.
  The all-wave view retains 86,125 rows without clipping; the pre-2023-cap sensitivity view
  retains 66,672.
- Published `AHSPublicCorpusDatasetCard.md` with the source hashes, label rules, features,
  table and lineage counts, frozen split, sensitivity views, fidelity limits, prohibited
  claims, and reproducible audit commands.
- Implemented and audited `ahs-training-fold-v1`: all learned preprocessing and the USD
  1,428 high-cost threshold fit on 13,871 training rows only; all 86,125 rows retain their
  original labels and cap metadata without target imputation or clipping. All 11
  preprocessing audits pass, and no model is fitted.
- Implemented and audited the fixed AHS-only `ahs-baselines-models-v1` comparison: three
  documented baselines plus linear regression, Random Forest, and gradient boosting use the
  same 205 frozen features. All fitting is limited to training rows, both evaluation views
  are reported, and all 11 artifact audits pass. No model was selected or promoted.
- Implemented and audited `ahs-baselines-models-log1p-v1` on the same split/features: fitted
  models train on `log1p(USD)` and metrics are computed after `expm1` in original USD.
  Baselines remain raw-USD rules. All 11 artifact audits pass; no promotion.
- Completed `ahs-diagnostic-review-v1`: residual, subgroup, survey-weight, and decision-utility
  analysis of the frozen comparison. All 10 review audits pass. See `AHSDiagnosticReview.md`.
- Froze `ahs-selection-policy-v1`: primary objective is validation MAE; sensitivity MAE and
  high-cost F1 are required secondary reports; a fitted model may be promoted only if it wins
  validation MAE and also leads (or ties) sensitivity MAE. Applied to
  `ahs-baselines-models-v1`, no fitted model is promoted; report `type_median` as primary
  estimator and `prior_cost` as high-cost reference. Hyperparameter search remains closed.
  See `AHSSelectionPolicy.md`.

Not complete:

- The other eight registered sources are candidates, not harmonized contributors.
- Appliance spending is not separable in the RHFS outcome, so it remains a lower-fidelity
  proxy rather than the exact WASC target.
- Redistribution and license review is pending; both row-level releases remain
  local-analysis-only.
- CPI/PPP normalization, PKR scenario conversion, uncertainty intervals, WASC scenario
  scoring, hyperparameter search, and fitted-model promotion remain unimplemented.

The next work is either keep reporting under `ahs-selection-policy-v1` for the CAIP write-up,
or open a separate written decision if hyperparameter search is desired later under the same
guardrails. The AHS gate passed, so NYC HPD is not opened as a
fallback; it may be evaluated later as complementary event evidence. Do not merge AHS or
any later HPD outcome with RHFS as if their labels represented the same maintenance concept.

## 4. Construction workflow

### Phase A — Source approval and acquisition

- Complete the weighted source-assessment matrix and record accept/reject reasons.
- Download fixed releases into immutable, gitignored source/version directories.
- Capture file hashes, byte counts, access dates, licenses, codebooks, and retrieval parameters.
- Check redistribution rights before producing any row-level release.
- Tokenize native identifiers immediately; exclude names, addresses, contact details, and free text from analytical outputs.

### Phase B — Source-specific staging

- Parse each source without altering raw files.
- Convert native missing values into explicit reasons: `unknown`, `not_applicable`, `not_collected`, `suppressed`, or `structural_absence`.
- Standardize dates, ISO currencies, measurement units, categories, and native grains.
- Retain source values alongside normalized values.
- Quarantine duplicate identities, impossible intervals, ambiguous joins, and incompatible cost definitions.

### Phase C — Harmonization and feature generation

- Stack compatible observations; do not copy features between unrelated properties.
- Join NYC data only through verified parcel/building keys.
- Join weather and economic series through documented geography-period keys.
- Generate only features available on or before `as_of_date`, including trailing 12-, 24-, and 36-month events and weather summaries.
- Keep structural missingness indicators. Fit statistical imputers, encoders, scalers, and optional winsorization on training folds only.
- Exclude features above 40% missingness from the core model unless a documented policy exception is approved.
- Never impute a target.

Normalize costs by:

1. Preserving original nominal amount and currency.
2. Deflating to 2023 local prices using country CPI.
3. Converting to `cost_intl_2023_ppp`.
4. Creating a separately named `cost_pkr_2023_ppp_equivalent` for WASC scenario presentation.

The PKR field must never be presented as an observed Pakistani or WAPDA transaction.

### Phase D — Modeling and evaluation

- Use baseline median, type/source median, and prior-cost models where valid.
- Compare regularized linear regression, random forest, and gradient boosting using identical splits.
- Use MAE as the primary metric; also report RMSE, median absolute error, RMSLE, and R² with bootstrap confidence intervals.
- Define “high cost” as the top 20% of target values in each training fold only. Evaluate PR-AUC, precision and recall at the top 20%, Brier score, and calibration.
- Report results separately by source, asset grain, housing type, zero/nonzero outcome, and label-fidelity class.
- Calculate survey-weighted descriptive and sensitivity results where source weights exist.

Split rules:

- RHFS: grouped property split, stratified by region and asset grain; report as held-out estimation.
- AHS: housing-unit group split with the latest eligible transition as test, preceding transition as validation, and older transitions as training.
- NYC: non-overlapping fiscal label windows; earlier periods train, penultimate complete period validates, and latest complete period tests.
- WASC: scoring only, with feature-support and out-of-domain warnings; never included in training or metric calculation.

### Phase E — Documentation and release

Produce for every release:

- Source-selection matrix and decision log.
- Machine-readable schema and data dictionary.
- Dataset card/datasheet describing population, outcome fidelity, exclusions, bias, and intended use.
- Mapping specifications for every source field.
- Release manifest containing versions, hashes, row counts, feature lists, splits, and transformations.
- QA report with passed, failed, and waived checks.
- EDA report separated by source and modeling task.
- Reproduction commands and environment lock file.
- Updates to the canonical policy, findings, architecture, workflows, security, testing, README, and changelog documents.

## 5. Verification and acceptance criteria

A dataset release is eligible for modeling only when:

- It contains at least 500 deduplicated, real, label-bearing analytical assets. RHFS sample size suggests feasibility, but the threshold must be verified after eligibility filtering.
- Every label has source-row lineage, period, currency, coverage, origin, and scope-fidelity metadata.
- Every feature passes an automated cutoff-date test.
- No label is statistically imputed or generated.
- No aggregate building is expanded into fictional unit-level samples.
- All primary and foreign keys, grains, and date intervals are valid.
- Costs are nonnegative; capital and appliance-scope rules are audited.
- Every zero target is supported by explicit response or documented complete coverage.
- RHFS maintenance expense reconciles with total operating expense where both values are usable; failures are quarantined.
- AHS contributes at least 500 valid earlier/later linked units before its task is released.
- NYC contributes at least 500 buildings with complete future-window coverage before its auxiliary task is released.
- Source-native identifiers are tokenized and automated scans find no prohibited personal information.
- Rebuilding from the same raw snapshots produces identical row counts, hashes, and split assignments.
- License and redistribution checks pass for every released source.

Required automated scenarios include checksum drift, schema drift, sentinel conversion, duplicate assets, invalid hierarchy, ambiguous joins, target leakage, cutoff boundaries, entity leakage across splits, training-fold high-cost thresholds, top-coded values, incomplete zeros, currency conversion, lineage completeness, privacy scanning, and strict separation of WASC reference data.

If a task fails its sample, lineage, coverage, or scope gates, withhold that task and document the failure. Do not manufacture replacement records or labels.

## Assumptions fixed for implementation

- Registration-gated public data is allowed when access and redistribution terms are documented.
- PPP-normalized cost is the cross-country modeling measure; PKR is a separately labeled scenario conversion.
- RHFS is the initial core cost source, subject to appliance-scope verification.
- AHS is a longitudinal proxy task, not an exact 12-month work-order outcome.
- NYC HPD is an auxiliary partial-scope forecast task.
- EHS and HIES provide reference, transfer, and validation evidence unless their records contain eligible same-property labels.
- Public-source corpus rows and the 101-unit WASC reference inventory remain analytically and semantically separate.
