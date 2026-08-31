# Code Review

## Review order

Review for correctness and harm before style. Lead with blocking findings, cite the affected
file and location, and distinguish evidence from assumptions.

1. Target and data correctness.
2. Leakage and evaluation integrity.
3. Privacy and security.
4. Behavioral regressions and compatibility.
5. Tests and reproducibility.
6. Application clarity and documentation.

## Correctness

- Is the data grain explicit and preserved?
- Are dates, units, nulls, identifiers, and monetary signs interpreted correctly?
- Does target eligibility match the versioned contract?
- Is zero distinguished from unknown or incomplete coverage?
- Are direct and shared costs reconciled without duplication?
- Are source conflicts quarantined instead of silently overwritten?
- Does the change stay inside the approved residential asset scope?

## Leakage and model validity

- Can any feature observe the label interval or a future-revised value?
- Are preprocessing and threshold decisions fitted on training data only?
- Are time and group splits suitable for the decision being claimed?
- Are all model comparisons made on the same rows, target, features, and splits?
- Do metrics, sample counts, uncertainty, and subgroup results support the written claim?
- Does the baseline provide a meaningful minimum standard?
- Are explanations generated from the exact promoted pipeline?

## Security and privacy

- Does the diff expose names, CNICs, telephone numbers, designations, free-text remarks,
  invoice references, credentials, internal paths, or sensitive row-level outputs?
- Are logs, exceptions, fixtures, screenshots, and report figures safe?
- Are external inputs validated and output strings escaped?
- Do ignore rules still cover local secrets, raw data, processed data, and artifacts?
- Could an aggregate view disclose an individual through a small group?

## Architecture and regressions

- Does domain or feature logic leak into scripts, notebooks, or the web adapter?
- Is a public schema, artifact, configuration, or command contract changed?
- Are migrations/version bumps and backward compatibility addressed?
- Is the new dependency necessary, maintained, and recorded?
- Could the change alter an existing report result or promoted artifact?
- Is the implementation smaller and clearer than a new abstraction would be?

## Tests and reproducibility

- Does every changed invariant have a focused test or strong verification evidence?
- Are edge cases for dates, missingness, duplicates, allocation, reversals, and high costs
  covered where relevant?
- Do fixtures avoid production PII and clearly mark synthetic rows?
- Are source version, splits, seed, parameters, and package versions reproducible?
- Were the smallest relevant checks run, followed by broader contract checks when needed?
- Are failures accurately separated into regressions and pre-existing limitations?

## Application and report

- Is this visibly decision support rather than an automatic authorization?
- Are PKR units, prediction horizon, cutoff, artifact version, limitations, and uncertainty
  clear?
- Does the UI handle missing coverage and incompatible artifacts safely?
- Can every report table and figure be traced to an experiment output?
- Are citations present for external facts and methods, without overstating causality?

## Review outcome

A review should record:

- Findings ordered by severity with file/line references.
- Open questions and unverified assumptions.
- Commands/checks run and their results.
- Residual risks or test gaps.
- Approval only when blocking correctness, leakage, and privacy issues are resolved.
