# AHS Longitudinal Gate Decision

## Decision

**GO, recorded 2026-08-08.** The official 2015, 2017, 2019, 2021, and 2023
American Housing Survey (AHS) national public-use files produce **36,623 distinct
linked housing units** and **86,125 eligible adjacent-wave feature-to-label pairs**
after the documented filters. This exceeds the required gate of 500 distinct units.

The approved output is the separate local release
`public-corpus-v0.2.0-ahs` for task `future_routine_cost_proxy_v1`. It is not
merged with the RHFS outcome, is not an exact WAPDA target, and remains
`local-analysis-only` while redistribution terms are reviewed. The NYC HPD
fallback is therefore not opened by this gate; HPD may be assessed later as
complementary event evidence after a short semantic and license review.

## Official evidence

The artifacts and their exact SHA-256 hashes and byte counts are registered in
`configs/sources.toml`. All 28 registered AHS artifacts passed local integrity
validation. They include five national PUF archives, the five wave-specific mini
codebooks, definitions, historical-changes documents and item booklets, plus the
codebook reference and Sample Case History documentation/data.

- The official [Sample Case History documentation](https://www2.census.gov/programs-surveys/ahs/documentation/Sample%20Case%20History%20File%202015%20to%202023.pdf)
  states that there is one record per sample case, that `CONTROL` uniquely identifies
  the sample case, and that `CONTROL` can merge the case-history file with AHS PUFs.
  Every selected PUF household table contains `CONTROL`.
- The official wave mini codebooks available from the Census Bureau's
  [AHS codebooks page](https://www.census.gov/programs-surveys/ahs/tech-documentation/codebooks.html)
  define `MAINTAMT` as annual routine-maintenance cost and `JMAINTAMT` as its edit
  flag. These fields exist in all five selected household files.
- The official [2023 Historical Changes document](https://www2.census.gov/programs-surveys/ahs/2023/2023%20AHS%20Historical%20Changes.pdf)
  records that the maximum response increased from USD 10,000 in 2021 to USD
  100,000 in 2023. The eligible PUF values reproduce this discontinuity: the
  observed maximum is 9,998 through 2021 and 99,998 in 2023.
- The AHS definitions describe routine maintenance as preventive care of the
  structure, property, and fixed equipment, while excluding housecleaning,
  additions, renovations, remodeling, and replacements. This is closer to the
  project scope than a general operating-expense outcome, but it is still a
  self-reported U.S. survey proxy rather than verified WAPDA work-order cost.

The proof uses the official documentation and actual PUF schemas; no linkage key or
label field was inferred from field names alone.

## Gate method and result

An earlier-wave row is feature-eligible when `INTSTATUS=1` and `YRBUILT`,
`UNITSIZE`, `TOTROOMS`, `BATHROOMS`, and `BLD` are usable. A later-wave row is
label-eligible when `INTSTATUS=1`, `TENURE` is 1 or 2, and `MAINTAMT` is usable
and nonnegative. Missing codes are blank, `-6`, `-7`, `-8`, `-9`, and `N`.
Pairs use an exact `CONTROL` match between adjacent national waves. Counts refer
to authentic records; survey weights are retained as weights and are not used to
replicate rows.

| Feature wave | Label wave | Eligible pairs |
|---:|---:|---:|
| 2015 | 2017 | 22,715 |
| 2017 | 2019 | 22,667 |
| 2019 | 2021 | 21,290 |
| 2021 | 2023 | 19,453 |
| **Total pairs** |  | **86,125** |

The total contains repeated transitions for the same unit; the gate denominator is
therefore the separately deduplicated **36,623 distinct linked units**.

| Wave | Household rows | Complete earlier-feature rows | Eligible owner-label rows | Eligible `MAINTAMT` maximum |
|---:|---:|---:|---:|---:|
| 2015 | 69,493 | 47,213 | 31,101 | 9,998 |
| 2017 | 66,752 | 51,178 | 30,621 | 9,998 |
| 2019 | 63,185 | 49,753 | 29,040 | 9,998 |
| 2021 | 64,141 | 49,597 | 28,094 | 9,998 |
| 2023 | 55,669 | 43,716 | 25,183 | 99,998 |

The aggregate, hash-bound gate result is written to the ignored path
`data/interim/gates/ahs_gate_result.json`. Harmonization refuses to proceed if the
gate is missing, is a no-go, or no longer matches the PUF archive hashes.

## Release contract

The release contains 36,623 tokenized assets, 86,125 earlier-wave snapshots,
86,125 later-wave labels, 86,125 normalized cost observations, 294,998 lineage
records, and 28 source-document records. It contains 11,648 explicit zero
responses. Native `CONTROL` values are never exported.

The retained earlier-wave feature set is declared in
`configs/mappings/ahs_2015_2023.toml`; the table contract is in
`configs/schemas/public_corpus_v0.2_ahs.json`. Each label retains its feature wave,
label wave, source response maximum, USD currency, public-survey origin, coverage
status, and explicit `is_exact_wapda_target=false` marker. The release audit passes
21 checks, including minimum distinct assets, task isolation, later-wave ordering,
cap metadata, source lineage, identifier exclusion, and output checksums.

Reproduction commands:

```bash
PYTHONPATH=src python3 -m caip_maintenance.data validate-raw --source ahs_2015_2023
PYTHONPATH=src python3 -m caip_maintenance.data assess-ahs
PYTHONPATH=src python3 -m caip_maintenance.data harmonize --release public-corpus-v0.2.0-ahs
PYTHONPATH=src python3 -m caip_maintenance.data audit-release --release public-corpus-v0.2.0-ahs
```

`harmonize` creates an immutable ignored release and will not overwrite an existing
directory. Use a new semantic release identifier when the mapping or transformation
changes.

## Interpretation limits before modeling

- AHS is a U.S., USD, self-reported survey view. Its later-wave “typical year” amount
  is separated by two survey years from the feature wave; it is not a directly
  observed next-12-calendar-month ledger interval.
- The 2023 response-cap change is an instrument discontinuity. It must be retained in
  features/metadata and addressed in split design and sensitivity analysis; values
  must not be silently clipped to the earlier cap.
- Explicit survey zeros are valid completed responses for this proxy task, not proof
  that a WAPDA operational ledger had complete work-order coverage.
- The source construct excludes renovation/remodeling and personal housecleaning, but
  includes fixed-equipment maintenance. It must not be generalized to personal
  appliance cost or to all corrective/emergency work.
- Multiple transitions from one `CONTROL` must remain in the same data split. The
  implemented `ahs-grouped-temporal-v1` contract assigns the entire unit history from
  its terminal eligible label-wave cohort: 2023 to test, 2021 to validation, and
  2017/2019 to training. This preserves zero unit overlap across splits.
- This gate did not authorize AHS/RHFS label stacking, PKR conversion, EDA, modeling,
  or a “final model” claim. The frozen semantic/license decision is recorded in
  `Documentation/AHSSemanticLicenseDecision.md`; redistribution remains under the
  repository's `local-analysis-only` hold. Subsequent separately authorized stages
  completed the dataset card, training-fold-only preprocessing, and one fixed baseline/model
  comparison. None of those stages authorizes label stacking or a final-model claim.
