**Recommendation: maintenance cost prediction for WAPDA staff colony housing.**  
It is the strongest fit for the current proposal: a clear applied problem, measurable metrics, two CAIP modules (ML + application/decision support), and direct relevance to public-sector budgeting. Proposal is due **28 Jul**; final submission **25 Aug**.

### What CAIP requires (from the brief)
Applied AI with a real dataset, at least **two modules**, measurable evaluation, and industry/governance relevance. Suggested topics include predictive maintenance and demand forecasting. Timeline is ~4 weeks after the proposal.

---

### Comparison of promising Pakistan domains

| Domain | Data sources | ML readiness | Real-world fit | CAIP risk |
|--------|----------------|--------------|----------------|-----------|
| **WAPDA housing maintenance cost** | WASC seed inventory/ledger (private); harmonized public housing/maintenance datasets for training; optional PBS/SBP prices, weather | Medium–high once public corpus is mapped to the project schema; WAPDA operational extracts blocked | Colony budgets, preventive repair prioritization, procurement planning | Best fit to proposal; training path revised under access limits |
| **Energy (load forecasting)** | NTDC hourly load (Kaggle, ~2015–2020); NEPRA IGCEP reports for context | High: years of hourly series; room for baselines + DL | Load shedding, day-ahead planning, DISCO/NTDC operations | Strong open-data alternative |
| **Environment / public health (AQI)** | Open-Meteo / Zenodo (Lahore, Karachi multi-year); Kaggle 10-city hourly; Pak-EPA / provincial EPA as stakeholders | High if you use multi-year city series; weak if only ~90 days | Smog, health advisories, city policy | Strong open-data option |
| **Agriculture (yield / drought)** | MNFSR Agricultural Statistics; PBS / Open Data Pakistan; Punjab CRS; FAOSTAT; PMD climate | Medium: often annual/district → few samples for DL | Food security, wheat/rice | Data merge + small *n* under tight deadline |
| **Finance (macro forecasting)** | SBP EasyData (~24k series: CPI, FX, M2, etc.); PBS prices | Medium: monthly series → thinner DL story | Inflation, policy rate, FX | Solid but less “system” demo |
| **Education / governance** | PIE / NODP EMIS; ASER | Medium: survey/cross-section; weaker sequential DL | Out-of-school, learning outcomes | Harder to show strong model results fast |

**Why WAPDA maintenance cost wins for this proposal:**  
1. Matches suggested CAIP themes of predictive maintenance and budget/demand-style forecasting.  
2. Property-level historical records (via a harmonized public corpus when WAPDA extracts are blocked) support a full pipeline: assess → clean → train → compare → pilot app.  
3. Two modules are natural: classical ML (regression / Random Forest / gradient boosting) **and** an AI-enabled decision-support application.  
4. Metrics are standard (MAE, RMSE) plus ranking of high-cost properties.  
5. Stakeholders are clear: WAPDA colony management, maintenance, and budgeting teams.

**Access update:** WAPDA property-linked work orders and costs are not currently obtainable under private-data rules. The approved path is a hybrid public multi-source training corpus framed on the WASC residential problem—not an arbitrary invented label set. See [DatasetPolicy.md](DatasetPolicy.md).

**Energy load forecasting** remains a fully open-data alternative only if the maintenance-domain public corpus cannot be constructed honestly.

---

### Recommended project framing

**Title:** *Machine Learning–Based Maintenance Cost Prediction for WAPDA Staff Colonies*

**Problem:** Estimate the **next-twelve-month maintenance cost** for a given WAPDA house or residential apartment, to improve budget planning and prioritize high-risk properties.

**Modules covered:** Machine Learning + AI-enabled system / decision support (optional: feature importance for transparent prioritization).

**Primary dataset:** Harmonized multi-source public residential/maintenance records mapped to the project schema (property attributes, repair/condition history, costs), with WASC seed files used only for framing and private descriptive evidence—not as unsupervised invented WAPDA labels.  
**Context sources:** Public inflation, construction material prices, labour rates, and weather data where relevant (e.g. SBP / PBS / Open-Meteo).

---

### High-level roadmap (proposal → final)

**1. Dataset selection**  
- Frame on WASC residential maintenance cost prediction (101-unit seed inventory).  
- Because WAPDA operational extracts are blocked, shortlist 5–10 public datasets and harmonize them into the project schema (>500 properties).  
- State problem, 12-month horizon, metrics, and modules (ML + application).  
- Document anonymization, lineage, and that public-harmonized labels are not observed WAPDA outcomes.

**2. Problem formulation**  
- Supervised regression at property level.  
- Target: total maintenance cost over the next 12 months (PKR).  
- Split by time and/or colony to avoid leakage.  
- Baselines: historical average cost per property / colony.

**3. Preprocessing**  
- Clean and standardize property IDs, dates, categories, and costs.  
- Build one row per house/apartment per historical 12-month period.  
- Features: age, size, type, occupancy, renovation history, complaints, prior spend; optional price/weather covariates.  
- Handle missing values and outliers; keep costs consistent (same inclusion rules for routine/emergency vs major renovation).

**4. Model development**  
- ML: historical baselines, linear regression, Random Forest, gradient boosting.  
- Compare under the same splits.  
- Optional: explanations / feature importance for high-cost flags.

**5. Evaluation**  
- MAE, RMSE; ability to flag high-maintenance-cost properties.  
- Breakdown by property type, age group, cost range, and colony where data allows.  
- Discuss limits: access constraints, uneven record quality, colony coverage, inflation drift.

**6. Deployment considerations (keep light but concrete)**  
- Web proof-of-concept: select/enter a property → estimated 12-month cost.  
- Optional: risk category, prediction range, top cost drivers, colony summaries.  
- Pilot on selected WAPDA staff colonies; compare predicted vs actual where available.  
- Frame as decision support for budgeting and prioritization, not a replacement for engineering judgment.

---

### Practical next step this week
Submit the **one-page proposal** on WAPDA maintenance cost prediction by **28 Jul 23:59** to `lab.tech@ncai.nust.edu.pk` (CC `rmeo@ncai.nust.edu.pk`), subject `CAIP Proposal Batch 8`.
