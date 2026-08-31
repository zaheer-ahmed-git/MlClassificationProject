#!/usr/bin/env python3
"""Build before/after AHS experiment metric comparison tables."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts" / "experiments" / "public-corpus-v0.2.0-ahs" / "ahs-grouped-temporal-v1"

METRICS = (
    "mae_usd",
    "rmse_usd",
    "high_cost_precision",
    "high_cost_recall",
    "high_cost_f1",
)
VIEWS = ("primary", "pre_2023_cap_sensitivity")
SPLITS = ("validation", "test")

# Before: raw 205-feature preprocessor. After: engineered pipeline outputs.
MODEL_PAIRS: list[tuple[str, Path, Path]] = [
    (
        "training_median",
        ARTIFACTS / "ahs-training-fold-v1" / "ahs-baselines-models-v1",
        ARTIFACTS / "ahs-training-fold-v1" / "ahs-baselines-models-v1",
    ),
    (
        "type_median",
        ARTIFACTS / "ahs-training-fold-v1" / "ahs-baselines-models-v1",
        ARTIFACTS / "ahs-training-fold-v1" / "ahs-baselines-models-v1",
    ),
    (
        "prior_cost",
        ARTIFACTS / "ahs-training-fold-v1" / "ahs-baselines-models-v1",
        ARTIFACTS / "ahs-training-fold-v1" / "ahs-baselines-models-v1",
    ),
    (
        "linear_regression",
        ARTIFACTS / "ahs-training-fold-v1" / "ahs-baselines-models-v1",
        ARTIFACTS / "ahs-feature-engineering-v1" / "ahs-feature-engineering-v1",
    ),
    (
        "random_forest",
        ARTIFACTS / "ahs-training-fold-v1" / "ahs-baselines-models-v1",
        ARTIFACTS / "ahs-feature-engineering-v1" / "ahs-model-tuning-v1",
    ),
    (
        "gradient_boosting (tuned HistGBR, squared loss)",
        ARTIFACTS / "ahs-training-fold-v1" / "ahs-baselines-models-v1",
        ARTIFACTS / "ahs-feature-engineering-v1" / "ahs-model-tuning-v1",
    ),
    (
        "gradient_boosting (absolute loss)",
        ARTIFACTS / "ahs-training-fold-v1" / "ahs-baselines-models-v1",
        ARTIFACTS / "ahs-feature-engineering-v1" / "ahs-robust-loss-v1",
    ),
    (
        "xgboost (default hyperparameters)",
        ARTIFACTS / "ahs-training-fold-v1" / "ahs-xgboost-v1",
        ARTIFACTS / "ahs-feature-engineering-v1" / "ahs-xgboost-feature-engineering-v1",
    ),
    (
        "xgboost (validation-tuned)",
        ARTIFACTS / "ahs-training-fold-v1" / "ahs-xgboost-v1",
        ARTIFACTS / "ahs-feature-engineering-v1" / "ahs-xgboost-tuning-v1",
    ),
    (
        "xgboost (absolute objective)",
        ARTIFACTS / "ahs-training-fold-v1" / "ahs-xgboost-v1",
        ARTIFACTS / "ahs-feature-engineering-v1" / "ahs-xgboost-robust-loss-v1",
    ),
]

ROBUST_LOSS_MODEL_KEYS = {
    "gradient_boosting (absolute loss)": "gradient_boosting_absolute",
    "xgboost (absolute objective)": "xgboost_absolute",
}


def _load_metrics(path: Path) -> dict[str, Any]:
    metrics_path = path / "metrics.json"
    if not metrics_path.exists():
        raise FileNotFoundError(f"missing metrics: {metrics_path}")
    with metrics_path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _model_key(display_name: str, after: bool) -> str:
    if display_name in ROBUST_LOSS_MODEL_KEYS and after:
        return ROBUST_LOSS_MODEL_KEYS[display_name]
    mapping = {
        "training_median": "training_median",
        "type_median": "type_median",
        "prior_cost": "prior_cost",
        "linear_regression": "linear_regression",
        "random_forest": "random_forest",
        "gradient_boosting (tuned HistGBR, squared loss)": "gradient_boosting",
        "gradient_boosting (absolute loss)": "gradient_boosting",
        "xgboost (default hyperparameters)": "xgboost",
        "xgboost (validation-tuned)": "xgboost",
        "xgboost (absolute objective)": "xgboost",
    }
    return mapping[display_name]


def _metric_value(metrics: dict[str, Any], model_key: str, view: str, split: str, metric: str) -> float | None:
    block = metrics["results"][model_key][view][split].get(metric)
    return None if block is None else float(block)


def _fmt(value: float | None) -> str:
    if value is None:
        return "—"
    if abs(value) >= 100:
        return f"{value:.2f}"
    return f"{value:.4f}"


def _delta(before: float | None, after: float | None, lower_is_better: bool) -> str:
    if before is None or after is None:
        return "—"
    change = after - before
    improved = change < 0 if lower_is_better else change > 0
    sign = "+" if change > 0 else ""
    arrow = "↓" if improved else "↑"
    return f"{sign}{change:.2f} {arrow}"


def build_markdown(pairs: list[tuple[str, Path, Path]]) -> str:
    lines: list[str] = [
        "# AHS Before/After Next-Steps Metrics Comparison",
        "",
        "Compares frozen baselines and fitted models on the same grouped temporal split,",
        "using the documented evaluation views (`primary`, `pre_2023_cap_sensitivity`) and",
        "splits (`validation`, `test`). Metrics: MAE USD, RMSE USD, high-cost precision,",
        "recall, and F1 (training-fold top-20% threshold).",
        "",
        "**Before:** preprocessor `ahs-training-fold-v1` (205 harmonized features).",
        "**After:** feature engineering, validation-only tuning, and robust-loss experiments",
        "on preprocessor `ahs-feature-engineering-v1` (215 features). Baselines are unchanged",
        "by design (feature-independent).",
        "",
    ]

    for view in VIEWS:
        for split in SPLITS:
            lines.extend(
                [
                    f"## {view} / {split}",
                    "",
                    "| Model | Metric | Before | After | Delta |",
                    "| --- | --- | ---: | ---: | ---: |",
                ]
            )
            for display_name, before_dir, after_dir in pairs:
                before_metrics = _load_metrics(before_dir)
                after_metrics = _load_metrics(after_dir)
                before_key = _model_key(display_name, after=False)
                after_key = _model_key(display_name, after=True)
                for metric in METRICS:
                    before_val = _metric_value(before_metrics, before_key, view, split, metric)
                    after_val = _metric_value(after_metrics, after_key, view, split, metric)
                    lower_better = metric in {"mae_usd", "rmse_usd"}
                    lines.append(
                        f"| {display_name} | {metric} | {_fmt(before_val)} | {_fmt(after_val)} | "
                        f"{_delta(before_val, after_val, lower_better)} |"
                    )
            lines.append("")

    lines.extend(
        [
            "## Primary test summary (MAE / RMSE / F1)",
            "",
            "| Model | Before MAE | After MAE | Before RMSE | After RMSE | Before F1 | After F1 |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    view, split = "primary", "test"
    for display_name, before_dir, after_dir in pairs:
        before_metrics = _load_metrics(before_dir)
        after_metrics = _load_metrics(after_dir)
        before_key = _model_key(display_name, after=False)
        after_key = _model_key(display_name, after=True)
        row = [display_name]
        for metric in ("mae_usd", "rmse_usd", "high_cost_f1"):
            before_val = _metric_value(before_metrics, before_key, view, split, metric)
            after_val = _metric_value(after_metrics, after_key, view, split, metric)
            row.extend([_fmt(before_val), _fmt(after_val)])
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    available_pairs: list[tuple[str, Path, Path]] = []
    missing: list[str] = []
    for display_name, before_dir, after_dir in MODEL_PAIRS:
        try:
            _load_metrics(before_dir)
            _load_metrics(after_dir)
            available_pairs.append((display_name, before_dir, after_dir))
        except FileNotFoundError as exc:
            missing.append(f"{display_name}: {exc}")

    output_path = ROOT / "Documentation" / "AHSBeforeAfterMetricsComparison.md"
    output_path.write_text(build_markdown(available_pairs), encoding="utf-8")
    print(f"wrote {output_path} ({len(available_pairs)} model pairs)")
    if missing:
        print("skipped (missing artifacts):")
        for item in missing:
            print(f"  - {item}")


if __name__ == "__main__":
    main()
