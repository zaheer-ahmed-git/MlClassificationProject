# Project and dataset review

The project is a public-sector property-maintenance forecasting system for WAPDA staff housing. Its primary objective is to predict the next-12-month maintenance cost of an individual house or apartment and support budgeting and maintenance prioritization.

The concept and WASC seed inventory remain well defined. The current `DatasetOfCAIP/` files are still **not** sufficient for property-level supervised training: they provide a useful 101-unit inventory and an account-level ledger, but lack consistently linked property-level work orders, actual costs, condition inspections, complaints, and renovation history. Under current organizational privacy and authorization rules, WAPDA cannot supply those operational extracts. The approved path is therefore a **hybrid public multi-source training corpus** (>500 properties) harmonized to this project’s schema, while WASC files remain private seed evidence for framing and descriptive analysis. See [DatasetPolicy.md](DatasetPolicy.md).

## 1. Materials reviewed

The original evidence review covered all 13 supplied files and the three root folders.
Repository-native `.agents` and `.codex` guidance was added after that evidence review and
now governs implementation work; it is not source evidence about WAPDA outcomes.

| Material | Role and findings |
|---|---|
| [CAIP_Final_Project_Instructions.pdf](CAIP_Final_Project_Instructions.pdf) | Requires a real dataset, applied AI, at least two CAIP modules, measurable evaluation, and industry/governance relevance. |
| [ProjectDomain.md](ProjectDomain.md) | Selects WAPDA housing maintenance forecasting over alternative domains. |
| [Projectproposal.md](Projectproposal.md) | Defines the prediction objective, models, evaluation, application, and desired data. |
| [DataStructureProposed.md](DataStructureProposed.md) | Proposes the target, candidate features, minimum dataset size, privacy rules, and property-period grain. |
| [CamScanner occupancy PDF](</nfs/home/lisic/zahmed/CaipProj/DatasetOfCAIP/CamScanner 08-03-2026 13.59.pdf>) | Inventory of 101 residential units, but also contains names, designations, employers, and remarks that must not enter the analytical dataset. |
| [Details of properties.docx](</nfs/home/lisic/zahmed/CaipProj/DatasetOfCAIP/Details of properties.docx>) | Lists eight sites with land areas, coordinates, and boundary dimensions. Only the first four clearly match the core WASC scope. |
| [Presentation.pdf](</nfs/home/lisic/zahmed/CaipProj/DatasetOfCAIP/Presentation.pdf>) | Property categories, unit counts, stated areas, facilities, and revenue information. |
| [Presentation.pptx](</nfs/home/lisic/zahmed/CaipProj/DatasetOfCAIP/Presentation.pptx>) | Native duplicate of the presentation PDF. |
| [Repair & maintenance 2020-2025.xls](</nfs/home/lisic/zahmed/CaipProj/DatasetOfCAIP/Repair & maintenance 2020-2025.xls>) | General ledger covering five maintenance accounts and 712 transactions. |
| [Repair & maintenance residential.xls](</nfs/home/lisic/zahmed/CaipProj/DatasetOfCAIP/Repair & maintenance residential.xls>) | Exact subset of 95 residential-account records from the larger ledger; it adds no unique records. |
| [WASC LAND AND FIXED ASSETS.pdf](</nfs/home/lisic/zahmed/CaipProj/DatasetOfCAIP/WASC LAND AND FIXED ASSETS.pdf>) | Fixed-asset listing, land acquisition records, possession documents, layouts, historical book values, and residential floor areas. |
| [WASC consists of four properties...docx](</nfs/home/lisic/zahmed/CaipProj/DatasetOfCAIP/WASC consists of four properties the details of which are as under.docx>) | Confirms the four core WASC land holdings and their boundary/security status. |
| [WASC propertySOP Data.xlsx](</nfs/home/lisic/zahmed/CaipProj/DatasetOfCAIP/WASC propertySOP Data.xlsx>) | Four core properties, notification details and land areas. Its two sheets are identical duplicates. |

## 2. Defined project scope

### Domain

Predictive maintenance, public-sector asset management, infrastructure budgeting, and procurement decision support.

### In-scope assets

The current residential inventory supports 101 units:

| Normalized category | Source terminology | Location | Units | Area per unit |
|---|---|---:|---:|---:|
| A | Cat-I bungalow | G-8/2 | 1 | 4,950 sq ft |
| B | Cat-II bungalows | G-7/2 | 4 | approximately 3,862.5 sq ft |
| C | Cat-III flats | I-8/1 | 16 | 2,068 sq ft |
| D | Cat-IV flats | I-8/1 | 24 | 1,675 sq ft |
| E | Cat-V flats | I-8/1 | 16 | 1,095 sq ft |
| F | Cat-VI flats | H-8/1 | 40 | 880 sq ft |

Academic blocks, hostel buildings, mosque, recreation centre, roads, hospital, offices, rest house, mini-WAPDA-house, complex, and revenue-generating facilities are excluded from the primary residential model. Stakeholder scope freeze: **101 WASC residential units only** for the operational framing inventory. Training volume expansion beyond 101 uses the public harmonized corpus, not an expansion of WASC non-residential assets.

### Objectives

1. Predict the next-12-month maintenance cost in PKR for each residential unit.
2. Rank or flag likely high-cost properties.
3. Improve colony-level budget estimates.
4. Support preventive-maintenance prioritization.
5. Explain the main drivers of each prediction.
6. Compare historical baselines, linear regression, Random Forest, and gradient boosting.
7. Deliver a web proof of concept that supports property selection, predictions, risk information, colony summaries and predicted-versus-actual comparison.

### Evaluation

- MAE
- RMSE
- High-cost-property identification, preferably precision/recall at an approved top-\(k\) budget
- Performance breakdowns by property type, age group, cost range and colony

## 3. Target definition

### Primary label

`maintenance_cost_next_12_months_pkr DECIMAL(18,2)`

Recommended contract:

```text
direct routine maintenance
+ direct corrective maintenance
+ direct emergency maintenance
+ approved allocation of shared-building maintenance
```

Exclude:

- Complete reconstruction
- Major capital renovation
- Land acquisition and book values
- Rent and revenue
- Academic, hostel, mosque and recreation expenditure
- Advances that cannot be reconciled to completed work
- PLV year-closing entries
- Reversals or duplicate accounting entries
- Personal appliance costs (always excluded)

Store the components separately:

- `direct_maintenance_cost_next_12m_pkr`
- `shared_allocated_cost_next_12m_pkr`
- `maintenance_cost_next_12_months_pkr`, their sum
- `major_renovation_cost_next_12m_pkr`, excluded from the primary label

Because the ledger follows financial-year closing, the most natural snapshot is:

```text
as_of_date: June 30
label period: July 1 through June 30 of the following year
```

### Secondary label

`high_cost_next_12m BOOLEAN`

No WAPDA operational budget threshold is available. Use the approved experimental rule: **top 20% of costs within each training fold**, with method and threshold stored alongside the label. The threshold must never be calculated from validation or test data.

### Zero labels

A property may receive a zero target only when source coverage confirms that it was active and had no eligible maintenance. Missing work-order or ledger coverage must not be interpreted as zero expenditure. For the public training corpus, completeness is governed by harmonized coverage flags; WAPDA colony coverage-attestation forms are not a current blocker because WAPDA operational extracts are unavailable.

### Shared-cost and renovation policy (approved)

- Shared apartment-building costs: **equal per active unit**; allocation policy approved by the **budget officer**.
- Major renovation versus ordinary repair: classify using **cost, scope, time period, and approval type** (version thresholds when set); keep major renovation out of the primary label.
- Personal appliances: always excluded.

## 4. Required relational dataset

Type conventions: `UUID` for internal keys, `VARCHAR` for controlled identifiers, `DATE`, `TIMESTAMP`, `BOOLEAN`, `SMALLINT`, `INTEGER`, and `DECIMAL(18,2)` for PKR.

### A. Governance and lineage

| Table | Grain and required fields |
|---|---|
| `source_document` | One source file or system extract. `source_id PK`, `file_name`, `source_type`, `document_date`, `coverage_start`, `coverage_end`, `sha256`, `ingested_at`, `contains_pii`, `authority_rank`, `notes`. |
| `record_lineage` | One entity-to-source assertion. `lineage_id PK`, `entity_table`, `entity_key`, `source_id FK`, `source_locator`, `extraction_method`, `confidence_score DECIMAL(3,2)`, `verification_status`, `verified_at`. |

These tables are necessary because several values conflict between presentations, spreadsheets and scanned possession records.

### B. Property master

| Table | Grain and required fields |
|---|---|
| `site` | One colony/land holding. `site_id PK`, `site_name`, `sector`, `city`, `province`, `latitude`, `longitude`, `boundary_geometry`, `notified_area_acres`, `raw_area_text`, `notification_number`, `notification_date`, `possession_date`, `acquisition_value_pkr`, `active_flag`, `verification_status`. |
| `building` | One physical bungalow or apartment block. `building_id PK`, `site_id FK`, `building_kind`, `category_code`, `legacy_category`, `block_number`, `construction_year`, `total_floors`, `total_units`, `total_covered_area_sqft`, `lift_available`, `lift_installation_date`, `shared_roof`, `shared_water_tank`, `shared_sewerage`, `active_from`, `active_to`. |
| `property_unit` | One house/apartment. `property_id PK`, `building_id FK`, `unit_number`, `property_type`, `category_code`, `floor_number`, `covered_area_sqft`, `plot_area_sqft`, `bedrooms`, `bathrooms`, `kitchens`, `number_of_floors`, `construction_material`, `roof_type`, `flooring_type`, `water_supply_type`, `sewerage_type`, `water_tank_type`, `active_from`, `active_to`, `master_data_status`. |
| `property_component` | One installed component. `component_id PK`, `property_id FK nullable`, `building_id FK nullable`, `component_type`, `material_or_model`, `installation_date`, `last_replacement_date`, `warranty_expiry_date`, `shared_component`, `condition_status`. |

Each component must belong to either a unit or a shared building, not both.

### C. Occupancy and usage

| Table | Grain and required fields |
|---|---|
| `occupancy_period` | One unit-status interval. `occupancy_id PK`, `property_id FK`, `start_date`, `end_date`, `occupancy_status`, `occupant_count`, `usage_intensity`, `unauthorized_modifications`, `source_id FK`. |
| `unit_usage_month` | One unit-month. `property_id FK`, `month`, `occupied_days`, `occupant_count`, `water_usage`, `electricity_usage`, `data_coverage_status`; composite PK `(property_id, month)`. |

Allowed occupancy values: `occupied`, `vacant`, `partially_occupied`, `unknown`.

Do not retain resident name, CNIC, telephone, designation, salary, family details or free-text personal remarks.

### D. Condition, complaints and repairs

| Table | Grain and required fields |
|---|---|
| `property_inspection` | One inspection. `inspection_id PK`, `property_id FK`, `inspection_date`, scores for `roof`, `wall`, `foundation`, `paint`, `plumbing`, `electrical`, `sewerage`, `floor`, `door_window`, `bathroom`, `kitchen`, `water_tank`, `overall`, defect booleans for leakage, cracks, dampness, exposed wiring, blocked drainage, termites and seepage, `inspection_complete`, `source_id FK`. |
| `complaint` | One complaint. `complaint_id PK`, `property_id FK`, `opened_date`, `category`, `component_type`, `priority`, `status`, `resolved_date`, `repeat_of_complaint_id FK nullable`, `description_redacted`, `emergency_flag`, `source_id FK`. |
| `work_order` | One maintenance job. `work_order_id PK`, `property_id FK nullable`, `building_id FK nullable`, `complaint_id FK nullable`, `inspection_date`, `start_date`, `completion_date`, `maintenance_category`, `maintenance_type`, `component_type`, `repair_action`, `priority`, `status`, `repeat_problem`, `contractor_id`, `warranty_covered`, `problem_description_redacted`, `target_eligible`, `exclusion_reason`. |
| `work_order_cost_line` | One cost component. `cost_line_id PK`, `work_order_id FK`, `cost_type`, `amount_pkr`, `invoice_number_token`, `invoice_date`, `payment_date`, `verified_actual`, `source_id FK`. |
| `renovation_event` | One major renovation or replacement. `renovation_id PK`, `property_id/building_id FK`, `component_type`, `start_date`, `completion_date`, `event_type`, `cost_pkr`, `warranty_expiry_date`, `excluded_from_primary_target`. |

Inspection scores use the documented scale:

```text
1 Excellent
2 Good
3 Fair
4 Poor
5 Critical
```

Maintenance categories should be controlled values:

```text
plumbing, electrical, roofing, civil_structural, paint, flooring,
doors_windows, sewerage_drainage, water_supply, kitchen, bathroom,
hvac, boundary_wall, shared_common_area, emergency_other
```

Maintenance types:

```text
preventive, corrective, emergency, major_renovation
```

### E. Financial records and allocation

| Table | Grain and required fields |
|---|---|
| `ledger_transaction` | One raw GL transaction. `transaction_id PK`, `posting_date`, `voucher_type`, `voucher_number`, `reference_nature`, `reference_number_token`, `reference_date`, `account_code`, `account_name`, `narration_redacted`, `debit_pkr`, `credit_pkr`, `signed_amount_pkr`, `balance_pkr`, `dr_cr`, `source_id FK`, `source_row`, `duplicate_group_id`, `transaction_stage`, `target_eligible`. |
| `work_order_ledger_link` | Audited many-to-many reconciliation. `link_id PK`, `transaction_id FK`, `work_order_id FK`, `linked_amount_pkr`, `link_method`, `link_confidence`, `manually_verified`. |
| `property_cost_allocation` | Allocation of a work order to a unit. `allocation_id PK`, `work_order_id FK`, `property_id FK`, `allocation_basis`, `allocation_weight`, `allocated_cost_pkr`, `approved_flag`. |

For shared apartment-block work, allocation weights must sum to 1. Approved policy: **equal per active unit**, approved by the budget officer.

### F. External context

| Table | Grain and required fields |
|---|---|
| `economic_index_month` | One month and geographic scope. `month`, `scope`, `cpi`, `inflation_rate`, `material_price_index`, `labour_rate_index`, `contractor_rate_index`, `cement_price_pkr`, `steel_price_pkr`, `paint_index`, `plumbing_index`, `electrical_index`, `source_id FK`. |
| `weather_site_month` | One site-month. `site_id FK`, `month`, `rainfall_mm`, `average_temperature_c`, `maximum_temperature_c`, `humidity_pct`, `flood_or_waterlogging_incidents`, `data_coverage_pct`, `source_id FK`. |

The project notes identify PBS/SBP for economic information and Open-Meteo for weather, but no external extracts are currently present.

### G. Model-ready tables

| Table | Grain and required fields |
|---|---|
| `property_period_snapshot` | One property and historical cutoff. `snapshot_id PK`, `property_id FK`, `as_of_date`, `feature_window_start`, static property features, latest condition scores and inspection age, occupancy features, maintenance cost/count aggregates for 12/24/36 months, complaint aggregates, renovation/component ages, economic and weather features, missingness indicators, `feature_coverage_status`. |
| `property_period_label` | One snapshot label. `snapshot_id PK/FK`, `label_start_date`, `label_end_date`, `direct_cost_pkr`, `shared_allocated_cost_pkr`, `maintenance_cost_next_12_months_pkr`, `major_renovation_cost_pkr`, `high_cost_flag`, `high_cost_threshold_pkr`, `threshold_method`, `label_complete`, `censor_reason`. |

Important snapshot features include:

- Property type, category, age and area
- Bedrooms, bathrooms and occupant count
- Plumbing, wiring, roof and component ages
- Latest condition scores
- Cost in the previous 12 and 24 months
- Three-year average annual cost
- Repair counts by type
- Emergency jobs and repeat failures
- Days since last repair
- Maximum and average repair cost
- Open requests and complaint counts
- Years since major renovation
- Rainfall and environmental conditions
- Material, labour and inflation indices

## 5. Relationships

```text
site 1 ── M building 1 ── M property_unit
property_unit 1 ── M occupancy_period
property_unit/building 1 ── M property_component
property_unit 1 ── M inspections, complaints and work_orders
complaint 0..1 ── M work_order
work_order 1 ── M work_order_cost_line
work_order M ── M ledger_transaction
work_order 1 ── M property_cost_allocation ── 1 property_unit
property_unit 1 ── M property_period_snapshot 1 ── 1 property_period_label
site/month and economic/month context ── M snapshots
```

## 6. Source-specific preprocessing

1. Use the larger maintenance workbook as the canonical ledger. The residential workbook is an exact subset and must not be appended.
2. Remove the duplicated second sheet from the SOP workbook during ingestion.
3. Normalize identifiers to `A-01`, `B-01`–`B-04`, `C-01`–`C-16`, `D-01`–`D-24`, `E-01`–`E-16`, and `F-01`–`F-40`.
4. Preserve both the A–F and Cat-I–Cat-VI naming systems through a controlled crosswalk.
5. Store original area text and canonical units. Convert acres, kanals, marlas, square yards and square feet only after validating the source meaning.
6. Treat notification date, purchase date, possession date and construction date as distinct fields.
7. Parse Excel serial dates into ISO dates. Preserve both GL posting date and reference/invoice date.
8. Compute `signed_amount_pkr = debit_pkr - credit_pkr`, but derive targets only from verified work-order costs.
9. Exclude `PLV` year-closing transactions from maintenance targets.
10. Do not assume an advance adjustment or accrual represents a distinct completed repair; reconcile it to invoice and work-order data first.
11. Redact employee names, CNICs and other personal identifiers from occupancy documents and ledger narration. Tokenize contractor and invoice identifiers.
12. Standardize misspellings and categories in narration, but retain the original redacted text and mapping confidence.
13. Keep valid high-cost jobs. Flag them as outliers rather than deleting them; transformations such as `log1p(cost)` belong only in the model copy.
14. Preserve nominal PKR. An inflation-adjusted copy can be generated for modeling, but the application output should remain nominal PKR.
15. Never impute a target. For features, use training-fold-only imputations and add explicit missingness indicators.
16. Use only information recorded on or before `as_of_date`. Do not use completion, complaint or price information from the label period.
17. Split by time, with optional property/colony group holdouts. Random row splitting would leak overlapping property history.

## 7. Required quality checks

| Check | Rule |
|---|---|
| Inventory completeness | Current WASC scope should reconcile to 101 active units: 1/4/16/24/16/40 by A–F category. |
| ID integrity | Every label-eligible work order must resolve to a valid property or auditable shared-building allocation. |
| Uniqueness | No duplicate property-period snapshots, ledger transactions, invoices or work orders. |
| Date validity | Complaint ≤ inspection/start ≤ completion; feature dates ≤ cutoff; label costs fall strictly within the label interval. |
| Cost arithmetic | Verified work-order total equals the sum of cost lines within an approved tolerance. |
| Ledger reconciliation | Linked amounts may not exceed their GL transaction or work-order totals; reversals and closures must net correctly. |
| Allocation | Shared allocation weights sum to 1 and allocated amounts sum to the eligible shared cost. |
| Score range | All condition scores are integers 1–5; unknown remains null rather than zero. |
| Area consistency | Unit area × unit count must reconcile to building totals or be raised as a source conflict. |
| Construction age | Construction year cannot be after the cutoff; land purchase year must not be substituted for construction year. |
| Coverage | A zero target requires confirmed complete source coverage. |
| Category scope | Residential labels cannot contain hostel, academic, mosque, recreation or unrelated account costs. |
| Privacy | No name, CNIC, telephone, designation or unredacted personal narration in analytical exports. |
| Leakage | High-cost thresholds, imputers, scalers and encoders are fitted on training data only. |
| Source conflict | Conflicting values remain quarantined with lineage and verification status rather than silently overwritten. |

## 8. Known data conflicts

| Conflict | Status |
|---|---|
| Four core holdings total 11.95 acres vs presentation 10.23 WASC / 10.73 H-8/1 | **Adjudicated for H-8/1 property-period:** use **10.73 acres**. Other site-area conflicts remain quarantined pending Director of Housing & Estate review. |
| Presentation residential “total area” multiplies unit area by blocks; fixed-asset listing implies 33,088 / 40,200 / 17,520 / 35,200 sq ft for C–F | **Adjudicated:** fixed-asset totals are authoritative for C–F. |
| G-8/2 notification vs purchase/possession vs construction dates | **Adjudicated process:** store as independent lifecycle columns; required for true-zero structural attestation on that property-period. |
| Four WASC properties vs eight WAPDA properties | **Adjudicated scope:** non-residential extras stay out of the primary model. |
| Ledger filename 2020–2025 vs rows through July 2026 | Open; preserve coverage dates from content, not filename. |
| Residential-account narration includes hostel, road, playground, file-cover, HVAC | Open; account code alone is not a residential-property label. |

Conflict adjudicator for remaining WASC seed disputes: **Director of Housing & Estate**.

## 9. Current data sufficiency

The full ledger contains:

- 712 transactions across five maintenance accounts
- 104 residential-account transactions
- 99 residential debit entries totaling PKR 17,105,112
- 5 PLV closing credits totaling PKR 16,865,897
- Residential activity from January 2020 through February 2025
- The standalone residential file contains 95 of these 104 rows and omits nine early-2020 rows

A conservative narration review finds only about seven debit records that identify a specific unit or small set of units. Approximately 19 mention any useful asset, category or location clue. Most are generic employee advances, hand receipts or miscellaneous bills.

Therefore:

> The current WASC files can support descriptive account-level expenditure analysis and problem framing, but not reliable property-level next-12-month supervised learning from observed WAPDA work orders.

Access update: stable property IDs on operational records, completed work orders, cost lines, invoice–ledger reconciliation, and authoritative construction-year exports are **not currently available** from WAPDA without further legal authorization. Waiting on those extracts is no longer the training path.

Training-volume target under [DatasetPolicy.md](DatasetPolicy.md): **>500 properties**, preferably multi-year history, and on the order of **1,500–2,000** eligible completed maintenance events in a **harmonized public multi-source corpus**. Even a perfect WASC-only linkage of 101 units across three fiscal windows (~303 rows) would remain below that target.

## 10. Governance answers and revised collection plan

### Approved governance (stakeholder)

| Item | Answer |
|---|---|
| Data owner | Project collector; WAPDA-derived material kept private |
| Data steward | Same project steward |
| Seed-file academic use | Authorized under privacy rules |
| Privacy | Lawful processing; retain only as necessary; role-limited access; critical infrastructure within national borders; redact PII and system blueprints before leaving the secure network |
| WASC scope | 101 residential units; non-residential out |
| Training expansion | >500 properties via public-source harmonization |
| Shared costs | Equal per active unit; budget officer approves |
| High-cost flag | Top 20% within each training fold |
| Zero/missing | Steward-owned coverage flags in the harmonized schema |
| Authoritative areas/dates | H-8/1 = 10.73 acres; C–F fixed-asset floor totals; G-8/2 lifecycle columns separate |
| Conflict adjudicator | Director of Housing & Estate |

### Blocking for the **current** training path

The 10-source register now has two implemented, deliberately separate task releases. RHFS
contains 4,425 authentic properties and 1,488 usable annual-cost proxy labels. The AHS gate
passed on official 2015–2023 materials with 36,623 distinct exact-`CONTROL` linked units and
86,125 eligible adjacent-wave feature-to-label pairs; its release implements
`future_routine_cost_proxy_v1`. RHFS passes 18 release checks and AHS passes 21. The frozen
AHS semantic decision permits local analysis while keeping row-level redistribution blocked.
The grouped temporal assignment passes 16 checks with zero unit leakage: 10,103 units are in
training, 7,067 in validation, and 19,453 in test. See
[AHSGateDecision.md](AHSGateDecision.md) and
[AHSSemanticLicenseDecision.md](AHSSemanticLicenseDecision.md). The release and split are
published in [AHSPublicCorpusDatasetCard.md](AHSPublicCorpusDatasetCard.md). The remaining
blockers are:

1. Implement training-fold-only preprocessing and high-cost thresholds after the frozen split.
2. Evaluate the 2023 response-cap discontinuity with metrics on all 86,125 rows and on the
   66,672-row sensitivity view; never silently clip the 2023 labels.
3. Preserve the semantic boundary: RHFS is cross-sectional annual estimation; AHS is a
   biennial future routine-cost proxy. Do not stack them as one target.
4. Resolve the exact-scope gap: neither public proxy is the complete direct-plus-shared
   WAPDA work-order target; RHFS appliance expenditure is not separable.
5. Keep WASC seed private and never present public-harmonized labels as observed WAPDA
   outcomes.

Because AHS passed the requested volume gate, the NYC HPD fallback has not been opened.
HPD may be assessed later as complementary emergency/event evidence after semantic and
license review.

### Deferred (WAPDA operational extracts)

These remain desirable for future transfer validation if authorization appears, but they are **not** current blockers for building the public training corpus:

- Stable WAPDA property IDs on complaints, work orders, invoices, and ledger entries
- Completed WAPDA work orders with full cost lines and invoice–ledger reconciliation
- Authoritative WAPDA construction-year exports beyond seed adjudication
- Additional WASC colonies as operational training rows

### Strongly recommended (public or later WASC)

- Standardized complaint and inspection analogues
- Renovation and component-replacement history
- Occupancy periods without personal identifiers
- Plumbing, wiring and roof ages
- Monthly inflation, material and labour indices
- Site-level weather and rainfall

### Optional extended features

- Water and electricity usage
- Water quality, flood and waterlogging history
- Supplier and maintenance-office distance
- Building common-area condition
- Warranty history

## 11. Data that may be generated

The following should be derived reproducibly:

- Anonymized property and contractor IDs
- A–F/Cat-I–Cat-VI crosswalk for the WASC seed
- Canonical unit conversions
- Property age and component age at each cutoff
- Historical cost and repair aggregates
- Complaint and emergency counts
- Inflation-adjusted model features
- Shared-cost allocations (equal per active unit)
- Data-coverage, outlier and quality flags
- Training labels and high-cost rankings (top 20% within training fold)
- Public-source field mappings and remapped condition scores
- Model explanation fields and prediction intervals

**Prohibited:** inventing maintenance histories or labels with no documented public-source (or later authorized WAPDA) lineage, then presenting them as observed outcomes.

**Allowed:** harmonizing multiple real public datasets into the project schema with explicit transforms, provenance, and a dataset card that states construction method and limits.

**Test-only:** small synthetic rows for application tests, stored separately and labeled non-analytical.
