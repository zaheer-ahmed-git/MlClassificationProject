# Public Corpus Dataset Card: `public-corpus-v0.2.0-ahs`

## Release status

`public-corpus-v0.2.0-ahs` is a frozen, local-analysis-only longitudinal proxy release for
task `future_routine_cost_proxy_v1`. It contains harmonized records from official United
States American Housing Survey (AHS) public-use files. It is **not WAPDA data**, not a
validated WASC forecast, and not an exact next-12-month work-order or cost ledger.
`is_exact_wapda_target` is false for every label.

The release passed all 21 implemented release checks, its frozen
`ahs-grouped-temporal-v1` assignment passed all 16 split checks on 2026-08-08, and
`ahs-training-fold-v1` passed all 11 preprocessing checks on 2026-08-09. The downstream
fixed comparison `ahs-baselines-models-v1` passed all 11 experiment-artifact checks on
2026-08-10. The parallel log1p-target comparison `ahs-baselines-models-log1p-v1` passed the
same 11 checks on 2026-08-20; see `Documentation/AHSBaselineModelLog1pExperiment.md`.
This does not establish a final CAIP model or a WAPDA application.

Raw AHS artifacts, harmonized row files, and split assignments remain
`local-analysis-only` while artifact-specific redistribution review is pending. They must
not be committed, uploaded, or redistributed. Versioned code, schemas, aggregate counts,
and non-disclosive documentation may be reviewed.

## Source, waves, and grain

- Source: American Housing Survey national Public Use Files, 2015, 2017, 2019, 2021, and
  2023.
- Publisher: United States Census Bureau and U.S. Department of Housing and Urban
  Development.
- Registered source: `ahs_2015_2023`, release `official_2015_2023`.
- Native grain: one housing unit in one biennial national PUF wave.
- Native longitudinal key: `CONTROL`, documented as the sample-case identifier used to
  link AHS waves. It is never exported; the release uses a deterministic namespace token.
- Analytical grain: one eligible housing unit observed in an earlier wave, paired with its
  eligible routine-maintenance response in the next adjacent wave two years later.
- Amount basis: respondent-reported nominal USD for routine maintenance in a typical year.
- Official resources: [AHS 2023 data landing page](https://www.census.gov/programs-surveys/ahs/data/2023.html),
  [AHS codebooks](https://www.census.gov/programs-surveys/ahs/tech-documentation/codebooks.html),
  [2015–2023 sample case history](https://www2.census.gov/programs-surveys/ahs/documentation/Sample%20Case%20History%20File%202015%20to%202023.pdf),
  [2023 historical changes](https://www2.census.gov/programs-surveys/ahs/2023/2023%20AHS%20Historical%20Changes.pdf),
  and [Census citation guidance](https://www.census.gov/about/policies/citation.html).

The five source PUF archives are pinned as follows:

| Wave | Official PUF archive | SHA-256 |
|---:|---|---|
| 2015 | [2015 AHS National PUF v3.1 CSV](https://www2.census.gov/programs-surveys/ahs/2015/2015%20AHS%20National%20PUF%20v3.1%20CSV.zip) | `cacf86b94fa953a7a7b3ea3f2f55b0f2520464dcd01f689af4726dd9e670bc9e` |
| 2017 | [2017 AHS National PUF v3.1 CSV](https://www2.census.gov/programs-surveys/ahs/2017/2017%20AHS%20National%20PUF%20v3.1%20CSV.zip) | `58927493c9012be61b00345b5d6e2533ae5678891e6d041b755455b18b7eb97b` |
| 2019 | [2019 AHS National PUF v1.1 CSV](https://www2.census.gov/programs-surveys/ahs/2019/2019%20AHS%20National%20PUF%20v1.1%20CSV.zip) | `6d2eb9e81b896e6bbeb1b7a8e4a099ed2598ddeb0323af04f810b76b1746def9` |
| 2021 | [2021 AHS National PUF v1.0 CSV](https://www2.census.gov/programs-surveys/ahs/2021/2021%20AHS%20National%20PUF%20v1.0%20CSV.zip) | `73a464118cfa4bbf962c22bde4e7e40349f6673eafc381d0b257b0d309c2d622` |
| 2023 | [2023 AHS National PUF v1.1 CSV](https://www2.census.gov/programs-surveys/ahs/2023/2023%20AHS%20National%20PUF%20v1.1%20CSV.zip) | `720aaa18198f23f1d25b19630ba97105394f653f32acf6e3f907235bd2d73ac0` |

The complete 28-artifact inventory—including wave-specific mini-codebooks, definitions,
item booklets, historical-change documents, and case-history files—with official URLs,
byte counts, and SHA-256 digests is canonical in `configs/sources.toml`. All 28 local raw
artifacts passed the registered hash and size checks. The release manifest also pins the
hashes of every processed table.

## Task and label contract

Task `future_routine_cost_proxy_v1` uses features from an earlier eligible AHS wave and the
next adjacent wave's `MAINTAMT` response as the label. `JMAINTAMT` is registered and used as
the source edit/status flag; it is not exported as a second outcome. Eligible transitions are 2015→2017,
2017→2019, 2019→2021, and 2021→2023.

An earlier-wave record is eligible when `INTSTATUS = 1` and `YRBUILT`, `UNITSIZE`,
`TOTROOMS`, `BATHROOMS`, and `BLD` are usable. The later-wave response is eligible when
`INTSTATUS = 1`, `TENURE` is 1 or 2, and `MAINTAMT` is usable, nonnegative, and not a
registered missing sentinel or blank. Target imputation is prohibited.

The build retains 11,648 zero labels. Each is an explicit eligible survey response; it is
not evidence that a WAPDA work-order or ledger system had complete coverage and recorded no
eligible maintenance.

The source response maximum is USD 10,000 for label waves through 2021 and USD 100,000 for
2023. `label_wave_year` and `source_response_maximum_usd` preserve this discontinuity. The
target must never be silently clipped to USD 10,000.

Eligible adjacent-wave counts are:

| Feature wave | Label wave | Eligible pairs |
|---:|---:|---:|
| 2015 | 2017 | 22,715 |
| 2017 | 2019 | 22,667 |
| 2019 | 2021 | 21,290 |
| 2021 | 2023 | 19,453 |
| **Total** |  | **86,125** |

## Feature set and schema

The snapshot contains 26 source-derived features, with explicit source sentinels converted
to missing values and recorded missing reasons. The feature groups are:

- Structure and layout: building type, year built, unit size, rooms, bathrooms, bedrooms,
  unit floors, foundation, garage, and lot characteristics.
- Building systems: heating type and fuel, primary air conditioning, and sewage type.
- Condition evidence: roof leak, hole, sag, and shingle condition, plus sewage breakdown.
- Occupancy and economic context: tenure and household income.
- Geography and survey design: Census division, CBSA code, and survey weight.
- Prior-cost history: earlier-wave routine-maintenance amount only; the later-wave
  `MAINTAMT` remains the label and is never used as a feature.

Exact field mappings, source names, types, eligibility, missing sentinels, and label rules
are in `configs/mappings/ahs_2015_2023.toml`. Table keys, task grain, temporal contract,
response limits, privacy rules, and distribution status are in
`configs/schemas/public_corpus_v0.2_ahs.json`. The frozen split contract is in
`configs/splits/ahs_grouped_temporal_v1.toml`, with its table schema in
`configs/schemas/ahs_split_assignment_v1.json`.

Survey weights remain weights and are never expanded into replicated housing units.

## Tables, relationships, and lineage

| Table | Rows | Grain |
|---|---:|---|
| `source_document.csv` | 28 | One registered immutable AHS source artifact |
| `source_asset_bridge.csv` | 36,623 | One authentic tokenized AHS housing unit |
| `property_period_snapshot.csv` | 86,125 | One unit at an eligible earlier-wave cutoff |
| `annual_cost_observation.csv` | 86,125 | One eligible later-wave `MAINTAMT` response |
| `property_period_label.csv` | 86,125 | One snapshot and AHS proxy-task label |
| `record_lineage.csv` | 294,998 | One derived-record-to-source-row/document link |

The bridge maps each native housing unit to one opaque analytical asset without exporting
`CONTROL`. Each snapshot references that asset. Each label references exactly one snapshot
and its corresponding later-wave cost observation. Lineage links derived records to one of
the 28 hash-pinned source documents and preserves source wave, row locator, and transform
provenance. The release audit confirms uniqueness, foreign keys, complete label and cost
lineage, task isolation, later-wave ordering, response-cap metadata, identifier removal,
and processed-file hashes.

## Frozen split: `ahs-grouped-temporal-v1`

All transitions for one tokenized housing unit stay in one split. Assignment is based on
the unit's latest eligible label wave: terminal 2023 units go to test, terminal 2021 units
to validation, and terminal 2017 or 2019 units to training. Consequently, test and
validation include earlier transitions belonging to their terminal-wave units; this is a
grouped terminal-cohort split, not an independent row-by-wave partition.

| Split | Distinct units | Transition rows |
|---|---:|---:|
| Training | 10,103 | 13,871 |
| Validation | 7,067 | 15,400 |
| Test | 19,453 | 56,854 |
| **Total** | **36,623** | **86,125** |

The audit reports **unit leakage = 0** and all 16 checks passing. Region and housing type
are represented by Census division and building-type strata in the split manifest; counts
are reported for audit, but the deterministic assignment is not rebalanced. No model
threshold is stored in the assignment. Any imputer, encoder, scaler, feature selector,
high-cost cutoff, or model must be fitted on training rows only.

## Training-fold-only preprocessing: `ahs-training-fold-v1`

The frozen preprocessing artifact fits on the 13,871 training assignments only, then
transforms all 86,125 assigned rows. Numeric values use training medians followed by
training-population standard scaling. Categorical values use a training-only vocabulary
with fixed missing and unknown buckets. Every candidate feature receives an explicit
missingness indicator. A value representation is retained only when its training-fold
missing rate is at most 40%; `roof_leak_code` is the sole excluded value representation,
while its missingness indicator remains available.

The high-cost threshold is USD 1,428, calculated as the nearest-rank 80th percentile of
training labels only. Labels at or above that threshold are marked high-cost; ties can make
the marked share differ from exactly 20%. Validation and test values, categories,
missingness rates, and labels do not affect any fitted artifact.

`target_metadata.csv` preserves each original target value, label wave, response maximum,
cap regime, and primary/sensitivity flags. Target imputation and target clipping are both
explicitly false. `feature_matrix.csv` contains no target. The manifest records
`model_fitted=false`; this stage is feature preparation, not modeling.

## Primary and cap-sensitivity views

| View | Rows | Rule |
|---|---:|---|
| Primary | 86,125 | Include every eligible transition with its original label; no target clipping |
| Pre-2023-cap sensitivity | 66,672 | Exclude all 19,453 transitions whose label wave is 2023 |

Any later evaluation must report results on both views. The sensitivity view diagnoses the
instrument change; it does not redefine or overwrite the primary dataset.

The first downstream comparison reports both views in
`Documentation/AHSBaselineModelExperiment.md`. It remains a separate local-only experiment;
its existence does not change this release's label semantics, distribution hold, or claim
boundary. The follow-on residual/subgroup/weight/utility review is documented in
`Documentation/AHSDiagnosticReview.md` and likewise does not promote a model.

## Intended uses

- Local, aggregate-safe exploratory analysis of the AHS proxy task.
- Leakage-safe feature engineering through the frozen training-fold-only preprocessing
  artifact.
- AHS-only baseline and model comparisons for `future_routine_cost_proxy_v1` using that
  audited artifact.
- Primary-versus-pre-2023-cap sensitivity analysis.
- Schema, lineage, split, and pipeline validation using real public-source records.

## Prohibited uses and fidelity limits

- Do not describe any row, label, estimate, or model result as observed WAPDA data or a
  validated WASC forecast.
- Do not describe `MAINTAMT` as a verified next-12-month WAPDA work-order ledger. It is a
  later-wave, typical-year, self-reported U.S. survey amount, and AHS waves are two years
  apart.
- Do not vertically stack AHS labels with RHFS labels or place both into one
  undifferentiated target column.
- Do not convert USD values to PKR and describe them as observed WAPDA costs. Any later
  conversion must be a separately documented scenario transform.
- Do not silently clip 2023 labels, impute targets, infer native identities, or use the data
  for resident, tenant, or employee decisions.
- Do not redistribute raw AHS artifacts, harmonized rows, or split assignments until an
  authorized artifact-specific review changes the current hold.
- Do not call this a final CAIP model dataset or use it to authorize budgets, procurement,
  maintenance work, or other operational decisions.

Fidelity to the WASC target is partial. AHS covers routine upkeep and attached fixed
equipment and excludes housecleaning, additions, renovations, remodeling, and replacement.
It has no verified work orders for corrective or emergency maintenance. Personal-appliance
treatment is not sufficiently separable to claim compliance with the WASC appliance
exclusion. The population is U.S. housing rather than Pakistani staff-colony residences.
The authoritative interpretation and distribution boundaries are frozen in
`Documentation/AHSSemanticLicenseDecision.md`.

## Rebuild and audit

Run from the repository root:

```bash
PYTHONPATH=src python3 -m caip_maintenance.data validate-raw --source ahs_2015_2023
PYTHONPATH=src python3 -m caip_maintenance.data assess-ahs
PYTHONPATH=src python3 -m caip_maintenance.data harmonize --release public-corpus-v0.2.0-ahs
PYTHONPATH=src python3 -m caip_maintenance.data audit-release --release public-corpus-v0.2.0-ahs
PYTHONPATH=src python3 -m caip_maintenance.data assign-splits --release public-corpus-v0.2.0-ahs --split ahs-grouped-temporal-v1
PYTHONPATH=src python3 -m caip_maintenance.data audit-split --release public-corpus-v0.2.0-ahs --split ahs-grouped-temporal-v1
PYTHONPATH=src python3 -m caip_maintenance.data preprocess-ahs --release public-corpus-v0.2.0-ahs --split ahs-grouped-temporal-v1 --preprocessor ahs-training-fold-v1
PYTHONPATH=src python3 -m caip_maintenance.data audit-preprocessing --release public-corpus-v0.2.0-ahs --split ahs-grouped-temporal-v1 --preprocessor ahs-training-fold-v1
PYTHONPATH=src .venv/bin/python -m caip_maintenance.data train-ahs-experiment --release public-corpus-v0.2.0-ahs --split ahs-grouped-temporal-v1 --preprocessor ahs-training-fold-v1 --experiment ahs-baselines-models-v1
PYTHONPATH=src .venv/bin/python -m caip_maintenance.data audit-experiment --release public-corpus-v0.2.0-ahs --split ahs-grouped-temporal-v1 --preprocessor ahs-training-fold-v1 --experiment ahs-baselines-models-v1
PYTHONPATH=src .venv/bin/python -m caip_maintenance.data train-ahs-experiment --release public-corpus-v0.2.0-ahs --split ahs-grouped-temporal-v1 --preprocessor ahs-training-fold-v1 --experiment ahs-baselines-models-log1p-v1
PYTHONPATH=src .venv/bin/python -m caip_maintenance.data audit-experiment --release public-corpus-v0.2.0-ahs --split ahs-grouped-temporal-v1 --preprocessor ahs-training-fold-v1 --experiment ahs-baselines-models-log1p-v1
.venv/bin/python -m unittest discover -s tests -v
```

Harmonized releases, split directories, and preprocessing directories are immutable. The
`harmonize`, `assign-splits`, and `preprocess-ahs` commands create artifacts and therefore
refuse an already-existing output. Use the audit commands for the frozen local release. If source artifacts, mappings,
eligibility, semantics, schemas, or split rules change, create new versioned release,
decision, and split identifiers instead of overwriting this one.

The release manifest is
`data/processed/releases/public-corpus-v0.2.0-ahs/manifest.json`; its SHA-256 as pinned by
the split is `2f6108687a6d9b0195079f2ff51e9fcf2179a65cd99522ee0add7f46879dc8a2`.
The split manifest is
`data/processed/splits/public-corpus-v0.2.0-ahs/ahs-grouped-temporal-v1/split_manifest.json`,
and the assignment SHA-256 is
`51dbd2f4f43474ffae752fa992a2bdd9815f77332e4c6b3bdaf48ed8bceb00f4`.
