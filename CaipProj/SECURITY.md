# Security Policy

## Scope and supported state

This is a pre-release academic proof of concept. No deployed version or security support
window exists yet. The policy covers repository content, source data, derived datasets,
model artifacts, reports, and the future web application.

## Reporting a vulnerability or data exposure

Report suspected vulnerabilities, leaked credentials, exposed personal data, or unsafe model
outputs privately to the repository/project maintainer. Do not include sensitive details in a
public issue, pull request, screenshot, chat, or email thread with unintended recipients.

The repository does not yet identify a public security contact. Add an approved private
contact before deployment or external collaboration.

## Data classification

- **Restricted:** raw WAPDA occupancy, ledger, asset, invoice, complaint, work-order, and
  free-text records; credentials; direct identifiers; linkable row-level exports.
- **Internal:** de-identified property-level tables, mappings, experiment artifacts, detailed
  predictions, and reconciliation reports.
- **Shareable after review:** aggregate metrics, sufficiently grouped charts, public methods,
  and the final CAIP report after privacy and authorization review.

The presence of a file in this workspace is not permission to redistribute it.

## Required controls

- Keep raw and processed row-level data out of version control.
- Restrict Cursor access to raw sources through `.cursorignore` and reduce binary/generated
  indexing through `.cursorindexingignore`.
- Store secrets in ignored local environment files or an approved secret manager.
- Use anonymized property identifiers and tokenized contractor/invoice references.
- Tokenize public source-native property keys before analytical export; retain only a stable
  opaque token, row locator, and row hash. RHFS native property identifiers and AHS
  `CONTROL` values must not appear in analytical releases.
- Remove resident name, CNIC, telephone, salary, family details, designation, and
  unredacted personal remarks from analytical and application surfaces.
- Process WAPDA-derived material lawfully; retain only as long as necessary; limit internal
  access by role; keep critical infrastructure within national borders; redact PII and
  system blueprints before any material leaves the secure network.
- Preserve access-controlled lineage so authorized reviewers can audit a derived value
  without publishing the source.
- Review downloads, logs, cache files, screenshots, error pages, and experiment trackers for
  indirect disclosure.
- Use aggregate group-size rules before presenting breakdowns.

## Source and model integrity

- Hash immutable inputs and record the expected source version.
- Refuse raw-artifact checksum drift and processed-release overwrites; record hashes for every
  emitted table in the release manifest.
- Do not overwrite raw files or silently resolve conflicting records.
- Store target-policy, split, feature-schema, dependency, and model metadata with artifacts.
- Load only compatible reviewed model bundles in the application.
- Treat imported spreadsheets, serialized models, and external web content as untrusted.
- Do not deserialize arbitrary Python objects from untrusted sources.

## Network and deployment

Project-level Codex network access is disabled by default. External data downloads require
an explicit source, license/terms review, checksum or version record, and approval where
needed.

The official AHS artifacts and derived v0.2 release are `local-analysis-only` pending a
specific redistribution review. Public availability of an upstream file is not, by itself,
approval to publish this repository's row-level derivative.

Before deploying the POC:

- Add authentication and authorization if row-level or internal data is accessible.
- Enforce TLS, secure cookies, request-size limits, dependency scanning, and secret rotation.
- Disable debug mode and detailed exception pages.
- Validate all inputs and restrict file upload/download paths.
- Define retention, backup, deletion, incident response, and access-review procedures.
- Complete a privacy review and obtain the data owner's deployment approval.

## What not to do

- Do not publish raw files or real row-level fixtures.
- Do not paste personal records into agent prompts or external services.
- Do not present public-harmonized or test-synthetic labels as observed WAPDA operational
  outcomes.
- Do not invent maintenance histories without documented public-source (or later authorized
  WAPDA) lineage.
- Do not use the model as the sole basis for budget denial, employee evaluation, tenancy,
  procurement award, or emergency-maintenance refusal.
- Do not report vulnerabilities publicly before the maintainer has assessed disclosure risk.
