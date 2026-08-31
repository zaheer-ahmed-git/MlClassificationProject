"""CAIP Final Project

This file is the entry point required by the CAIP brief.
It does not load raw WASC documents, AHS microdata, or trained model weights.

What it does:
  1. States the WAPDA residential data model constants used by the project.
  2. Implements the same unweighted MAE / RMSE / high-cost metrics used in
     the report

Run:
  python3 caip_final_source.py
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


# WAPDA residential data model 

WAPDA_DATA_MODEL = {
    "prediction_unit": "one residential property at one historical cutoff",
    "label": (
        "eligible direct building maintenance plus equal-per-occupied-unit "
        "shared-building allocation for the following 12 months"
    ),
    "in_scope_work": [
        "routine",
        "corrective",
        "emergency building maintenance",
    ],
    "out_of_scope": [
        "major renovation",
        "reconstruction",
        "personal appliances",
        "land values",
        "revenue",
        "closing entries",
    ],
    "wasc_residential_units": 101,
    "category_counts_A_to_F": (1, 4, 16, 24, 16, 40),
    "high_cost_rule": "top 20% of training-fold costs",
    "training_corpus_note": (
        "Linked WAPDA work-order extracts were not released. The same "
        "WAPDA data model is populated from mapped AHS public-use files."
    ),
}

HIGH_COST_THRESHOLD_USD = 1428.0


def calculate_metrics(
    actual: list[float],
    predicted: list[float],
    threshold: float = HIGH_COST_THRESHOLD_USD,
) -> dict[str, Any]:
    """Unweighted regression and high-cost retrieval metrics."""
    if len(actual) == 0 or len(actual) != len(predicted):
        raise ValueError("actual and predicted must be non-empty and equal length")
    errors = [p - a for a, p in zip(actual, predicted)]
    mae = sum(abs(e) for e in errors) / len(errors)
    rmse = math.sqrt(sum(e * e for e in errors) / len(errors))
    actual_high = [a >= threshold for a in actual]
    predicted_high = [p >= threshold for p in predicted]
    tp = sum(1 for ah, ph in zip(actual_high, predicted_high) if ah and ph)
    fp = sum(1 for ah, ph in zip(actual_high, predicted_high) if (not ah) and ph)
    fn = sum(1 for ah, ph in zip(actual_high, predicted_high) if ah and (not ph))
    precision = None if (tp + fp) == 0 else tp / (tp + fp)
    recall = None if (tp + fn) == 0 else tp / (tp + fn)
    if precision is None or recall is None or precision + recall == 0:
        f1 = None
    else:
        f1 = 2 * precision * recall / (precision + recall)
    return {
        "count": len(actual),
        "mae_usd": mae,
        "rmse_usd": rmse,
        "high_cost_precision": precision,
        "high_cost_recall": recall,
        "high_cost_f1": f1,
        "true_positive": tp,
        "false_positive": fp,
        "false_negative": fn,
    }


def demo_fixture() -> None:
    """Tiny synthetic check an examiner can recompute by hand."""
    actual = [0.0, 100.0, 800.0, 2000.0, 3000.0]
    predicted = [50.0, 120.0, 700.0, 1500.0, 2500.0]
    metrics = calculate_metrics(actual, predicted, threshold=1428.0)
    print("Synthetic metric fixture (threshold = 1428)")
    print(f"  MAE  = {metrics['mae_usd']:.4f}")
    print(f"  RMSE = {metrics['rmse_usd']:.4f}")
    print(f"  P/R/F1 = {metrics['high_cost_precision']:.4f} / "
          f"{metrics['high_cost_recall']:.4f} / {metrics['high_cost_f1']:.4f}")
    # Hand targets: errors = 50,20,-100,-500,-500
    expected_mae = (50 + 20 + 100 + 500 + 500) / 5
    assert abs(metrics["mae_usd"] - expected_mae) < 1e-9
    print("  Hand-check MAE matched.")


REPORT_SYSTEMS = [
    ("type_median", "ahs-training-fold-v1", "ahs-baselines-models-v1", "type_median"),
    ("prior_cost", "ahs-training-fold-v1", "ahs-baselines-models-v1", "prior_cost"),
    ("linear_regression", "ahs-training-fold-v1", "ahs-baselines-models-v1", "linear_regression"),
    ("random_forest_tuned", "ahs-feature-engineering-v1", "ahs-model-tuning-v1", "random_forest"),
    ("gradient_boosting_tuned", "ahs-feature-engineering-v1", "ahs-model-tuning-v1", "gradient_boosting"),
    ("xgboost_tuned", "ahs-feature-engineering-v1", "ahs-xgboost-tuning-v1", "xgboost"),
    ("xgboost_absolute", "ahs-feature-engineering-v1", "ahs-xgboost-robust-loss-v1", "xgboost_absolute"),
]


def print_report_table(repo_root: Path) -> None:
    base = (
        repo_root
        / "artifacts"
        / "experiments"
        / "public-corpus-v0.2.0-ahs"
        / "ahs-grouped-temporal-v1"
    )
    if not base.exists():
        print("No local experiment artifacts found; skipping aggregate reprint.")
        return
    print("\nAggregate primary metrics from audited experiment records")
    print(f"{'system':24} {'val_MAE':>10} {'test_MAE':>10} {'sens_MAE':>10} {'test_F1':>8}")
    for label, prep, exp, model in REPORT_SYSTEMS:
        path = base / prep / exp / "metrics.json"
        if not path.exists():
            print(f"{label:24} missing {path.name}")
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        block = data["results"][model]
        val = block["primary"]["validation"]
        test = block["primary"]["test"]
        sens = block["pre_2023_cap_sensitivity"]["test"]
        f1 = test.get("high_cost_f1")
        f1_txt = f"{f1:.4f}" if f1 is not None else "—"
        print(
            f"{label:24} {val['mae_usd']:10.2f} {test['mae_usd']:10.2f} "
            f"{sens['mae_usd']:10.2f} {f1_txt:>8}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--metrics-root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="Repository root that may contain artifacts/experiments",
    )
    args = parser.parse_args()

    print("WAPDA data model constants")
    for key, value in WAPDA_DATA_MODEL.items():
        print(f"  {key}: {value}")
    print()
    demo_fixture()
    print_report_table(args.metrics_root.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
