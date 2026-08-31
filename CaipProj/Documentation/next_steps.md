# What I recommend doing next

I would **not immediately try another target transformation**.

You now have enough evidence that the main weakness is not simply "the data needs to be normalized."

Your next priority should be:

**feature quality → feature engineering → controlled model tuning.**

That stays fully within your proposal, which explicitly says you will clean/standardize the data and compare Linear Regression, Random Forest and Gradient Boosting. 

## Step 1 — Audit the 205 features

You currently have **205 model features**. 

Before tuning models, determine whether all of them are actually useful.

Produce a feature audit containing:

```text
feature
source
numeric/categorical
missing %
unique values
variance/frequency
prediction-time availability
possible leakage?
domain interpretation
```

Pay particular attention to:

* very high missingness;
* near-constant variables;
* redundant one-hot categories;
* strongly correlated numerical variables;
* survey identifiers/codes with no predictive meaning;
* variables that would not realistically exist in the eventual WAPDA system;
* temporal variables that might accidentally encode survey wave rather than property condition.

Don't blindly remove variables based only on correlation with the target. Use training data and domain reasoning.

---

# Step 2 — Create meaningful derived features

This is probably the highest-value modeling change available to you without leaving the proposal.

The models currently receive raw survey variables. Try deriving variables that better represent maintenance behavior.

For example, wherever the AHS fields permit:

### Property age

```python
property_age = label_year - construction_year
```

Much easier for a model to use than raw construction year.

### Prior-maintenance intensity

If area is available:

```python
prior_maintenance_per_sqft = prior_cost / floor_area
```

Possibly protect against zero area:

```python
prior_maintenance_per_sqft = prior_cost / np.maximum(area, 1)
```

### Property-size features

Depending on available columns:

```text
rooms per unit area
bathrooms per unit area
persons per room
occupancy density
```

### Condition burden

If there are multiple legitimate condition indicators, derive counts such as:

```text
number_of_reported_defects
number_of_system_problems
```

rather than relying only on dozens of individual flags.

### Prior-cost transformations as *features*

This is different from transforming the target.

You can retain:

```text
prior_routine_maintenance_usd
```

and add:

```python
log_prior_cost = np.log1p(prior_cost)
```

This lets the model access both representations while keeping the **target in raw USD**.

That could be particularly useful because prior cost already carries meaningful high-cost information; your existing experiment found that `prior_cost` has high-cost F1 of **0.410**. 

---

# Step 3 — Keep model-specific preprocessing

You don't need another global scaling experiment if this is already handled correctly.

Use:

**Linear Regression**

```text
numeric:
median imputation
→ StandardScaler

categorical:
imputation
→ OneHotEncoder
```

**Random Forest / Gradient Boosting**

```text
numeric:
median imputation

categorical:
imputation
→ encoding
```

Scaling trees won't normally solve the issue you're seeing.

Your audit already confirms preprocessing is fitted on the training split only, which is exactly what you want. 

---

# Step 4 — Tune the existing models

This should probably become your next formal experiment.

For example:

**`ahs-baselines-models-tuned-v1`**

Keep:

* same dataset release;
* same split;
* same raw USD target;
* same evaluation policy;
* same baselines.

Only vary model hyperparameters.

For Random Forest, investigate a modest grid such as:

```python
n_estimators = [300, 600]
max_depth = [None, 10, 20]
min_samples_leaf = [1, 5, 10]
max_features = ["sqrt", 0.5, 1.0]
```

For Gradient Boosting:

```python
n_estimators = [100, 200, 400]
learning_rate = [0.03, 0.05, 0.1]
max_depth = [2, 3, 4]
min_samples_leaf = [5, 10, 20]
subsample = [0.7, 1.0]
```

Don't create a huge search space. You want a controlled academic experiment, not hundreds of opaque runs.

Most importantly:

> **Select hyperparameters using validation MAE only.**

The primary test must remain untouched during selection.

---

# Step 5 — Consider robust regression loss

This is the next experiment I would prioritize after ordinary tuning.

It remains Gradient Boosting, so you are **not introducing a new model family**.

Instead of changing `y`, change how errors are penalized.

For example, compare:

```text
Gradient Boosting + squared_error
Gradient Boosting + absolute_error
Gradient Boosting + huber
```

This is particularly relevant to your dataset because the target contains a small number of extreme observations up to **$99,998**. 

`Huber` is interesting because it attempts a compromise:

* retains sensitivity to ordinary residuals;
* reduces domination by extreme residuals;
* does not compress the entire target like `log1p`.

Conceptually:

```text
Raw squared loss
             Extreme observations can dominate

Log target
             Extreme observations become heavily compressed

Huber loss
             Middle ground
```

This makes it a much more logical next test after what you just learned from `log1p`.

---

# Step 6 — Investigate inflation adjustment, but not yet as the main experiment

I still think this is worth studying because the target is nominal USD and spans multiple waves.

However, there is a methodological complication.

Your 2023 problem is not necessarily just inflation. Your previous investigation found a **response-cap change from roughly $9,998 to $99,998**. 

CPI adjustment will not fix that structural measurement difference.

So do not assume:

> "2023 is worse because of inflation."

You would need to distinguish:

```text
general price inflation
        versus

survey response-cap / measurement change
        versus

actual maintenance-cost distribution change
```

Inflation normalization is therefore useful as a **sensitivity experiment**, but I'd put it after feature engineering/tuning.

---

# Step 7 — Do a feature-ablation experiment

This can become one of the strongest parts of your dissertation.

Instead of only comparing algorithms, ask:

> **Which groups of information actually contribute to maintenance forecasting?**

For example:

| Feature configuration          | Question                                           |
| ------------------------------ | -------------------------------------------------- |
| Structural only                | Can building characteristics predict cost?         |
| Structural + socioeconomic     | Does household context help?                       |
| Structural + prior maintenance | How important is historical maintenance?           |
| All available features         | Full model                                         |
| All except prior cost          | How dependent is the model on historical spending? |

This is especially important because `prior_routine_maintenance_usd` is likely a powerful variable.

If performance changes from, say:

```text
Without prior cost → MAE 1000
With prior cost    → MAE 850
```

that gives you an actionable conclusion:

> Historical property-level expenditure is a key requirement for a future WAPDA system.

That is far more useful to WAPDA than simply saying Gradient Boosting had a certain MAE.

The proposal specifically expects inputs such as previous repairs, work orders, labour/material expenses and actual expenditure. 

---

# Your experiment sequence should now be

I would structure it like this:

```text
Experiment 1 ✅
ahs-baselines-models-v1
Raw USD target
LR / RF / GB + baselines

             ↓

Experiment 2 ✅
ahs-baselines-models-log1p-v1
Target-transformation ablation
Conclusion: not selected

             ↓

Experiment 3 ← NEXT
ahs-feature-engineering-v1
Raw target
Improved/derived predictors
Same model families

             ↓

Experiment 4
ahs-model-tuning-v1
Validation-only hyperparameter tuning

             ↓

Experiment 5
ahs-robust-loss-v1
GB squared vs absolute vs Huber

             ↓

Experiment 6
Feature-group ablations

             ↓

Optional sensitivity
Inflation-adjusted target/features
```

I would actually put **feature engineering before extensive hyperparameter tuning**, because tuning a model on a weak representation of the underlying problem rarely produces as much improvement as giving it better information.

I would proceed like this:

Keep your current temporal splits unchanged.
Keep the target distribution naturally skewed.
Check missing values, duplicates, impossible values and data types.
Median-impute numeric features using training statistics only.
Impute categorical variables and one-hot encode using training categories only.
Standardize numerical features for Linear Regression.
Do not unnecessarily scale Random Forest/Gradient Boosting.
Reproduce your current baseline to verify the pipeline.
Investigate inflation-adjusted costs as another controlled experiment.
Perform feature engineering using information available before the prediction period.
Tune LR/RF/GB using validation only.
Freeze the best validation configuration.
Evaluate once on the test set.
Report MAE + MedAE + RMSE + non-zero MAE + subgroup/cost-bucket results.
