## Recommended dataset strategy

Use a **hybrid, multi-source construction strategy** under current access constraints:

1. Keep the existing WAPDA/WASC files as immutable **seed evidence** for problem framing, inventory shape, category mix, and known conflicts—not as the supervised training corpus.
2. Because property-linked WAPDA operational extracts (work orders, invoices, complaints, construction years, cost lines) are **not currently obtainable** under organizational privacy and authorization rules, do **not** wait on WAPDA retrospective exports for model training.
3. Identify and analyze **5–10 high-quality public datasets** aligned with residential/building maintenance, housing attributes, repair costs, condition, occupancy proxies, and related economic or environmental context.
4. Extract transferable features, relationships, and cost/condition patterns from those sources; **harmonize** them into one unified schema that matches this project’s prediction grain and target contract.
5. Construct a training corpus of **more than 500 properties** with rich features and high-quality labels suitable for exploratory analysis, feature engineering, model comparison, and evaluation.
6. Keep any residual WAPDA seed material private, redacted, and clearly separated from the public-source training tables.
7. Add public economic and weather context only as supplementary features after license and provenance review.
8. If WAPDA later authorizes operational extracts, treat them as a future validation or transfer cohort—not a silent rewrite of the public training history.

This is **not** arbitrary fabrication of maintenance histories. Labels and features must derive from documented real public sources (or transparent, versioned transforms of those sources), with lineage for every constructed field. The final analytical surfaces must state clearly that training data are **harmonized public multi-source records designed to mirror the WASC residential maintenance-cost problem**, not observed WAPDA work-order outcomes.

### AHS longitudinal gate status — 2026-08-08

The first longitudinal gate is **GO**. Official AHS 2015–2023 national PUFs and
documentation yield 36,623 distinct exact-`CONTROL` linked units and 86,125 eligible
adjacent-wave feature-to-label pairs, exceeding the 500-unit requirement. The implemented
release `public-corpus-v0.2.0-ahs` is restricted to the separate task
`future_routine_cost_proxy_v1`; it must not be stacked with RHFS or described as an exact
12-month WAPDA outcome. The 2023 maintenance-response cap change is retained explicitly.
Redistribution remains `local-analysis-only` pending license review. The evidence, filters,
counts, artifacts, and reproduction commands are canonical in
[AHSGateDecision.md](AHSGateDecision.md).

The analytical-use review is frozen in
[AHSSemanticLicenseDecision.md](AHSSemanticLicenseDecision.md): official PUF material is
approved for local analysis, while redistribution of copied or derived row-level artifacts
remains blocked until artifact-specific approval is recorded. The immutable
`ahs-grouped-temporal-v1` assignment keeps all transitions for a tokenized housing unit in
one cohort. It assigns 10,103 units to training, 7,067 to validation, and 19,453 to test;
its 16 audits pass with zero unit leakage. The primary evaluation view retains all 86,125
labels without clipping, while the cap-sensitivity view excludes the 19,453 labels from the
2023 wave. The release, label, feature, lineage, split, use, and fidelity contracts are
published in [AHSPublicCorpusDatasetCard.md](AHSPublicCorpusDatasetCard.md).

The existing WASC files remain valuable for:

- locking the 101-unit residential inventory and A–F category counts
- documenting account-level ledger limitations
- approving target, allocation, and privacy policies
- grounding the decision-support narrative in a real public-sector setting

They are still insufficient alone for property-level supervised learning. See [CodexFindings.md](CodexFindings.md).

## 0. Approved policy decisions (stakeholder answers)

| Topic | Decision |
|---|---|
| Data owner | Project collector / student owner; all WAPDA-derived material remains private |
| Project data steward | Same project steward |
| Academic use of current seed files | Authorized under privacy constraints below |
| Privacy / retention | Process lawfully; retain only as long as necessary; role-limited internal access; keep critical infrastructure within national borders; redact PII and system blueprints before any material leaves the secure network |
| Primary operational scope | 101 WASC residential units only (`1/4/16/24/16/40` by A–F) |
| Non-residential / extra sites | Out of primary model (hospital, complex, rest house, mini-WAPDA-house, academic, hostel, mosque, recreation, roads, offices, revenue) |
| Training volume | Expand the **model-training corpus** beyond 101 to **>500 properties** via public multi-source harmonization |
| Primary target | Direct routine/corrective/emergency + equal-per-active-unit shared allocation; fiscal June 30 → July 1–June 30 |
| Target exclusions | Reconstruction, major capital renovation, land/book values, rent/revenue, unreconciled advances, PLV closings, duplicates/reversals, unrelated assets |
| Major renovation vs repair | Classify using **cost, scope, time period, and approval type** (thresholds versioned when set) |
| Personal appliances | Always excluded |
| Shared-cost rule | Equal per active unit |
| Allocation approver | Budget officer |
| High-cost operational threshold | None from WAPDA; use experimental **top 20% within each training fold** |
| Zero vs missing attestation | Project data steward; for the public training corpus, completeness is defined by source coverage flags in the harmonized schema (WAPDA coverage-attestation forms are not a current blocker) |
| Authoritative H-8/1 land area | **10.73 acres** for that property-period |
| Authoritative C–F floor areas | Fixed-asset totals **33,088 / 40,200 / 17,520 / 35,200** sq ft |
| G-8/2 dates | Store notification, purchase/possession, and construction milestones as **independent columns** |
| Conflict adjudicator | Director of Housing & Estate (for WASC seed conflicts) |
| WAPDA property IDs on operational records | Not available without further legal authorization |
| WAPDA work orders / costs / invoices / construction years / job volume | Not available under current private-data rules; construct the training dataset from public sources instead |

## 1. Dataset contract to approve first

### Population

**Decision-support framing:** WAPDA/WASC residential houses and apartments (101-unit baseline inventory).

**Training corpus:** a harmonized residential property-period dataset of **>500** units built from public sources, mapped onto the same grain, target, and feature contract so models can be trained and evaluated honestly under access constraints.

| Category | Location | Type | Units | Area per unit |
|---|---|---|---:|---:|
| A / Cat-I | G-8/2 | Bungalow | 1 | 4,950 sq ft |
| B / Cat-II | G-7/2 | Bungalow | 4 | Approximately 3,862.5 sq ft |
| C / Cat-III | I-8/1 | Apartment | 16 | 2,068 sq ft |
| D / Cat-IV | I-8/1 | Apartment | 24 | 1,675 sq ft |
| E / Cat-V | I-8/1 | Apartment | 16 | 1,095 sq ft |
| F / Cat-VI | H-8/1 | Apartment | 40 | 880 sq ft |
| **Total (WASC seed)** |  |  | **101** |  |

Academic buildings, hostels, hospitals, offices, mosques, recreation facilities, roads, rent, revenue, land, and book values remain outside the primary model.

### Prediction grain

One record represents:

> One residential property at one historical cutoff date.

Use fiscal-year cutoffs where possible:

- `as_of_date`: June 30
- Feature information: available on or before June 30
- Label interval: July 1 through June 30 of the following year

Public-source calendars may use calendar years or other fiscal conventions; map them explicitly and document the mapping in the dataset card.

### Primary target

```text
maintenance_cost_next_12_months_pkr
  = verified direct routine/corrective/emergency cost
  + approved allocation of eligible shared-building cost
```

Store separately:

- `direct_cost_next_12m_pkr`
- `shared_allocated_cost_next_12m_pkr`
- `maintenance_cost_next_12_months_pkr`
- `major_renovation_cost_next_12m_pkr`
- `label_complete`
- `censor_reason`
- `label_origin` (`public_source_harmonized`, `wapda_seed_descriptive_only`, etc.)

Exclude reconstruction, major capital renovation, unreconciled advances, year-closing entries, duplicates, reversals, and unrelated asset expenditure. Personal appliances are always excluded.

A zero label is allowed only when the governing coverage flags for that property-period show complete eligible-source coverage and no eligible work. Absence of a row must not be interpreted as zero.

### Expected model outputs

The dataset must support:

- Next-12-month nominal maintenance cost in PKR (or a documented currency conversion to nominal PKR)
- High-cost property ranking or flag (top 20% within each training fold until a WAPDA budget threshold exists)
- Optional prediction range
- Colony/site-level sum of property predictions
- Property type, age, cost-band, and site evaluation
- Model explanations based on non-personal property features

## 2. Evaluation of acquisition alternatives

| Strategy | Assessment | Decision |
|---|---|---|
| Existing repository files only | Real seed inventory and account-level ledger; ~seven residential debits identify a unit | Keep as seed / descriptive evidence only |
| Existing GL plus narration parsing | Unreliable property linkage; misclassified narrations | Reconciliation and descriptive analysis only |
| Direct WAPDA work orders / invoices / complaints | Best operational alignment, but **blocked** by privacy and authorization rules | Deferred; not the current training path |
| Generic single open-source file used unchanged | May be real but poorly aligned to grain, currency, climate, and target | Insufficient alone |
| **5–10 public datasets harmonized into one schema** | Real-source features and labels, adapted to the project contract, volume >500 properties | **Current primary training strategy** |
| Newly collected WASC inspections | Useful future features if authorized; cannot alone supply 12-month labels now | Optional later |
| Public price and weather data | Inflation and environmental covariates | Supplementary |
| Arbitrary invented maintenance histories with no public-source lineage | Fabrication presented as observation | **Prohibited** |

## 3. Required data acquisition streams

### A. Public multi-source research and selection (primary)

Identify and document **5–10** candidate public datasets. For each candidate record:

- Source name, URL, license/terms, citation
- Geography, time span, and grain
- Property or building attributes available
- Maintenance, repair, complaint, inspection, or cost fields
- Strengths, gaps, and mapping risk to this project’s schema
- Whether it can contribute labels, features, or both

Prefer sources that together cover:

- Residential or housing-unit attributes (type, area, age, rooms, building kind)
- Maintenance/repair expenditure or work events with dates
- Condition, complaint, or service-request proxies where available
- Occupancy or usage intensity proxies where ethically usable
- Multi-year history sufficient for cutoff-safe snapshots

After selection, design a **unified harmonization specification** before building tables: field mappings, unit conversions, eligibility rules, currency handling, and provenance columns.

### B. WASC / WAPDA seed (secondary, private)

Retain from existing files only what is needed to:

- Freeze the 101-unit inventory and anonymized IDs `A-01` … `F-40`
- Crosswalk A–F ↔ Cat-I–Cat-VI
- Apply adjudicated area and date resolutions below
- Support descriptive account-level analysis of the ledger

Do **not** treat ledger debits as property-level training labels. Do not copy PII, designations, or unredacted narration into analytical exports.

Generate anonymized analytical IDs such as:

```text
A-01
B-01 ... B-04
C-01 ... C-16
D-01 ... D-24
E-01 ... E-16
F-01 ... F-40
```

Retain any protected source-to-anonymous crosswalk outside analytical exports and outside the public training corpus.

### C. Harmonized work-order / cost events (from public sources)

Map public repair/maintenance events into the project’s operational tables where possible:

- Work-order or event ID
- Property or shared-building ID (constructed analytical IDs)
- Related complaint ID when available
- Inspection, start, and completion dates
- Job status
- Maintenance category and type
- Component repaired
- Repair versus replacement / major renovation flags (using cost, scope, time period, approval type)
- Priority and emergency status
- Repeat-problem indicator
- Contractor token when present
- Verification / completion status
- Cost lines and totals used for labels

Only completed, eligibility-screened events may contribute to labels. Every label row must cite public-source lineage.

### D. Complaints, inspections, occupancy, renovation

Where public sources provide analogues, map them into:

- Standardized complaint categories
- Condition scores on the 1–5 scale (or a documented remapping)
- Occupancy status periods without personal identifiers
- Major renovation and component-replacement dates

If a public source lacks a field, store null with an explicit missingness indicator—do not invent values.

### E. Public contextual data

After approval and license review, obtain monthly:

- Inflation/CPI
- Material price indices
- Labour and contractor indices
- Cement, steel, paint, plumbing, and electrical price indicators
- Site rainfall, temperature, humidity, and waterlogging events where geography is known

Each extract must be versioned, hashed, and documented. Prefer nominal PKR outputs; if source currency differs, document conversion and keep both raw and converted amounts.

## 4. Required collection volume

Training corpus targets:

- **More than 500** properties in the harmonized dataset
- Preferably multiple sites or strata analogous to colonies/categories
- At least three years of history where source coverage allows, preferably five
- On the order of **1,500–2,000** verified completed maintenance events after harmonization and eligibility filtering

The WASC 101-unit inventory remains the operational framing seed; it is **not** expected to supply the full training volume under current access rules.

A practical public-source window should cover enough complete cutoff-plus-label intervals for temporal train / validation / test splits, with the latest complete period reserved for testing.

## 5. Dataset structure

Use normalized event tables as the source of truth and generate model-ready snapshots from them.

| Layer | Required tables |
|---|---|
| Governance | `source_document`, `record_lineage`, `data_conflict`, `coverage_period`, `public_source_register` |
| Property | `site`, `building`, `property_unit`, `property_component` |
| Usage | `occupancy_period`, optional `unit_usage_month` |
| Condition | `property_inspection` |
| Operations | `complaint`, `work_order`, `renovation_event` |
| Costs | `work_order_cost_line`, `ledger_transaction` (optional/public analogue), `work_order_ledger_link`, `property_cost_allocation` |
| Context | `economic_index_month`, `weather_site_month` |
| Modeling | `property_period_snapshot`, `property_period_label` |

The principal relationships are:

```text
site -> building -> property_unit
property_unit -> occupancy, inspection, complaint, direct work order
building -> shared work order
work order -> cost lines
shared work order -> equal-per-active-unit allocations
property_unit + cutoff -> snapshot -> following-12-month label
```

Every normalized row must retain a source identifier and locator (dataset ID, file, row, API extract version, or form ID). Constructed fields must record transform version and confidence.

## 6. End-to-end build plan

### Phase 1 — Governance and policy approval

Completed or in force from stakeholder answers:

1. Data owner and project data steward assigned (same individual under private handling).
2. Authorization confirmed for current seed files under privacy rules.
3. Residential WASC scope frozen at 101 units; non-residential assets excluded.
4. Target eligibility policy approved.
5. Shared-cost allocation: equal per active unit; budget officer is approver.
6. Major renovation dimensions: cost, scope, time period, approval type.
7. High-cost rule: top 20% within each training fold.
8. Privacy, access, retention, and redaction rules approved.
9. WAPDA operational extraction deferred; public multi-source path adopted.

Exit criterion: target policy, scope version, privacy rules, and training-source strategy are written and approved. **Met for documentation purposes by this revision.**

### Phase 2 — Public source shortlist and mapping design

1. Search and shortlist 5–10 candidate public datasets.
2. Score each on license, grain, features, label usability, geography/time fit, and volume.
3. Select the harmonization set and write a field-mapping specification.
4. Define currency, area, category, and date normalizations.
5. Define how shared costs and major renovations will be derived when native fields differ.
6. Register every public source in `public_source_register` with hash/version.

Exit criterion: approved shortlist, mapping spec, and lineage plan before bulk construction.

Status: **met for RHFS and AHS task slices**. Eight other registered sources remain
candidates. The AHS official-field/linkage/sample gate passed; this does not approve mixing
the two task outcomes.

### Phase 3 — Freeze the WASC property master (seed)

1. Import existing property sources without modifying them.
2. Hash and register every file.
3. Crosswalk A–F against Cat-I–Cat-VI.
4. Reconcile the active-unit count to 101.
5. Apply adjudicated resolutions:
   - H-8/1 land area **10.73 acres** for that property-period
   - C–F building floor areas from fixed-asset totals
   - G-8/2 lifecycle dates in separate columns
6. Quarantine remaining unresolved conflicts for Director of Housing & Estate review.
7. Issue permanent anonymous property and building IDs for the seed inventory.

Exit criterion: every in-scope WASC active unit has a unique property ID and verified core characteristics for framing; seed remains separate from the public training corpus.

### Phase 4 — Construct the harmonized training corpus

1. Land public extracts in immutable raw storage (separate from `DatasetOfCAIP/`).
2. Stage exact copies with locators.
3. Normalize IDs, dates, amounts, areas, and controlled categories.
4. Build property, event, cost, and coverage tables.
5. Apply eligibility and shared-allocation rules.
6. Quarantine unresolved mappings with reason codes.
7. Produce source-level coverage and bias reports.
8. Scale to **>500** properties and sufficient completed events.

Exit criterion: verified public-source lineage for admitted labels; no invented outcomes without lineage.

Status: **met for two separate local task releases, not for a single pooled target**. RHFS
provides annual held-out estimation and AHS provides a longitudinal future routine-cost
proxy. The AHS split, training-fold-only preprocessing, and first fixed comparison are
implemented and audited. Artifact-specific redistribution review remains open.

### Phase 5 — Optional prospective / inspection collection

Only if later authorized:

1. Inspect WASC units with the standard 1–5 form.
2. Start prospective complaint and work-order collection with mandatory property IDs.
3. Use as a future transfer or validation cohort if WAPDA releases linked costs.

Retrospective public-source costs remain necessary for the immediate CAIP model under current constraints.

### Phase 6 — Normalize, reconcile, and build cutoff-safe snapshots

For each property and eligible cutoff:

1. Use only information known on or before the cutoff.
2. Join static attributes effective on that date.
3. Aggregate prior maintenance, complaints, condition, occupancy, and context features.
4. Sum eligible costs in the following 12 months for the label.
5. Set `label_complete` / `censor_reason` from coverage flags.
6. Fit nothing that requires validation/test labels.

Exit criterion: one unique snapshot and label per eligible property-period, with no future leakage.

### Phase 7 — Freeze the first dataset release

A release should contain:

- Immutable source manifest and hashes (public sources + WASC seed register)
- Harmonization and mapping specification version
- Normalized schema version
- Target and allocation policy versions
- Anonymized analytical tables with `label_origin`
- Snapshot and label manifests
- Quality and reconciliation reports
- Missingness, exclusion, and bias reports
- Conflict register
- Train/validation/test split manifest
- Dataset card stating public-source construction and limits vs WAPDA operations
- Release notes and responsible approver

Processed row-level data should remain outside version control. Only schemas, mappings, code, documentation, and privacy-safe aggregates belong in the repository.

## 7. Cleaning and preprocessing rules

- Parse all dates to ISO format; preserve posting, invoice, reference, completion, and payment dates separately when present.
- Use decimal-safe monetary arithmetic; document currency conversion to PKR.
- Preserve nominal source amounts; never overwrite them with adjusted values.
- Standardize category spelling through versioned mappings.
- Preserve redacted original values and mapping confidence for audit.
- Convert area units only after confirming their meaning.
- Keep land notification, acquisition, possession, and construction dates separate (required for G-8/2).
- Exclude PLV-like closing entries and personal appliances from labels.
- Reconcile advances and accruals before treating them as completed expenditure when such fields exist.
- Preserve valid high-cost repairs; flag rather than delete them.
- Never impute targets.
- Distinguish unknown, not applicable, not collected, and confirmed zero.
- Fit feature imputers, encoders, scalers, and transformations on training data only.
- Add missingness indicators where absence may be informative.
- Keep free-text narration out of the first model; use standardized categories.
- Maintain direct and shared costs separately even when the model predicts their sum.
- Never present harmonized public labels as observed WAPDA outcomes.

## 8. Release-blocking quality checks

### Inventory and identity

- WASC seed inventory equals 101 units with category counts `1/4/16/24/16/40`.
- Training corpus has **>500** distinct properties after deduplication rules.
- Property, building, complaint, work-order, invoice/event, and snapshot keys are unique within the analytical schema.
- Every direct label-eligible job resolves to exactly one property.
- Every shared job resolves to one building and equal-per-active-unit allocations.

### Coverage and lineage

- Each included property-period has complete label-source coverage or is censored.
- Incomplete periods are censored, not assigned zero.
- Every admitted label cites public-source lineage (or an approved future WAPDA extract ID).
- Coverage and selection bias are reported by source, property type, and year.

### Dates and leakage

- Event date sequences are plausible.
- Every feature date is on or before `as_of_date`.
- Every label cost falls inside the following 12-month interval.
- Construction and component dates are not after the cutoff.
- High-cost thresholds are computed inside the training fold only.

### Money and reconciliation

- Verified totals equal cost-line sums within approved tolerance.
- Shared allocation weights sum to 1 (equal per active unit).
- Major renovation remains separate from the primary label.
- Currency conversion parameters are versioned.

### Values and privacy

- Condition scores are integers 1–5 after remapping, or null.
- WASC area conversions use the adjudicated authoritative figures or raise conflicts.
- Analytical outputs contain no resident name, CNIC, phone, designation, family details, or unredacted narration.
- WAPDA seed material never enters public releases or shareable fixtures.

## 9. Model-ready preparation

Freeze temporal splits before model tuning. For example:

- Training: earlier complete cutoff-label windows
- Validation: the next complete window
- Final test: the latest untouched complete window
- Optional site/stratum holdout: evaluate transfer

Do not randomly split annual histories from the same properties.

Prepare:

- Historical last-year-cost baseline
- Property/category historical-average baseline
- Linear regression pipeline
- Random Forest pipeline
- Gradient-boosting pipeline

Evaluate MAE, RMSE, high-cost precision/recall or top-\(k\), sample counts, subgroup diagnostics, temporal drift, and missingness dependence. Colony/site budget is the sum of property predictions.

Reports must disclose that metrics are measured on the **harmonized public training corpus**, and that transfer to real WAPDA operations is unvalidated until authorized linked data exist.

The first fixed AHS comparison implements the authorized subset of this plan: training
median, property-type median, and valid prior-cost baselines; ordinary linear regression,
Random Forest, and histogram gradient boosting; and MAE, RMSE, and frozen-threshold
high-cost metrics. It performs no tuning or model selection. The broader subgroup,
drift, missingness-dependence, and budget-aggregation work above remains planned.

## 10. Documentation package

Create and maintain:

- Dataset card: purpose, population, period, ownership, permitted use, public-source construction method, limitations vs WAPDA operations
- Public source register and selection memo (5–10 candidates; chosen set; reject reasons)
- Harmonization / mapping specification
- Data dictionary
- Target specification
- Allocation specification (equal per active unit; budget officer)
- ID crosswalk specification (seed vs training IDs)
- Controlled vocabulary and category mappings
- Transformation and lineage specification
- Quality, missingness, coverage, and bias reports
- Conflict and adjudication log
- Privacy/de-identification assessment
- Split and experiment manifest
- Release notes and version history

## 11. Go/no-go decision

Supervised model development on the **harmonized public corpus** may begin when:

- Scope and target policies are approved (done).
- Public source shortlist and mapping specification are approved.
- Constructed properties exceed 500 with cutoff-safe labels and lineage.
- Shared costs use equal-per-active-unit allocation where applicable.
- Complete label coverage can distinguish zero from missing inside the corpus.
- Privacy checks pass; WAPDA seed PII never enters training exports.
- A final test period is reserved before modeling.
- Dataset card states that results are not observed WAPDA operational outcomes.

Supervised training on **WAPDA ledger rows as property labels** remains a no-go under current linkage and access constraints.

If the public-source shortlist cannot supply adequate volume or label quality after honest mapping, narrow the research claim or extend the search—do not invent undocumented labels.
