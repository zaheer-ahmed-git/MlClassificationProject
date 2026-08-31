# AHS Semantic and License Decision

**Decision ID:** `ahs-semantic-license-v1`  
**Status:** Frozen for `public-corpus-v0.2.0-ahs`  
**Decision date:** 2026-08-08  
**Task:** `future_routine_cost_proxy_v1`

## Decision

The official 2015–2023 American Housing Survey (AHS) national Public Use Files may be
used for local analysis and for the separate AHS proxy task. The Census Bureau describes
the PUF as microdata made for custom tabulation, with one housing-unit record and direct
identifiers removed, and asks users to cite the Census Bureau as the original source when
publishing estimates. These statements establish the intended analytical use of the PUF.

They do not, by themselves, provide this project with a reviewed, artifact-specific
redistribution decision covering copied row-level PUF data or the derived row-level release.
Accordingly, the repository's conservative distribution status remains
`local-analysis-only`: raw AHS files, harmonized rows, and split assignments must not be
committed, uploaded, or redistributed until an authorized license review records approval.
This is an internal governance hold, not a claim that the Census Bureau prohibits analysis.
Code, schemas, aggregate counts, and non-disclosive documentation may remain reviewable.

Official references used for this decision:

- U.S. Census Bureau, [AHS 2023 National Public Use File](https://www.census.gov/programs-surveys/ahs/data/2023/ahs-2023-public-use-file--puf-/ahs-2023-national-public-use-file--puf-.html).
- U.S. Census Bureau, [Citing our Data, Tools, Technical Documents and Research](https://www.census.gov/about/policies/citation.html).
- The hash-pinned AHS codebooks, definitions, historical-change documents, and case-history
  files registered in `configs/sources.toml` and summarized in
  `Documentation/AHSGateDecision.md`.

## Outcome semantics and fidelity

For each eligible pair, features come from an earlier AHS wave and the label is the later
wave's `MAINTAMT` response. The field represents the respondent's annual routine
maintenance cost for a **typical year**. Because waves are two years apart, this is a
biennial next-wave proxy; it is not a verified sum of work orders during the immediately
following 12 months.

The AHS wording includes routine upkeep and fixed equipment attached to the home. It
excludes housecleaning, additions, renovations, remodeling, and replacement. Relative to
the approved WASC target, the overlap is useful but incomplete: fixed equipment is in scope
for AHS, major renovation is out, and no source work order proves corrective or emergency
maintenance. Personal-appliance treatment is not sufficiently separable to claim full
alignment with the WASC rule that personal appliances are always excluded.

An eligible zero is retained as an explicit survey response under the AHS eligibility
rules. It is **not** evidence that a WAPDA ledger or work-order system had complete coverage
and found no eligible cost.

The source response maximum is recorded per label. It is USD 10,000 through the 2021 wave
and USD 100,000 in 2023. Values must never be silently clipped back to USD 10,000. Any
evaluation must report the complete eligible set and a sensitivity view that excludes
2021-to-2023 labels.

## Required claim language

- Keep `task_id=future_routine_cost_proxy_v1`.
- Keep `is_exact_wapda_target=false` for every AHS label.
- Describe amounts as public U.S. survey responses in nominal USD, not PKR and not observed
  WAPDA outcomes.
- Keep AHS separate from RHFS and from any future WASC operational label table.
- Do not call this release a validated WASC forecast, a WAPDA next-12-month ledger, or a
  final CAIP model dataset.

## Change control

This decision is frozen as version `ahs-semantic-license-v1`. The split specification pins
the file's SHA-256 digest. Any semantic, claim, or distribution change requires a new
decision version, a new split specification version, affected contract tests, and a
changelog entry; the existing decision must not be edited in place after a split artifact
has been built.
