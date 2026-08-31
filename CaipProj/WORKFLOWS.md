# Workflows

## Build and audit the implemented RHFS release

1. Validate the registry with
   `PYTHONPATH=src python3 -m caip_maintenance.data register-sources`.
2. Acquire the fixed source release with the registered `fetch` command, or confirm the
   expected ignored raw files are present.
3. Verify hashes and byte counts with
   `PYTHONPATH=src python3 -m caip_maintenance.data validate-raw --source rhfs_2024`.
4. Choose a new semantic release identifier if the mapping or transformation changed.
5. Build with `PYTHONPATH=src python3 -m caip_maintenance.data harmonize --release RELEASE`.
   Never delete or overwrite a completed release to reuse its name.
6. Audit with
   `PYTHONPATH=src python3 -m caip_maintenance.data audit-release --release RELEASE`.
7. Review `manifest.json`, `qa_build_summary.json`, and `qa_report.json` using aggregate
   evidence only; do not copy row-level outputs into version control or documentation.
8. Update the mapping, schema, dataset card, tests, and changelog together when the contract
   changes.

## Assess and build the implemented AHS release

1. Verify all official 2015, 2017, 2019, 2021, and 2023 PUF/codebook artifacts with
   `PYTHONPATH=src python3 -m caip_maintenance.data validate-raw --source ahs_2015_2023`.
2. Reproduce the hash-bound pre-adapter decision with
   `PYTHONPATH=src python3 -m caip_maintenance.data assess-ahs`.
3. Confirm the result remains GO with at least 500 distinct exact-`CONTROL` linked units;
   inspect aggregate counts only in `data/interim/gates/ahs_gate_result.json`.
4. Build a new immutable release with
   `PYTHONPATH=src python3 -m caip_maintenance.data harmonize --release public-corpus-v0.2.0-ahs`.
   Harmonization refuses a missing, stale, or no-go gate.
5. Audit with
   `PYTHONPATH=src python3 -m caip_maintenance.data audit-release --release public-corpus-v0.2.0-ahs`.
6. Verify the frozen decision in `Documentation/AHSSemanticLicenseDecision.md`; local
   analysis is approved, but redistribution remains blocked pending artifact-specific review.
7. Build the immutable grouped temporal assignment with
   `PYTHONPATH=src python3 -m caip_maintenance.data assign-splits --release public-corpus-v0.2.0-ahs --split ahs-grouped-temporal-v1`.
8. Audit completeness, terminal-wave rules, unit isolation, response-cap flags, and source
   hashes with `PYTHONPATH=src python3 -m caip_maintenance.data audit-split --release public-corpus-v0.2.0-ahs --split ahs-grouped-temporal-v1`.
9. Keep `future_routine_cost_proxy_v1` separate from RHFS, retain the 2023 cap-change
   metadata, never clip the target to USD 10,000, and do not export native `CONTROL` values.
10. Keep all row-level outputs `local-analysis-only` until redistribution review is complete.
11. Verify `Documentation/AHSPublicCorpusDatasetCard.md` against the release and split
    manifests and QA reports before building downstream artifacts.
12. Build immutable training-fold-only preprocessing with
    `PYTHONPATH=src python3 -m caip_maintenance.data preprocess-ahs --release public-corpus-v0.2.0-ahs --split ahs-grouped-temporal-v1 --preprocessor ahs-training-fold-v1`.
13. Audit the fitted state, transformed rows, target preservation, and source/config hashes
    with `PYTHONPATH=src python3 -m caip_maintenance.data audit-preprocessing --release public-corpus-v0.2.0-ahs --split ahs-grouped-temporal-v1 --preprocessor ahs-training-fold-v1`.
14. Create the pinned modeling environment from `requirements-modeling.txt`, then run the
    fixed raw-target comparison with `PYTHONPATH=src .venv/bin/python -m caip_maintenance.data train-ahs-experiment --release public-corpus-v0.2.0-ahs --split ahs-grouped-temporal-v1 --preprocessor ahs-training-fold-v1 --experiment ahs-baselines-models-v1`.
15. Audit source/output hashes, training-only fit evidence, reloaded predictions, metrics,
    views, and claim boundaries with `PYTHONPATH=src .venv/bin/python -m caip_maintenance.data audit-experiment --release public-corpus-v0.2.0-ahs --split ahs-grouped-temporal-v1 --preprocessor ahs-training-fold-v1 --experiment ahs-baselines-models-v1`.
16. Optionally run the same systems with a `log1p` model target and USD metrics after `expm1`
    using `--experiment ahs-baselines-models-log1p-v1`, then audit with the same command and
    that experiment id. See `Documentation/AHSBaselineModelLog1pExperiment.md`.
17. Record any semantic, eligibility, artifact, or count change in
   `Documentation/AHSGateDecision.md`, its mapping/schema, tests, and changelog.

## Add or update a source

1. Confirm authorization, purpose, coverage, owner, and PII classification.
2. Place the original in the protected raw-source area without modifying it.
3. Calculate a content hash and register the source metadata.
4. Define the source grain, keys, dates, units, and expected relationships.
5. Extract into an isolated staging output with source row/page/cell locators.
6. Redact prohibited personal data and tokenize sensitive business identifiers.
7. Normalize with controlled mappings while retaining redacted original values.
8. Run schema, key, date, cost, scope, privacy, and reconciliation checks.
9. Quarantine conflicts and low-confidence mappings for authorized review.
10. Update `CodexFindings.md` when sufficiency, conflicts, or collection gaps change.

Never append the residential ledger subset to the larger workbook, and never treat a
duplicated workbook sheet as additional evidence.

## Approve the data-readiness gate

1. Confirm WASC framing inventory reconciles to 101 residential units and approved exclusions.
2. Confirm target, equal-per-active-unit allocation, renovation dimensions, and top-20% high-cost
   policy are versioned.
3. Approve the public-source shortlist (5–10 candidates) and harmonization mapping specification.
4. Verify constructed corpus volume (>500 properties), eligible completed events, and lineage.
5. Confirm coverage flags distinguish zero from missing; censor incomplete periods.
6. Confirm privacy: no WASC PII in training exports; public labels not presented as WAPDA outcomes.
7. Reserve a final test period before model tuning.
8. Record a go/no-go decision. A no-go leads to a better public-source shortlist or narrowed
   claims—not undocumented invented labels.

## Implement a data or feature change

1. State the grain, inputs, output columns, cutoff behavior, and null semantics.
2. Identify source and target contracts affected.
3. Write unit and leakage boundary tests first where feasible.
4. Implement the transformation in the correct package layer.
5. Run targeted tests, then the data-contract and integration suites.
6. Compare row counts, missingness, distributions, and reconciliation before and after.
7. Update data documentation, configuration, and changelog when the contract changed.

## Train and compare models

1. Confirm the task's dataset card is published and current; for AHS use
   `Documentation/AHSPublicCorpusDatasetCard.md` and keep the task isolated from RHFS.
2. Freeze a versioned eligible snapshot/label manifest.
3. Define train, validation, and final test periods before model tuning.
4. Fit preprocessing and any high-cost threshold on training rows only.
5. Fit a historical baseline and document its prediction rule.
6. Train linear regression, Random Forest, and gradient boosting through identical
   preprocessing and split contracts.
7. Treat `ahs-baselines-models-v1` and `ahs-baselines-models-log1p-v1` as fixed, untuned
   comparisons. Any later tuning stage
   requires separate authorization and may use training/validation data only; do not inspect
   the final test set repeatedly.
8. Report MAE, RMSE, high-cost retrieval metrics, sample counts, and subgroup diagnostics.
9. Review residuals, survey-weight sensitivity, temporal/cap drift, and decision utility
   before authorizing any selection or tuning stage. For AHS, use
   `review-ahs-diagnostics` / `audit-diagnostic-review` and
   `Documentation/AHSDiagnosticReview.md`.
10. Save every compared fitted estimator with the experiment manifest; do not label one the
    winner when selection was disabled or the metrics disagree.
11. Promote an artifact only after data, model, privacy, reproducibility, intended-use, and
    selection-policy review. For AHS, follow `Documentation/AHSSelectionPolicy.md`: primary
    objective is validation MAE; sensitivity MAE and high-cost F1 are required secondaries;
    promote a fitted model only if it wins validation MAE and also leads or ties sensitivity
    MAE; otherwise report `type_median` and `prior_cost`.

## Change the target or allocation policy

1. Obtain the business rationale and approving owner.
2. Version the target or allocation policy rather than overwriting history.
3. Identify affected labels, experiments, metrics, reports, and application language.
4. Add boundary, arithmetic, and backward-compatibility tests.
5. Rebuild labels and rerun comparisons from governed sources.
6. Update `ARCHITECTURE.md`, `TESTING.md`, and the report methodology.
7. Do not compare metrics across target versions as if they used the same outcome.

## Add or change the web POC

1. Define the user decision and minimum non-personal inputs.
2. Keep prediction logic behind a framework-neutral service interface.
3. Load only a reviewed model bundle with a compatible feature schema.
4. Add input, missing-coverage, model-load, and explanation tests.
5. Verify that estimates show nominal PKR, cutoff, model version, and limitations.
6. Test desktop and mobile layouts without exposing raw narrations or identities.
7. Confirm the application cannot trigger training or mutate governed source data.

## Fix a bug

1. Reproduce the observable failure.
2. Determine whether data, target, model, UI, or documentation contracts are involved.
3. Add a focused regression test when feasible.
4. Apply the smallest complete correction.
5. Rerun the reproduction and relevant targeted tests.
6. Review for leakage, privacy, and downstream artifact impact.
7. Record the fix in `CHANGELOG.md` when user-visible or methodologically material.

## Update documentation

1. Find the canonical document for the changed fact.
2. Update it and replace stale duplication with a link where possible.
3. Check references from `AGENTS.md` and `README.md` if navigation changed.
4. Verify relative paths, headings, commands, dates, and current-versus-planned wording.
5. Update `CHANGELOG.md` for material policy or architecture changes.

## Prepare the CAIP final submission

1. Freeze the dataset and experiment manifests used by the report.
2. Re-run the documented end-to-end evaluation in a clean environment.
3. Reconcile every reported table and figure to recorded aggregate outputs.
4. Write the report sections required by the CAIP brief and keep the main report to 5-8
   pages excluding references, figures, and appendices.
5. Include 5-10 IEEE-formatted scholarly or industry references.
6. Run privacy, plagiarism/citation, spelling, formatting, and PDF checks.
7. Attach complete code as an annex and provide the Python source separately for testing.
8. Use the deadline and submission address from the authoritative CAIP brief; re-check them
   before submission rather than relying on an old planning note.

## Local review

1. Inspect the complete changed-file set.
2. Apply `CODE_REVIEW.md` in risk order.
3. Run the smallest relevant checks and any broader contract suite required by the change.
4. Distinguish new failures from pre-existing limitations.
5. Summarize what changed, evidence, commands, results, risks, and remaining assumptions.
