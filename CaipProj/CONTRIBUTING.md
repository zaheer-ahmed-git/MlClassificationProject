# Contributing

## Current phase

This repository is not yet initialized as a working software project: the visible `.git`
directory is empty, and there is no Python package or dependency manifest. Contributions
should preserve the distinction between confirmed evidence, proposed contracts, and future
implementation.

Read `AGENTS.md`, `README.md`, and the task-relevant references before making a change.

## Change types

### Documentation and governance

- Keep one canonical source for each fact and link to it instead of copying long sections.
- Mark future commands, modules, and results as planned until they exist.
- Update `CHANGELOG.md` for material changes to the target, architecture, security policy,
  data contract, or workflow.
- Verify relative links and cross-document terminology.

### Data sources and schema

- Do not edit files in `DatasetOfCAIP/` in place.
- Register each new source with a hash, coverage, PII classification, authority, and owner.
- Describe the expected grain, keys, controlled values, units, null semantics, and lineage.
- Quarantine source conflicts and request validation from an authorized data owner.
- Never commit raw or processed row-level data unless explicit approval, de-identification,
  and repository policy permit it.

### Code and models

- Scaffold the installable package and `pyproject.toml` before adding isolated scripts.
- Keep domain, ingestion, feature, model, evaluation, and UI responsibilities separate.
- Add tests with behavior changes and use deterministic seeds where supported.
- Do not add a model result without its data version, split definition, parameters, metrics,
  and reproducible command.
- Do not train the property-level model until the readiness gate in `README.md` passes or
  an explicitly narrower, defensible research question is approved.

## Branches, commits, and pull requests

When a real Git repository and remote exist:

- Create a short-lived branch for each coherent change.
- Use imperative commit messages that state the outcome, for example
  `Define cutoff-safe label contract`.
- Keep generated data, caches, credentials, local paths, and large model artifacts out of
  commits.
- In the pull request, state the goal, evidence, scope, risks, data/privacy effect, checks run,
  and documentation changed.
- Separate unrelated cleanup from functional or data-contract changes.

Do not claim a Git commit, branch, or CI result while the repository is not initialized.

## Required checks

Use `TESTING.md` to select the smallest relevant checks. A change is not ready for review
unless:

- Its factual and source assumptions are traceable.
- Target and leakage invariants still hold.
- Privacy and ignore rules still cover sensitive outputs.
- Relevant tests or structural checks pass.
- Failures and unverified assumptions are reported honestly.
- A reviewer can reproduce the result from documented inputs.

## Review expectations

Follow `CODE_REVIEW.md`. Target definition, cost eligibility, shared allocation, coverage,
PII handling, temporal splits, and reported results require particularly careful review.

`CODEOWNERS` is intentionally inactive until the repository's actual GitHub owner or team
is supplied. Do not insert a guessed account merely to activate automatic review.

## Pre-merge checklist

- Scope and definition of done are satisfied.
- Raw evidence is unchanged.
- No personal or secret values appear in the diff, logs, fixtures, or screenshots.
- Tests and checks are listed with results.
- Documentation and changelog changes are included where required.
- The changed-file set has been reviewed for correctness, leakage, security, and stale
  claims.
