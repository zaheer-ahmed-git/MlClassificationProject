> **Submission PDF:** the formatted final report is
> `reports/submission/caip_final_report.pdf` (7 pages, with charts).
> Code annex: `reports/submission/caip_code_annex.zip`.
> Separate examiner source: `reports/submission/caip_final_source.py`.
> Email draft: `reports/submission/EMAIL_DRAFT.txt`.
>
> This markdown file remains a working draft. Prefer the PDF for the emailed submission.

# Leakage-Safe Maintenance-Cost Estimation for WAPDA Residential Properties

**CAIP Final Project Report Draft**  
**Group member(s):** Z. Ahmed  
**Submission date:** 24 August 2026  
**Programme:** Certified Artificial Intelligence Professional (CAIP), Batch 8

> Submission note: replace the bracketed title-page fields, apply the required institutional
> formatting, and export this source to PDF. References and appendices are intended to sit
> outside the 5–8 page main-text limit.

## Abstract

This project investigates a leakage-safe decision-support workflow for estimating the next
12 months of maintenance cost for WAPDA staff-colony houses and apartments. Because linked
WAPDA property, work-order, and cost records are not yet available, the completed experiment
uses the 2015–2023 American Housing Survey (AHS) as a separate public proxy. Its outcome,
`future_routine_cost_proxy_v1`, represents reported routine-maintenance expenditure at the
next biennial survey wave; it is neither an observed WAPDA cost nor an exact next-12-month
label. A frozen grouped-temporal split produced 86,125 adjacent-wave transitions from 36,623
linked housing units with no unit overlap across training, validation, and test partitions.
All preprocessing and the high-cost threshold were fitted on training rows only. Fixed
baselines, linear regression, random forest, and gradient boosting were evaluated under a
predeclared selection policy using validation mean absolute error, a primary held-out test,
and a required pre-2023 sensitivity test. The type-median baseline achieved validation,
primary-test, and sensitivity-test MAE values of 827.95, 962.81, and 824.82 USD. Although
some fitted regressors slightly improved primary-test MAE, the gains did not satisfy the
frozen promotion criteria. The final reporting outcome therefore retains `type_median` as
the primary cost estimator and `prior_cost` as the interpretable high-cost reference; no
fitted model is promoted.

**Keywords:** maintenance-cost estimation, temporal validation, leakage prevention,
decision support, model governance, American Housing Survey

## 1. Introduction

### 1.1 Background and problem

Maintenance planning for a residential estate requires more than a historical expenditure
summary. Managers need a defensible estimate of future cost at the level at which work is
planned: one property observed at a historical cutoff, followed by a defined forecast
window. The approved WAPDA use case is therefore to estimate eligible direct maintenance
plus an approved allocation of shared-building maintenance during the following 12 months,
in nominal PKR. Routine, corrective, and emergency building work belongs in that target;
major renovation, reconstruction, personal appliances, land values, revenue, closing
entries, and unrelated asset classes do not.

The current WASC residential framing scope reconciles to 101 units across categories A–F.
However, the available WASC ledger does not provide verified property-to-work-order-to-cost
linkage or evidence of complete coverage. It supports descriptive account-level analysis,
not defensible property-level supervised learning. In particular, an absent ledger charge
cannot silently become a zero target: zero is valid only when complete operational coverage
shows that no eligible maintenance occurred.

The project consequently separates the operational objective from the experiment used to
study methods. The AHS experiment is a local-analysis-only public proxy. It tests whether a
reproducible, leakage-safe comparison and governance process can be built while preserving
the distinction between proxy evidence and future WAPDA validation.

### 1.2 Objectives and scope

The completed AHS phase had five objectives:

1. construct a reproducible longitudinal proxy view with explicit lineage;
2. prevent unit and temporal leakage in splitting and preprocessing;
3. compare simple baselines with fixed linear and tree-based regressors;
4. evaluate both cost error and a training-defined high-cost decision signal; and
5. freeze an interpretable reporting outcome without promoting a fitted model whose gains
   were not stable enough.

The work demonstrates two CAIP capability areas: machine-learning experimentation and
responsible AI/data governance. A web proof of concept, RHFS experiments, and validation on
real WAPDA operational data are outside this completed AHS evaluation. They remain separate
future tracks and do not reopen training or model selection.

## 2. Methodology

### 2.1 Study design and proxy semantics

The analytical unit is an AHS housing unit at source wave *t*, linked to the same unit at
the next available biennial wave *t+2*. The target `future_routine_cost_proxy_v1` is derived
from the next-wave AHS routine-maintenance response. Thus a 2019 feature row is paired with
the linked unit's 2021 response. The corpus covers national public-use files for 2015, 2017,
2019, 2021, and 2023.

This design is useful for temporal experimentation but differs materially from the intended
WAPDA target. The response is U.S.-based, self-reported, routine-maintenance expenditure
over the AHS reference period. It is not an observed work-order total, is not denominated in
PKR, and is not an exact next-12-month outcome. Results therefore support method selection
and risk analysis only; they do not establish WAPDA predictive validity.

The final harmonized release contains 36,623 distinct linked units and 86,125 eligible
adjacent-wave pairs. It preserves source-wave and label-wave lineage, target origin, linkage
status, and a marker for the 2023 questionnaire response-cap change. There are 11,648
reported zero responses. These are legitimate AHS responses under the source rules, not
evidence about missing WAPDA activity.

### 2.2 Frozen grouped-temporal split

The split `ahs-grouped-temporal-v1` was declared before model fitting. Units, rather than
individual rows, form the groups, so one linked housing unit cannot occur in multiple
partitions. Allocation is temporal:

| Partition | Linked units | Rows | Analytical role |
|---|---:|---:|---|
| Training | 10,103 | 13,871 | Fit preprocessing, thresholds, and models |
| Validation | 7,067 | 15,400 | Primary selection objective: MAE |
| Primary test | 19,453 | 56,854 | Final held-out assessment |
| **Total** | **36,623** | **86,125** | |

The split audit confirmed zero linked-unit overlap. The primary test includes labels from
2023, when the AHS maintenance-response cap increased from USD 10,000 to USD 100,000.
Accordingly, a second frozen test slice excludes 2023 labels. This pre-2023 sensitivity
test is required for interpretation and guards against treating a questionnaire change as
ordinary model drift.

### 2.3 Leakage-safe preprocessing

The preprocessor `ahs-training-fold-v1` fits every learned transformation on the training
partition only. It performs numeric coercion, missingness-indicator creation, median
imputation for feature values, categorical vocabulary fitting with unknown-category
handling, one-hot encoding, and feature-order freezing. The target is never imputed or
clipped. Unexpected non-finite values fail the contract instead of being silently repaired.

This process yields 205 model columns. The high-cost classification threshold is the 80th
percentile of training targets only: USD 1,428. Validation and test labels have no influence
on that threshold. The same threshold is used to report high-cost precision, recall, and F1.
This is a proxy decision signal, not a WAPDA budget rule.

### 2.4 Systems compared

The fixed experiment `ahs-baselines-models-v1` compares three simple references and three
fitted regressors:

- `training_median`: one constant equal to the training-target median;
- `type_median`: the training-target median within the available housing-type group, with a
  global training median fallback;
- `prior_cost`: the source-wave routine-maintenance value used as the next-wave prediction;
- linear regression with a fixed preprocessing and estimator configuration;
- random forest regression with fixed hyperparameters and random seed; and
- gradient boosting regression with fixed hyperparameters and random seed.

No hyperparameter search, post-test retraining, or iterative leaderboard selection was
authorized. Baselines and fitted models were scored on exactly the same frozen partitions.

### 2.5 Evaluation and selection policy

Mean absolute error (MAE) on validation is the primary objective because it expresses the
typical absolute dollar error and is less dominated by a small number of extreme responses
than root mean squared error (RMSE). RMSE remains a tail-sensitive diagnostic. An
error-band rate reports the share of predictions within `max(USD 500, 25% of actual cost)`.
High-cost precision, recall, and F1 are secondary operational diagnostics.

The frozen `ahs-selection-policy-v1` requires more than the smallest test-set number. A
fitted model must show adequate, stable improvement over appropriate baselines without
creating unacceptable sensitivity to the 2023 response-cap change. If those conditions are
not met, the policy permits a baseline-only reporting outcome and prohibits promotion.

### 2.6 Reproducible workflow

```text
Official AHS public-use files
            |
            v
validate sources -> harmonize adjacent waves -> audit release
            |
            v
assign grouped-temporal split -> audit zero unit overlap
            |
            v
fit preprocessing on training rows -> audit frozen feature contract
            |
            v
train fixed comparison once -> validation + two held-out test views
            |
            v
diagnostic review -> apply frozen selection policy -> report without promotion
```

Raw source files remain immutable. Release, split, preprocessing, experiment, review, and
selection declarations are versioned separately, while generated row-level data and model
artifacts remain ignored and local.

## 3. Implementation and Results

### 3.1 Implementation

The implementation is an installable Python package under `src/caip_maintenance/`, with
thin command-line entry points and declarative TOML contracts under `configs/`. Data
ingestion, validation, feature generation, modeling, evaluation, and future application
adapters remain separate. This prevents presentation code from redefining target or feature
logic.

Contract tests cover source registration, raw validation, harmonization, split integrity,
training-only preprocessing, deterministic experiment behavior, and review/selection
artifacts. The completed fixed experiment passed its repository audit. These checks establish
software and data-contract consistency for the local AHS run; they are not evidence of
performance on protected or future WAPDA data.

### 3.2 Final fixed metrics

| System | Validation MAE | Primary-test MAE | Pre-2023 sensitivity MAE | Primary-test high-cost F1 |
|---|---:|---:|---:|---:|
| Training median | 832.16 | 965.85 | 828.69 | — |
| **Type median** | **827.95** | **962.81** | **824.82** | — |
| **Prior cost** | 952.44 | 1,058.25 | 936.53 | **0.410** |
| Linear regression | 849.50 | 950.91 | 833.34 | 0.384 |
| Random forest | 850.27 | 956.54 | 837.78 | 0.397 |
| Gradient boosting | 843.34 | **949.15** | 829.68 | 0.356 |

All monetary errors in this table are nominal U.S. dollars under the AHS proxy. The table
does not translate them into PKR or WAPDA budget impact.

### 3.3 Interpretation of cost estimates

`type_median` produced the lowest validation MAE at USD 827.95. Gradient boosting produced
the lowest primary-test MAE at USD 949.15, a USD 13.66 improvement over `type_median`, or
about 1.4%. Linear regression also slightly beat the baseline on the primary test. These
small test differences did not reverse the policy outcome because selection was anchored to
the validation objective and required stable evidence across the sensitivity view.

The pre-2023 MAE values are materially lower for every system than the corresponding
primary-test values. That consistent gap supports the diagnostic concern that the 2023
instrument change altered the observable target range. It does not establish that any one
model generalized better to the changed regime. Promoting gradient boosting solely because
it achieved the lowest primary-test MAE would therefore use held-out evidence as a new
selection loop and overstate a small, regime-sensitive gain.

### 3.4 High-cost signal

Among systems with a defined continuous score for thresholding, `prior_cost` achieved the
highest primary-test high-cost F1 at 0.410. Random forest, linear regression, and gradient
boosting followed at 0.397, 0.384, and 0.356. The persistence baseline is easy to explain:
units reporting higher source-wave routine cost are flagged as higher-risk references for
the next wave. Its cost MAE is worse than the other systems, so it is not the primary cost
estimator. It is retained only as the high-cost triage reference.

### 3.5 Final authorized outcome

Applying `ahs-selection-policy-v1` gives a baseline-only outcome:

- report `type_median` as the primary cost estimator;
- report `prior_cost` as the high-cost reference;
- do not promote linear regression, random forest, or gradient boosting;
- do not bind a future web proof of concept to a purported winning fitted model; and
- do not reopen training, tuning, or evaluation without a new authorization.

This outcome is not a failure to select a model. It is the intended behavior of a governance
policy when fitted complexity has not demonstrated sufficiently stable practical value.

## 4. Discussion

### 4.1 Main findings

The experiment shows that simple, transparent references are difficult to beat reliably on
this proxy. Housing-type medians capture enough structure to lead the predeclared validation
objective, while fitted models offer only small and inconsistent MAE improvements across
the held-out views. Prior cost carries a useful persistence signal for high-cost triage but
is not competitive as the main point estimator.

The more important project result is methodological. Grouped-temporal splitting prevents
the same housing unit from appearing on both sides of evaluation. Training-only preprocessing
prevents validation and test distributions from influencing encoders, medians, thresholds,
or feature order. A frozen policy then prevents a favorable test metric from becoming an
informal second validation set. Together, these controls make the conclusion auditable.

### 4.2 Practical relevance to WAPDA

The workflow supplies a template for a future WAPDA experiment: define one property at one
cutoff, establish complete label coverage, preserve source lineage, split histories by time
and property, learn all transformations on training data, compare against transparent
baselines, and apply a decision rule written before final testing. The current numerical
results must not be transferred directly. AHS dollars, survey responses, building types,
maintenance definitions, and biennial timing differ from WAPDA operational records and the
approved 12-month PKR target.

For actual deployment, WAPDA would need an anonymized property register, dated eligible
work orders, verified direct cost, approved shared-building allocations, and explicit
coverage periods. Only then could a zero cost be distinguished from missing activity and a
property-level model be validated.

### 4.3 Limitations and challenges

The main limitation is domain mismatch. The AHS target is self-reported U.S. routine
maintenance rather than WAPDA's broader eligible direct and allocated maintenance. Its
two-year wave spacing does not exactly match the desired 12-month forecast horizon. Survey
nonresponse and the 2023 response-cap change also affect the observed distribution.

The experiment does not estimate causal effects, optimize maintenance interventions, or
prove operational savings. High-cost F1 depends on a proxy threshold fitted from AHS
training labels, and baseline systems without a compatible continuous triage score do not
have comparable F1 entries. Finally, no application or promoted artifact exists, so user
experience, latency, monitoring, and deployment security have not been evaluated.

### 4.4 Remaining work

No AHS retraining, hyperparameter search, additional final validation, or fitted-model
promotion remains in this phase. The immediate remaining tasks are report formatting and
submission packaging. RHFS baselines may be performed only as a separately authorized,
unmerged experiment. A later web proof of concept should demonstrate workflow and
explanation behavior without claiming a winning fitted model. Real WAPDA validation remains
blocked until suitable operational records exist.

## 5. Conclusion

The completed AHS experiment provides a reproducible and leakage-safe assessment of simple
and fitted maintenance-cost estimators on a public longitudinal proxy. Its final authorized
evaluation comprises validation MAE, a primary held-out test, and a required pre-2023
sensitivity test. Under the frozen selection policy, fitted regressors did not demonstrate
enough stable benefit to justify promotion. The project therefore reports `type_median` as
the primary cost estimator and `prior_cost` as the high-cost reference.

This deliberately modest conclusion is appropriate for the evidence. It preserves a clear
boundary between a completed public-proxy experiment and a future WAPDA system. The next
phase is documentation and submission—not more AHS modeling—while operational validation
awaits property-linked, coverage-complete WAPDA data.

## References

[1] U.S. Census Bureau and U.S. Department of Housing and Urban Development, “American
Housing Survey: 2023 Data,” 2023. [Online]. Available:
https://www.census.gov/programs-surveys/ahs/data/2023.html. [Accessed: Aug. 16, 2026].

[2] U.S. Census Bureau, “American Housing Survey Codebooks.” [Online]. Available:
https://www.census.gov/programs-surveys/ahs/tech-documentation/codebooks.html. [Accessed:
Aug. 16, 2026].

[3] U.S. Census Bureau, *Sample Case History File 2015 to 2023*. [Online]. Available:
https://www2.census.gov/programs-surveys/ahs/documentation/Sample%20Case%20History%20File%202015%20to%202023.pdf.
[Accessed: Aug. 16, 2026].

[4] U.S. Census Bureau, *2023 AHS Historical Changes*, 2023. [Online]. Available:
https://www2.census.gov/programs-surveys/ahs/2023/2023%20AHS%20Historical%20Changes.pdf.
[Accessed: Aug. 16, 2026].

[5] L. Breiman, “Random forests,” *Machine Learning*, vol. 45, no. 1, pp. 5–32, 2001,
doi: 10.1023/A:1010933404324.

[6] J. H. Friedman, “Greedy function approximation: A gradient boosting machine,” *The
Annals of Statistics*, vol. 29, no. 5, pp. 1189–1232, 2001, doi:
10.1214/aos/1013203451.

[7] F. Pedregosa *et al.*, “Scikit-learn: Machine learning in Python,” *Journal of Machine
Learning Research*, vol. 12, pp. 2825–2830, 2011.

## Appendix A. Reproducibility and submission notes

The canonical local sequence is source validation, harmonization, release audit, grouped
split and audit, training-fold preprocessing and audit, one fixed experiment run, experiment
audit, diagnostic review, and frozen selection. Those steps are already complete; they are
not rerun for this report. Exact commands and artifact contracts are maintained in
`WORKFLOWS.md`, `TESTING.md`, and `Documentation/AHSBaselineModelExperiment.md`.

The final submission package should include the formatted PDF and the Python source tree as
the separate code annex required by the course brief. Generated row-level data, raw source
files, credentials, and trained artifacts must not be attached.
