# CAIP Final Submission Package

Deadline: **25 August 2026, 23:59**

## Files to email

| File | Role |
|---|---|
| `caip_final_report.pdf` | 7-page CAIP exam report (text, charts, analysis) |
| `wapda_project_walkthrough.pdf` | 9-page plain-language project journey (for family/stakeholders) |
| `caip_code_annex.zip` | Complete Python package annex (no raw data, no artifacts) |
| `caip_final_source.py` | Separate Python source for testing/verification |

## Walkthrough document

`wapda_project_walkthrough.pdf` explains the full project in simple language: WASC data assessment, WAPDA data model, dataset preparation, Experiments 1--2, Phase~2 improvements, XGBoost, and what remains. It is **not** required for CAIP email submission unless you choose to attach it for context.

Rebuild:

```bash
cd reports/submission
pdflatex wapda_project_walkthrough.tex
pdflatex wapda_project_walkthrough.tex
```

## Email

- **To:** lab.tech@ncai.nust.edu.pk
- **CC:** rmeo@ncai.nust.edu.pk
- **Subject:** CAIP Final Project Batch 8

Use the body in `EMAIL_DRAFT.txt`. Confirm the author name on the PDF title page before sending (currently `Saeed Ahmad`).

## Report claim boundary

The report states that the **dataset is made on the WAPDA data model** (WASC residential schema: 101 units, A–F, 12-month eligible maintenance, top-20% high-cost rule). Training rows are **mapped AHS public-use records** filling that model because linked WAPDA work-order extracts were not released. The PDF does **not** claim those rows are observed WAPDA invoices.

## Rebuild the PDF

```bash
cd reports/submission
pdflatex caip_final_report.tex
pdflatex caip_final_report.tex
```

## Test the separate source file

```bash
python3 reports/submission/caip_final_source.py
```
