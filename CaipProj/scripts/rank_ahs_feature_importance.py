#!/usr/bin/env python3
"""Rank AHS matrix columns by how much they affect a fitted model's predictions.

Default model: validation-tuned XGBoost (`ahs-xgboost-tuning-v1`), the best
balanced post-next-steps estimator on primary-test MAE/RMSE/F1.

Two rankings are produced:
  1. Built-in importance (XGBoost gain, or sklearn feature_importances_).
  2. Optional permutation importance on the validation primary view only
     (held-out from fit; does not touch the test split).

Example:
  PYTHONPATH=src .venv/bin/python scripts/rank_ahs_feature_importance.py --top 25
  PYTHONPATH=src .venv/bin/python scripts/rank_ahs_feature_importance.py \\
      --permutation --permutation-repeats 5 --top 20
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_RELEASE = "public-corpus-v0.2.0-ahs"
DEFAULT_SPLIT = "ahs-grouped-temporal-v1"
DEFAULT_PREPROCESSOR = "ahs-feature-engineering-v1"
DEFAULT_EXPERIMENT = "ahs-xgboost-tuning-v1"
DEFAULT_MODEL = "xgboost"


def base_feature_name(column: str) -> str:
    """Map one-hot / missing-indicator columns back to the harmonized feature."""
    if "__" in column:
        return column.split("__", 1)[0]
    return column


def rank_builtin(
    model: Any, feature_columns: list[str], importance_type: str
) -> list[dict[str, Any]]:
    """Return per-column importance from the fitted estimator."""
    if hasattr(model, "get_booster"):
        booster = model.get_booster()
        score = booster.get_score(importance_type=importance_type)
        # XGBoost keys are f0, f1, ... when no feature names were set at fit time.
        values = []
        for index, name in enumerate(feature_columns):
            values.append(float(score.get(f"f{index}", score.get(name, 0.0))))
    elif hasattr(model, "feature_importances_"):
        values = [float(v) for v in model.feature_importances_]
    else:
        raise TypeError(
            f"{type(model).__name__} does not expose feature importance; "
            "use --permutation"
        )
    if len(values) != len(feature_columns):
        raise ValueError("importance length does not match feature columns")
    total = sum(values)
    rows = []
    for name, value in zip(feature_columns, values, strict=True):
        rows.append(
            {
                "column": name,
                "base_feature": base_feature_name(name),
                "importance": value,
                "importance_share": (value / total) if total else 0.0,
            }
        )
    rows.sort(key=lambda row: row["importance"], reverse=True)
    for rank, row in enumerate(rows, start=1):
        row["rank"] = rank
    return rows


def aggregate_by_base(column_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sum one-hot pieces so each original survey field gets one score."""
    totals: dict[str, float] = {}
    for row in column_rows:
        totals[row["base_feature"]] = totals.get(row["base_feature"], 0.0) + float(
            row["importance"]
        )
    total = sum(totals.values())
    rows = [
        {
            "base_feature": name,
            "importance": value,
            "importance_share": (value / total) if total else 0.0,
            "matrix_column_count": sum(
                1 for row in column_rows if row["base_feature"] == name
            ),
        }
        for name, value in totals.items()
    ]
    rows.sort(key=lambda row: row["importance"], reverse=True)
    for rank, row in enumerate(rows, start=1):
        row["rank"] = rank
    return rows


def rank_permutation(
    model: Any,
    features: Any,
    target: Any,
    feature_columns: list[str],
    repeats: int,
    random_state: int,
    n_jobs: int,
) -> list[dict[str, Any]]:
    """MAE increase when each column is shuffled on validation primary rows."""
    from sklearn.inspection import permutation_importance

    result = permutation_importance(
        model,
        features,
        target,
        scoring="neg_mean_absolute_error",
        n_repeats=repeats,
        random_state=random_state,
        n_jobs=n_jobs,
    )
    # sklearn returns increase in score; with neg MAE, larger mean means more harmful when shuffled.
    values = [float(v) for v in result.importances_mean]
    stds = [float(v) for v in result.importances_std]
    total = sum(max(v, 0.0) for v in values)
    rows = []
    for name, value, std in zip(feature_columns, values, stds, strict=True):
        rows.append(
            {
                "column": name,
                "base_feature": base_feature_name(name),
                "importance": value,
                "importance_std": std,
                "importance_share": (max(value, 0.0) / total) if total else 0.0,
            }
        )
    rows.sort(key=lambda row: row["importance"], reverse=True)
    for rank, row in enumerate(rows, start=1):
        row["rank"] = rank
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError("no rows to write")
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def print_table(title: str, rows: list[dict[str, Any]], top: int, key: str = "column") -> None:
    print(f"\n{title}")
    print(f"{'rank':>4}  {'importance':>12}  {'share':>8}  {key}")
    for row in rows[:top]:
        label = row.get(key) or row.get("base_feature")
        print(
            f"{row['rank']:4d}  {row['importance']:12.6f}  "
            f"{row['importance_share']:8.2%}  {label}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Rank AHS feature columns by prediction importance."
    )
    parser.add_argument("--release", default=DEFAULT_RELEASE)
    parser.add_argument("--split", default=DEFAULT_SPLIT)
    parser.add_argument("--preprocessor", default=DEFAULT_PREPROCESSOR)
    parser.add_argument("--experiment", default=DEFAULT_EXPERIMENT)
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Model artifact stem, e.g. xgboost")
    parser.add_argument(
        "--importance-type",
        default="gain",
        choices=("gain", "weight", "cover", "total_gain", "total_cover"),
        help="XGBoost booster score type (ignored for sklearn-only estimators)",
    )
    parser.add_argument("--top", type=int, default=25)
    parser.add_argument(
        "--permutation",
        action="store_true",
        help="Also run validation-primary permutation importance (slower)",
    )
    parser.add_argument("--permutation-repeats", type=int, default=5)
    parser.add_argument("--permutation-jobs", type=int, default=1)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory for CSV outputs (default: artifacts/diagnostics/...)",
    )
    args = parser.parse_args()

    import joblib
    import numpy as np

    from caip_maintenance.modeling.ahs_experiment import _load_inputs

    experiment_dir = (
        ROOT
        / "artifacts"
        / "experiments"
        / args.release
        / args.split
        / args.preprocessor
        / args.experiment
    )
    model_path = experiment_dir / "models" / f"{args.model}.joblib"
    if not model_path.is_file():
        raise FileNotFoundError(f"model not found: {model_path}")

    print(f"Loading features from preprocessor {args.preprocessor} ...")
    inputs = _load_inputs(ROOT, args.release, args.split, args.preprocessor, np)
    feature_columns: list[str] = list(inputs["feature_columns"])
    print(f"Loading model {model_path.relative_to(ROOT)} ...")
    model = joblib.load(model_path)

    builtin_rows = rank_builtin(model, feature_columns, args.importance_type)
    base_rows = aggregate_by_base(builtin_rows)

    output_dir = args.output_dir or (
        ROOT
        / "artifacts"
        / "diagnostics"
        / args.release
        / args.split
        / args.preprocessor
        / args.experiment
        / "feature_importance"
    )
    write_csv(output_dir / "column_importance_builtin.csv", builtin_rows)
    write_csv(output_dir / "base_feature_importance_builtin.csv", base_rows)

    print_table(
        f"Top {args.top} matrix columns ({args.importance_type} / builtin)",
        builtin_rows,
        args.top,
        key="column",
    )
    print_table(
        f"Top {args.top} base features (summed one-hots)",
        base_rows,
        args.top,
        key="base_feature",
    )

    summary: dict[str, Any] = {
        "release": args.release,
        "split": args.split,
        "preprocessor": args.preprocessor,
        "experiment": args.experiment,
        "model": args.model,
        "importance_type": args.importance_type,
        "feature_column_count": len(feature_columns),
        "top_columns": builtin_rows[: args.top],
        "top_base_features": base_rows[: args.top],
        "claim_boundary": {
            "public_proxy_task_only": True,
            "is_wapda_data": False,
            "is_validated_wasc_or_wapda_forecast": False,
        },
    }

    if args.permutation:
        validation_mask = (inputs["split_name"] == "validation") & inputs[
            "include_in_primary_metrics"
        ]
        print(
            f"\nRunning permutation importance on "
            f"{int(validation_mask.sum())} validation primary rows "
            f"({args.permutation_repeats} repeats) ..."
        )
        perm_rows = rank_permutation(
            model,
            inputs["features"][validation_mask],
            inputs["target"][validation_mask],
            feature_columns,
            repeats=args.permutation_repeats,
            random_state=args.seed,
            n_jobs=args.permutation_jobs,
        )
        perm_base = aggregate_by_base(perm_rows)
        write_csv(output_dir / "column_importance_permutation.csv", perm_rows)
        write_csv(output_dir / "base_feature_importance_permutation.csv", perm_base)
        print_table(
            f"Top {args.top} matrix columns (permutation MAE impact)",
            perm_rows,
            args.top,
            key="column",
        )
        print_table(
            f"Top {args.top} base features (permutation, summed)",
            perm_base,
            args.top,
            key="base_feature",
        )
        summary["permutation"] = {
            "split": "validation",
            "view": "primary",
            "repeats": args.permutation_repeats,
            "top_columns": perm_rows[: args.top],
            "top_base_features": perm_base[: args.top],
        }

    summary_path = output_dir / "feature_importance_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"\nWrote rankings to {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
