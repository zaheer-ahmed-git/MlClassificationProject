# Coding Standards

## Principles

The implementation should favor correctness, auditability, and reproducibility over clever
abstractions. Write code that makes dates, units, inclusion policies, missingness, and data
lineage visible. Use the smallest dependency set that supports the CAIP POC.

These conventions become enforceable when the Python project is scaffolded. Until then,
they define the target implementation style.

## Python and packaging

- Use an installable `src/` package named `caip_maintenance` and declare supported Python
  versions in `pyproject.toml`.
- Keep dependencies and tool configuration in `pyproject.toml`; do not rely on undeclared
  global packages.
- Prefer standard library modules and established pandas/scikit-learn APIs.
- Pin top-level dependencies for the submitted environment and record a reproducible lock
  or requirements export.
- Use four spaces in Python, UTF-8, LF line endings, and final newlines.

## Naming and organization

- Use `snake_case` for modules, functions, variables, table names, and column names.
- Use `PascalCase` for classes and `UPPER_SNAKE_CASE` for true constants.
- Include units and time windows in analytical names, for example `covered_area_sqft`,
  `cost_last_12m_pkr`, and `rainfall_mm`.
- Distinguish event dates, cutoff dates, and label interval boundaries explicitly.
- Keep modules focused on one layer from `ARCHITECTURE.md`; avoid generic `utils.py`
  collections when a domain-specific module name is possible.

## Types and contracts

- Type public functions and data-transfer objects.
- Validate external inputs at ingestion and application boundaries.
- Represent controlled categories with one canonical mapping or enum-like contract.
- Use timezone-aware timestamps where time-of-day matters and ISO dates for day-grain data.
- Use decimal-safe arithmetic or integer minor units for audited money calculations. Convert
  to floating point only at the modeling boundary when required by the library.
- Make null semantics explicit. Unknown, not applicable, not collected, and confirmed zero
  are different states.

## Data transformations

- Each transformation takes defined inputs and returns a new output; do not mutate raw
  source files or depend on notebook execution order.
- Retain source identifiers and locators through normalization.
- Validate units before conversion and preserve the redacted original value when useful for
  audit.
- Keep target construction separate from feature construction.
- Store cutoff-aware joins and rolling windows in package code with boundary tests.
- Fit any learned transform only on a training partition, preferably inside a scikit-learn
  `Pipeline` or `ColumnTransformer`.
- Do not delete valid high-cost records merely because they are statistical outliers. Record
  review flags and justify any modeling transform.

## Errors and logging

- Fail loudly on schema mismatch, impossible dates, broken keys, cost imbalance, or leakage.
- Use structured exceptions with actionable messages; do not silently coerce invalid values.
- Log counts, source IDs, and aggregate diagnostics, not resident names or raw narrations.
- Do not log secrets, personal identifiers, full invoices, or row-level predictions tied to a
  person.
- Make quarantined and skipped records measurable with reason codes.

## Modeling

- Implement a historical baseline before trained models.
- Keep split generation independent from model selection.
- Set and record random seeds for stochastic algorithms.
- Compare models on identical eligible rows, features, and splits.
- Calculate high-cost thresholds from training data only unless an approved fixed business
  threshold is supplied.
- Persist preprocessing and model components together with their schema and metadata.
- Explanations must match the exact stored model and transformed feature set.

## Application code

- Keep the web framework at the edge; the UI calls typed prediction services.
- Validate property identifiers and feature completeness server-side.
- Escape or avoid free text from source documents.
- Present nominal PKR consistently and label estimates, intervals, cutoffs, and model version.
- Do not expose raw identifiers, resident details, or internal filesystem paths.

## Tests

- Name tests for observable behavior, including the relevant boundary or invariant.
- Prefer small synthetic fixtures for logic tests; label them as test-only.
- No fabricated records presented as real WAPDA evidence.
- Public-harmonized training rows must carry lineage and must not be labeled as observed
  WAPDA operational outcomes.
- Never copy production PII into fixtures or snapshots.
- Add regression tests for every repaired defect where feasible.
- Follow the layers and mandatory data-quality checks in `TESTING.md`.

## Anti-patterns

- No training directly from an ad hoc spreadsheet path in UI or notebook code.
- No business or target logic in a web callback.
- No random row split of overlapping property-period records.
- No inferred zero target from an absent ledger row.
- No imputation, scaling, feature selection, or thresholding before the training split.
- No manual editing of generated metrics, figures, processed tables, or model artifacts.
- No fabricated records presented as real WAPDA evidence.
