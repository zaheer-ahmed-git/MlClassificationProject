# Public Corpus Dataset Card: `public-corpus-v0.1.0-rhfs`

## Release status

This is the first implemented, local-analysis-only slice of the hybrid public corpus. It
contains real records from one approved source and is not yet the final multi-source training
release. Row-level redistribution remains disabled while source terms are reviewed. The raw
and processed files are intentionally ignored by version control; the registry, mapping,
schema, builder, tests, and this card are versioned.

The release passed all 18 implemented integrity, lineage, target, and privacy checks on
2026-08-08. Its use is limited to cross-sectional annual-cost exploration and pipeline
development. It must not be described as observed WAPDA data or as a validated
next-12-month WAPDA forecasting dataset.

## Source and population

- Source: 2024 Rental Housing Finance Survey public-use file, version 1.0.
- Publisher: United States Census Bureau.
- Native population and grain: sampled United States rental properties; one row per public
  survey property record.
- Outcome period: calendar year 2023.
- Official resources: [PUF landing page](https://www.census.gov/programs-surveys/rhfs/data/puf/2024/microdata.html),
  [CSV](https://www2.census.gov/programs-surveys/rhfs/data/public-use-files/2024/rhfspuf2024.csv),
  [codebook](https://www2.census.gov/programs-surveys/rhfs/data/public-use-files/2024/Codebook-Version-1.pdf),
  and [version document](https://www2.census.gov/programs-surveys/rhfs/data/public-use-files/2024/2024-RHFS-PUF-Version-Document.pdf).
- Raw CSV SHA-256: `dcc7c2331337bf10e3fa90027a30508c20268b7087d2c61d7e88a6dfbb3bf96f`.
- Authentic source properties: 4,425.
- Label-bearing properties after outcome checks: 1,488.
- Survey weights are retained as weights and are never expanded into replicated records.

## Implemented task and label

Task `annual_cost_estimation_v1` estimates the source record's 2023 maintenance-and-repair
expense (`OPREP`) from same-record property characteristics. This is a held-out
cross-sectional estimation task. It is not a future forecasting task.

A label is included only when:

1. `OPREP` is a nonnegative reported value rather than `-8`, `-9`, or blank.
2. A zero `OPREP` is accompanied by `PROPANS = 1`, providing explicit response evidence.
3. `OPREP` does not exceed `OPEX_R` where both are usable.

The build retained 32 explicit valid zeros and flagged 29 usable source-edited responses via
`JPREP`. It excluded 1,830 not-reported outcomes, 1,100 not-applicable outcomes, and 7
ambiguous zeros. No operating-expense reconciliation failure was found.

Capital variables are excluded. The public field does not separate appliance expenditure,
so every label is marked `annual_maintenance_proxy_appliance_unseparated`. Every label also
has `is_exact_wapda_target = false`, original currency `USD`, and public-survey origin.

## Features

The snapshot table contains 34 source-derived values, each paired with an explicit missing
reason. Feature groups are:

- Scale and layout: unit, building, bedroom, and bedroom-category counts.
- Age and rehabilitation: construction and rehabilitation year-band codes.
- Structure and use: condominium, townhouse/rowhouse, complex, commercial-space, parking,
  and historic-property codes.
- Ownership and management: ownership entity, management arrangement, and management hours.
- Programme and area context: rent control, subsidy, and low-income-area codes.
- Included services: electricity, gas, water, sewer, trash, parking, and pool codes.
- Occupancy and value: occupied/vacant units, market value, and value per unit.
- Descriptive analysis: survey weight.

The exact field-to-field contract is in `configs/mappings/rhfs_2024.toml`. Source codes are
retained without inventing semantic categories, while `-8`, `-9`, and blanks become explicit
missingness reasons.

## Tables and relationships

| Table | Rows | Grain |
|---|---:|---|
| `source_document.csv` | 3 | One immutable source artifact |
| `source_asset_bridge.csv` | 4,425 | One authentic tokenized source property |
| `property_period_snapshot.csv` | 4,425 | One property at the 2023-12-31 analytical cutoff |
| `annual_cost_observation.csv` | 1,488 | One usable 2023 maintenance observation |
| `property_period_label.csv` | 1,488 | One snapshot and task label |
| `record_lineage.csv` | 11,826 | One derived-record-to-source-row link |

Snapshots reference tokenized analytical assets; labels reference snapshots; lineage
references one of the three hashed source documents. The public native identifier is never
exported. A deterministic opaque asset token and raw-row SHA-256 support reproducibility
without copying the native identifier into analytical files.

## Quality and reproducibility

The release audit checks minimum sample size, uniqueness, foreign keys, label and observation
lineage, nonnegative costs, zero evidence, capital exclusion, operating-expense
reconciliation, public-versus-WAPDA claims, prohibited identifier headers, and processed-file
hashes. Test-only synthetic fixtures verify sentinel conversion, deterministic table hashes,
immutability, and deliberate checksum drift.

Rebuild from the repository root:

```bash
PYTHONPATH=src python3 -m caip_maintenance.data validate-raw --source rhfs_2024
PYTHONPATH=src python3 -m caip_maintenance.data harmonize --release public-corpus-v0.1.0-rhfs
PYTHONPATH=src python3 -m caip_maintenance.data audit-release --release public-corpus-v0.1.0-rhfs
```

Release directories are immutable. Use a new release identifier after any mapping,
eligibility, or transformation change.

## Intended and prohibited uses

Intended uses are public-source EDA, schema and pipeline validation, cross-sectional baseline
development, and comparison with later task-specific public sources. Prohibited uses include
claiming WAPDA provenance, representing the source outcome as an exact next-12-month label,
using the data for tenant or employee decisions, inferring resident identity, or publishing
row-level files before the redistribution review is approved.

## Known limitations and next collection work

- One source is implemented; nine candidates are registered but not yet acquired or approved.
- The sample covers U.S. rental properties, not Pakistani staff-colony residences.
- The label period overlaps the descriptive survey reference rather than following a June 30
  forecast cutoff.
- Appliance expense is not separable, so this slice does not meet the exact WASC appliance
  exclusion rule.
- Construction and rehabilitation dates are bands, not exact dates.
- This release has no longitudinal prior-cost features, condition inspections, complaints,
  weather joins, economic normalization, temporal split, or PKR scenario conversion.

AHS subsequently passed its official linkage, maintenance-field, volume, lineage, semantic,
and split gates as a separate longitudinal modeling view; see
`AHSPublicCorpusDatasetCard.md`. It does not change this RHFS release or permit the two
outcomes to be vertically stacked into a single undifferentiated target. NYC HPD remains
closed as a fallback and may be reviewed later only as complementary event evidence.
