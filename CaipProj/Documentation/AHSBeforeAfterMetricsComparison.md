# AHS Before/After Next-Steps Metrics Comparison

Compares frozen baselines and fitted models on the same grouped temporal split,
using the documented evaluation views (`primary`, `pre_2023_cap_sensitivity`) and
splits (`validation`, `test`). Metrics: MAE USD, RMSE USD, high-cost precision,
recall, and F1 (training-fold top-20% threshold).

**Before:** preprocessor `ahs-training-fold-v1` (205 harmonized features).
**After:** feature engineering, validation-only tuning, and robust-loss experiments
on preprocessor `ahs-feature-engineering-v1` (215 features). Baselines are unchanged
by design (feature-independent).

## primary / validation

| Model | Metric | Before | After | Delta |
| --- | --- | ---: | ---: | ---: |
| training_median | mae_usd | 832.16 | 832.16 | 0.00 ↑ |
| training_median | rmse_usd | 1546.63 | 1546.63 | 0.00 ↑ |
| training_median | high_cost_precision | — | — | — |
| training_median | high_cost_recall | 0.0000 | 0.0000 | 0.00 ↑ |
| training_median | high_cost_f1 | — | — | — |
| type_median | mae_usd | 827.95 | 827.95 | 0.00 ↑ |
| type_median | rmse_usd | 1549.36 | 1549.36 | 0.00 ↑ |
| type_median | high_cost_precision | — | — | — |
| type_median | high_cost_recall | 0.0000 | 0.0000 | 0.00 ↑ |
| type_median | high_cost_f1 | — | — | — |
| prior_cost | mae_usd | 952.44 | 952.44 | 0.00 ↑ |
| prior_cost | rmse_usd | 1682.96 | 1682.96 | 0.00 ↑ |
| prior_cost | high_cost_precision | 0.4242 | 0.4242 | 0.00 ↑ |
| prior_cost | high_cost_recall | 0.3391 | 0.3391 | 0.00 ↑ |
| prior_cost | high_cost_f1 | 0.3769 | 0.3769 | 0.00 ↑ |
| linear_regression | mae_usd | 849.50 | 852.06 | +2.55 ↑ |
| linear_regression | rmse_usd | 1370.12 | 1368.12 | -2.00 ↓ |
| linear_regression | high_cost_precision | 0.4754 | 0.4739 | -0.00 ↑ |
| linear_regression | high_cost_recall | 0.2782 | 0.2936 | +0.02 ↓ |
| linear_regression | high_cost_f1 | 0.3510 | 0.3626 | +0.01 ↓ |
| random_forest | mae_usd | 850.27 | 841.23 | -9.03 ↓ |
| random_forest | rmse_usd | 1370.85 | 1364.40 | -6.45 ↓ |
| random_forest | high_cost_precision | 0.4441 | 0.4914 | +0.05 ↓ |
| random_forest | high_cost_recall | 0.3029 | 0.2759 | -0.03 ↑ |
| random_forest | high_cost_f1 | 0.3602 | 0.3534 | -0.01 ↑ |
| gradient_boosting (tuned HistGBR, squared loss) | mae_usd | 843.34 | 841.16 | -2.19 ↓ |
| gradient_boosting (tuned HistGBR, squared loss) | rmse_usd | 1369.70 | 1364.49 | -5.21 ↓ |
| gradient_boosting (tuned HistGBR, squared loss) | high_cost_precision | 0.4871 | 0.5008 | +0.01 ↓ |
| gradient_boosting (tuned HistGBR, squared loss) | high_cost_recall | 0.2473 | 0.2726 | +0.03 ↓ |
| gradient_boosting (tuned HistGBR, squared loss) | high_cost_f1 | 0.3281 | 0.3531 | +0.03 ↓ |
| gradient_boosting (absolute loss) | mae_usd | 843.34 | 779.31 | -64.03 ↓ |
| gradient_boosting (absolute loss) | rmse_usd | 1369.70 | 1456.62 | +86.92 ↑ |
| gradient_boosting (absolute loss) | high_cost_precision | 0.4871 | 0.6173 | +0.13 ↓ |
| gradient_boosting (absolute loss) | high_cost_recall | 0.2473 | 0.0291 | -0.22 ↑ |
| gradient_boosting (absolute loss) | high_cost_f1 | 0.3281 | 0.0556 | -0.27 ↑ |
| xgboost (default hyperparameters) | mae_usd | 845.90 | 846.03 | +0.13 ↑ |
| xgboost (default hyperparameters) | rmse_usd | 1375.55 | 1373.85 | -1.69 ↓ |
| xgboost (default hyperparameters) | high_cost_precision | 0.4471 | 0.4509 | +0.00 ↓ |
| xgboost (default hyperparameters) | high_cost_recall | 0.2965 | 0.2968 | +0.00 ↓ |
| xgboost (default hyperparameters) | high_cost_f1 | 0.3566 | 0.3580 | +0.00 ↓ |
| xgboost (validation-tuned) | mae_usd | 845.90 | 838.83 | -7.07 ↓ |
| xgboost (validation-tuned) | rmse_usd | 1375.55 | 1361.85 | -13.70 ↓ |
| xgboost (validation-tuned) | high_cost_precision | 0.4471 | 0.4811 | +0.03 ↓ |
| xgboost (validation-tuned) | high_cost_recall | 0.2965 | 0.2933 | -0.00 ↑ |
| xgboost (validation-tuned) | high_cost_f1 | 0.3566 | 0.3645 | +0.01 ↓ |
| xgboost (absolute objective) | mae_usd | 845.90 | 778.41 | -67.49 ↓ |
| xgboost (absolute objective) | rmse_usd | 1375.55 | 1448.78 | +73.24 ↑ |
| xgboost (absolute objective) | high_cost_precision | 0.4471 | 0.6111 | +0.16 ↓ |
| xgboost (absolute objective) | high_cost_recall | 0.2965 | 0.0545 | -0.24 ↑ |
| xgboost (absolute objective) | high_cost_f1 | 0.3566 | 0.1000 | -0.26 ↑ |

## primary / test

| Model | Metric | Before | After | Delta |
| --- | --- | ---: | ---: | ---: |
| training_median | mae_usd | 965.85 | 965.85 | 0.00 ↑ |
| training_median | rmse_usd | 2360.09 | 2360.09 | 0.00 ↑ |
| training_median | high_cost_precision | — | — | — |
| training_median | high_cost_recall | 0.0000 | 0.0000 | 0.00 ↑ |
| training_median | high_cost_f1 | — | — | — |
| type_median | mae_usd | 962.81 | 962.81 | 0.00 ↑ |
| type_median | rmse_usd | 2361.65 | 2361.65 | 0.00 ↑ |
| type_median | high_cost_precision | — | — | — |
| type_median | high_cost_recall | 0.0000 | 0.0000 | 0.00 ↑ |
| type_median | high_cost_f1 | — | — | — |
| prior_cost | mae_usd | 1058.25 | 1058.25 | 0.00 ↑ |
| prior_cost | rmse_usd | 2358.81 | 2358.81 | 0.00 ↑ |
| prior_cost | high_cost_precision | 0.4561 | 0.4561 | 0.00 ↑ |
| prior_cost | high_cost_recall | 0.3726 | 0.3726 | 0.00 ↑ |
| prior_cost | high_cost_f1 | 0.4102 | 0.4102 | 0.00 ↑ |
| linear_regression | mae_usd | 950.91 | 954.55 | +3.64 ↑ |
| linear_regression | rmse_usd | 2182.90 | 2179.87 | -3.03 ↓ |
| linear_regression | high_cost_precision | 0.5081 | 0.5028 | -0.01 ↑ |
| linear_regression | high_cost_recall | 0.3086 | 0.3244 | +0.02 ↓ |
| linear_regression | high_cost_f1 | 0.3840 | 0.3944 | +0.01 ↓ |
| random_forest | mae_usd | 956.54 | 946.57 | -9.97 ↓ |
| random_forest | rmse_usd | 2188.13 | 2186.38 | -1.74 ↓ |
| random_forest | high_cost_precision | 0.4763 | 0.5126 | +0.04 ↓ |
| random_forest | high_cost_recall | 0.3403 | 0.3084 | -0.03 ↑ |
| random_forest | high_cost_f1 | 0.3970 | 0.3851 | -0.01 ↑ |
| gradient_boosting (tuned HistGBR, squared loss) | mae_usd | 949.15 | 945.27 | -3.88 ↓ |
| gradient_boosting (tuned HistGBR, squared loss) | rmse_usd | 2188.68 | 2183.34 | -5.34 ↓ |
| gradient_boosting (tuned HistGBR, squared loss) | high_cost_precision | 0.5014 | 0.5153 | +0.01 ↓ |
| gradient_boosting (tuned HistGBR, squared loss) | high_cost_recall | 0.2763 | 0.2925 | +0.02 ↓ |
| gradient_boosting (tuned HistGBR, squared loss) | high_cost_f1 | 0.3563 | 0.3732 | +0.02 ↓ |
| gradient_boosting (absolute loss) | mae_usd | 949.15 | 899.84 | -49.30 ↓ |
| gradient_boosting (absolute loss) | rmse_usd | 2188.68 | 2274.14 | +85.46 ↑ |
| gradient_boosting (absolute loss) | high_cost_precision | 0.5014 | 0.6904 | +0.19 ↓ |
| gradient_boosting (absolute loss) | high_cost_recall | 0.2763 | 0.0339 | -0.24 ↑ |
| gradient_boosting (absolute loss) | high_cost_f1 | 0.3563 | 0.0647 | -0.29 ↑ |
| xgboost (default hyperparameters) | mae_usd | 949.38 | 952.18 | +2.80 ↑ |
| xgboost (default hyperparameters) | rmse_usd | 2189.87 | 2190.75 | +0.89 ↑ |
| xgboost (default hyperparameters) | high_cost_precision | 0.4768 | 0.4733 | -0.00 ↑ |
| xgboost (default hyperparameters) | high_cost_recall | 0.3246 | 0.3279 | +0.00 ↓ |
| xgboost (default hyperparameters) | high_cost_f1 | 0.3863 | 0.3874 | +0.00 ↓ |
| xgboost (validation-tuned) | mae_usd | 949.38 | 944.34 | -5.03 ↓ |
| xgboost (validation-tuned) | rmse_usd | 2189.87 | 2182.07 | -7.79 ↓ |
| xgboost (validation-tuned) | high_cost_precision | 0.4768 | 0.5018 | +0.03 ↓ |
| xgboost (validation-tuned) | high_cost_recall | 0.3246 | 0.3197 | -0.00 ↑ |
| xgboost (validation-tuned) | high_cost_f1 | 0.3863 | 0.3906 | +0.00 ↓ |
| xgboost (absolute objective) | mae_usd | 949.38 | 899.07 | -50.30 ↓ |
| xgboost (absolute objective) | rmse_usd | 2189.87 | 2268.28 | +78.42 ↑ |
| xgboost (absolute objective) | high_cost_precision | 0.4768 | 0.6342 | +0.16 ↓ |
| xgboost (absolute objective) | high_cost_recall | 0.3246 | 0.0623 | -0.26 ↑ |
| xgboost (absolute objective) | high_cost_f1 | 0.3863 | 0.1134 | -0.27 ↑ |

## pre_2023_cap_sensitivity / validation

| Model | Metric | Before | After | Delta |
| --- | --- | ---: | ---: | ---: |
| training_median | mae_usd | 832.16 | 832.16 | 0.00 ↑ |
| training_median | rmse_usd | 1546.63 | 1546.63 | 0.00 ↑ |
| training_median | high_cost_precision | — | — | — |
| training_median | high_cost_recall | 0.0000 | 0.0000 | 0.00 ↑ |
| training_median | high_cost_f1 | — | — | — |
| type_median | mae_usd | 827.95 | 827.95 | 0.00 ↑ |
| type_median | rmse_usd | 1549.36 | 1549.36 | 0.00 ↑ |
| type_median | high_cost_precision | — | — | — |
| type_median | high_cost_recall | 0.0000 | 0.0000 | 0.00 ↑ |
| type_median | high_cost_f1 | — | — | — |
| prior_cost | mae_usd | 952.44 | 952.44 | 0.00 ↑ |
| prior_cost | rmse_usd | 1682.96 | 1682.96 | 0.00 ↑ |
| prior_cost | high_cost_precision | 0.4242 | 0.4242 | 0.00 ↑ |
| prior_cost | high_cost_recall | 0.3391 | 0.3391 | 0.00 ↑ |
| prior_cost | high_cost_f1 | 0.3769 | 0.3769 | 0.00 ↑ |
| linear_regression | mae_usd | 849.50 | 852.06 | +2.55 ↑ |
| linear_regression | rmse_usd | 1370.12 | 1368.12 | -2.00 ↓ |
| linear_regression | high_cost_precision | 0.4754 | 0.4739 | -0.00 ↑ |
| linear_regression | high_cost_recall | 0.2782 | 0.2936 | +0.02 ↓ |
| linear_regression | high_cost_f1 | 0.3510 | 0.3626 | +0.01 ↓ |
| random_forest | mae_usd | 850.27 | 841.23 | -9.03 ↓ |
| random_forest | rmse_usd | 1370.85 | 1364.40 | -6.45 ↓ |
| random_forest | high_cost_precision | 0.4441 | 0.4914 | +0.05 ↓ |
| random_forest | high_cost_recall | 0.3029 | 0.2759 | -0.03 ↑ |
| random_forest | high_cost_f1 | 0.3602 | 0.3534 | -0.01 ↑ |
| gradient_boosting (tuned HistGBR, squared loss) | mae_usd | 843.34 | 841.16 | -2.19 ↓ |
| gradient_boosting (tuned HistGBR, squared loss) | rmse_usd | 1369.70 | 1364.49 | -5.21 ↓ |
| gradient_boosting (tuned HistGBR, squared loss) | high_cost_precision | 0.4871 | 0.5008 | +0.01 ↓ |
| gradient_boosting (tuned HistGBR, squared loss) | high_cost_recall | 0.2473 | 0.2726 | +0.03 ↓ |
| gradient_boosting (tuned HistGBR, squared loss) | high_cost_f1 | 0.3281 | 0.3531 | +0.03 ↓ |
| gradient_boosting (absolute loss) | mae_usd | 843.34 | 779.31 | -64.03 ↓ |
| gradient_boosting (absolute loss) | rmse_usd | 1369.70 | 1456.62 | +86.92 ↑ |
| gradient_boosting (absolute loss) | high_cost_precision | 0.4871 | 0.6173 | +0.13 ↓ |
| gradient_boosting (absolute loss) | high_cost_recall | 0.2473 | 0.0291 | -0.22 ↑ |
| gradient_boosting (absolute loss) | high_cost_f1 | 0.3281 | 0.0556 | -0.27 ↑ |
| xgboost (default hyperparameters) | mae_usd | 845.90 | 846.03 | +0.13 ↑ |
| xgboost (default hyperparameters) | rmse_usd | 1375.55 | 1373.85 | -1.69 ↓ |
| xgboost (default hyperparameters) | high_cost_precision | 0.4471 | 0.4509 | +0.00 ↓ |
| xgboost (default hyperparameters) | high_cost_recall | 0.2965 | 0.2968 | +0.00 ↓ |
| xgboost (default hyperparameters) | high_cost_f1 | 0.3566 | 0.3580 | +0.00 ↓ |
| xgboost (validation-tuned) | mae_usd | 845.90 | 838.83 | -7.07 ↓ |
| xgboost (validation-tuned) | rmse_usd | 1375.55 | 1361.85 | -13.70 ↓ |
| xgboost (validation-tuned) | high_cost_precision | 0.4471 | 0.4811 | +0.03 ↓ |
| xgboost (validation-tuned) | high_cost_recall | 0.2965 | 0.2933 | -0.00 ↑ |
| xgboost (validation-tuned) | high_cost_f1 | 0.3566 | 0.3645 | +0.01 ↓ |
| xgboost (absolute objective) | mae_usd | 845.90 | 778.41 | -67.49 ↓ |
| xgboost (absolute objective) | rmse_usd | 1375.55 | 1448.78 | +73.24 ↑ |
| xgboost (absolute objective) | high_cost_precision | 0.4471 | 0.6111 | +0.16 ↓ |
| xgboost (absolute objective) | high_cost_recall | 0.2965 | 0.0545 | -0.24 ↑ |
| xgboost (absolute objective) | high_cost_f1 | 0.3566 | 0.1000 | -0.26 ↑ |

## pre_2023_cap_sensitivity / test

| Model | Metric | Before | After | Delta |
| --- | --- | ---: | ---: | ---: |
| training_median | mae_usd | 828.69 | 828.69 | 0.00 ↑ |
| training_median | rmse_usd | 1528.56 | 1528.56 | 0.00 ↑ |
| training_median | high_cost_precision | — | — | — |
| training_median | high_cost_recall | 0.0000 | 0.0000 | 0.00 ↑ |
| training_median | high_cost_f1 | — | — | — |
| type_median | mae_usd | 824.82 | 824.82 | 0.00 ↑ |
| type_median | rmse_usd | 1529.88 | 1529.88 | 0.00 ↑ |
| type_median | high_cost_precision | — | — | — |
| type_median | high_cost_recall | 0.0000 | 0.0000 | 0.00 ↑ |
| type_median | high_cost_f1 | — | — | — |
| prior_cost | mae_usd | 936.53 | 936.53 | 0.00 ↑ |
| prior_cost | rmse_usd | 1630.49 | 1630.49 | 0.00 ↑ |
| prior_cost | high_cost_precision | 0.4374 | 0.4374 | 0.00 ↑ |
| prior_cost | high_cost_recall | 0.3666 | 0.3666 | 0.00 ↑ |
| prior_cost | high_cost_f1 | 0.3989 | 0.3989 | 0.00 ↑ |
| linear_regression | mae_usd | 833.34 | 835.01 | +1.67 ↑ |
| linear_regression | rmse_usd | 1334.46 | 1332.70 | -1.76 ↓ |
| linear_regression | high_cost_precision | 0.4903 | 0.4888 | -0.00 ↑ |
| linear_regression | high_cost_recall | 0.3064 | 0.3187 | +0.01 ↓ |
| linear_regression | high_cost_f1 | 0.3771 | 0.3858 | +0.01 ↓ |
| random_forest | mae_usd | 837.78 | 828.18 | -9.60 ↓ |
| random_forest | rmse_usd | 1339.19 | 1332.38 | -6.80 ↓ |
| random_forest | high_cost_precision | 0.4582 | 0.4964 | +0.04 ↓ |
| random_forest | high_cost_recall | 0.3377 | 0.3097 | -0.03 ↑ |
| random_forest | high_cost_f1 | 0.3888 | 0.3814 | -0.01 ↑ |
| gradient_boosting (tuned HistGBR, squared loss) | mae_usd | 829.68 | 826.76 | -2.92 ↓ |
| gradient_boosting (tuned HistGBR, squared loss) | rmse_usd | 1336.06 | 1330.37 | -5.69 ↓ |
| gradient_boosting (tuned HistGBR, squared loss) | high_cost_precision | 0.4869 | 0.4971 | +0.01 ↓ |
| gradient_boosting (tuned HistGBR, squared loss) | high_cost_recall | 0.2756 | 0.2920 | +0.02 ↓ |
| gradient_boosting (tuned HistGBR, squared loss) | high_cost_f1 | 0.3520 | 0.3679 | +0.02 ↓ |
| gradient_boosting (absolute loss) | mae_usd | 829.68 | 768.47 | -61.21 ↓ |
| gradient_boosting (absolute loss) | rmse_usd | 1336.06 | 1423.74 | +87.68 ↑ |
| gradient_boosting (absolute loss) | high_cost_precision | 0.4869 | 0.6636 | +0.18 ↓ |
| gradient_boosting (absolute loss) | high_cost_recall | 0.2756 | 0.0339 | -0.24 ↑ |
| gradient_boosting (absolute loss) | high_cost_f1 | 0.3520 | 0.0644 | -0.29 ↑ |
| xgboost (default hyperparameters) | mae_usd | 830.26 | 833.04 | +2.78 ↑ |
| xgboost (default hyperparameters) | rmse_usd | 1339.89 | 1341.13 | +1.23 ↑ |
| xgboost (default hyperparameters) | high_cost_precision | 0.4599 | 0.4577 | -0.00 ↑ |
| xgboost (default hyperparameters) | high_cost_recall | 0.3263 | 0.3277 | +0.00 ↓ |
| xgboost (default hyperparameters) | high_cost_f1 | 0.3817 | 0.3820 | +0.00 ↓ |
| xgboost (validation-tuned) | mae_usd | 830.26 | 825.35 | -4.92 ↓ |
| xgboost (validation-tuned) | rmse_usd | 1339.89 | 1329.33 | -10.56 ↓ |
| xgboost (validation-tuned) | high_cost_precision | 0.4599 | 0.4815 | +0.02 ↓ |
| xgboost (validation-tuned) | high_cost_recall | 0.3263 | 0.3169 | -0.01 ↑ |
| xgboost (validation-tuned) | high_cost_f1 | 0.3817 | 0.3823 | +0.00 ↓ |
| xgboost (absolute objective) | mae_usd | 830.26 | 767.77 | -62.50 ↓ |
| xgboost (absolute objective) | rmse_usd | 1339.89 | 1417.07 | +77.18 ↑ |
| xgboost (absolute objective) | high_cost_precision | 0.4599 | 0.6207 | +0.16 ↓ |
| xgboost (absolute objective) | high_cost_recall | 0.3263 | 0.0646 | -0.26 ↑ |
| xgboost (absolute objective) | high_cost_f1 | 0.3817 | 0.1170 | -0.26 ↑ |

## Primary test summary (MAE / RMSE / F1)

| Model | Before MAE | After MAE | Before RMSE | After RMSE | Before F1 | After F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| training_median | 965.85 | 965.85 | 2360.09 | 2360.09 | — | — |
| type_median | 962.81 | 962.81 | 2361.65 | 2361.65 | — | — |
| prior_cost | 1058.25 | 1058.25 | 2358.81 | 2358.81 | 0.4102 | 0.4102 |
| linear_regression | 950.91 | 954.55 | 2182.90 | 2179.87 | 0.3840 | 0.3944 |
| random_forest | 956.54 | 946.57 | 2188.13 | 2186.38 | 0.3970 | 0.3851 |
| gradient_boosting (tuned HistGBR, squared loss) | 949.15 | 945.27 | 2188.68 | 2183.34 | 0.3563 | 0.3732 |
| gradient_boosting (absolute loss) | 949.15 | 899.84 | 2188.68 | 2274.14 | 0.3563 | 0.0647 |
| xgboost (default hyperparameters) | 949.38 | 952.18 | 2189.87 | 2190.75 | 0.3863 | 0.3874 |
| xgboost (validation-tuned) | 949.38 | 944.34 | 2189.87 | 2182.07 | 0.3863 | 0.3906 |
| xgboost (absolute objective) | 949.38 | 899.07 | 2189.87 | 2268.28 | 0.3863 | 0.1134 |
