"""Residual, subgroup, survey-weight, and decision-utility review for the frozen AHS experiment."""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
from pathlib import Path
import tomllib
from typing import Any

from caip_maintenance.data.ahs import DATASET_RELEASE, TASK_ID
from caip_maintenance.data.ahs_split import SPLIT_ID
from caip_maintenance.data.common import sha256_file
from caip_maintenance.features.ahs_preprocessing import PREPROCESSOR_ID
from caip_maintenance.modeling.ahs_experiment import EXPERIMENT_ID, SYSTEM_NAMES


REVIEW_ID = "ahs-diagnostic-review-v1"
HIGH_COST_THRESHOLD = 1428.0
SNAPSHOT_JOIN_FIELDS = [
    "snapshot_id",
    "building_type_code",
    "division_code",
    "survey_weight",
]
PREDICTION_SYSTEM_FIELDS = [f"prediction_{name}_usd" for name in SYSTEM_NAMES]


def build_ahs_diagnostic_review(
    project_root: Path,
    release: str = DATASET_RELEASE,
    split_id: str = SPLIT_ID,
    preprocessor_id: str = PREPROCESSOR_ID,
    experiment_id: str = EXPERIMENT_ID,
    review_id: str = REVIEW_ID,
) -> Path:
    """Build an immutable diagnostic review of the frozen AHS comparison. Does not fit models."""
    spec, config_path = _load_spec(project_root, review_id)
    _validate_spec(spec, release, split_id, preprocessor_id, experiment_id, review_id)
    experiment_dir = _experiment_dir(
        project_root, release, split_id, preprocessor_id, experiment_id
    )
    experiment_manifest = _load_verified_experiment_manifest(experiment_dir)
    rows = _load_joined_rows(project_root, release, experiment_dir, experiment_manifest)
    threshold = float(spec["high_cost_threshold_usd"])

    residual_summary = _residual_summary(rows, threshold)
    subgroup_metrics = _subgroup_metrics(rows, spec, threshold)
    survey_weight_metrics = _survey_weight_metrics(rows, spec, threshold)
    decision_utility = _decision_utility(
        residual_summary, subgroup_metrics, survey_weight_metrics, rows, threshold
    )

    output_dir = _review_dir(
        project_root, release, split_id, preprocessor_id, experiment_id, review_id
    )
    if output_dir.exists():
        raise FileExistsError(
            f"diagnostic review already exists: {output_dir}; artifacts are immutable"
        )
    output_dir.mkdir(parents=True)

    artifacts = {
        "residual_summary.json": residual_summary,
        "subgroup_metrics.json": subgroup_metrics,
        "survey_weight_metrics.json": survey_weight_metrics,
        "decision_utility.json": decision_utility,
    }
    output_hashes: dict[str, str] = {}
    for name, payload in artifacts.items():
        path = output_dir / name
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        output_hashes[name] = sha256_file(path)

    manifest = {
        "review_id": review_id,
        "review_contract_version": spec["review_contract_version"],
        "dataset_release": release,
        "split_id": split_id,
        "preprocessor_id": preprocessor_id,
        "experiment_id": experiment_id,
        "task_id": TASK_ID,
        "status": "completed_diagnostic_review_local_analysis_only",
        "built_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "distribution": spec["distribution"],
        "model_fitting": False,
        "hyperparameter_search": False,
        "model_selection": False,
        "promotion_authorized": False,
        "high_cost_threshold_usd": threshold,
        "systems": list(SYSTEM_NAMES),
        "counts": {
            "prediction_rows": len(rows),
            "validation_rows": sum(1 for row in rows if row["split_name"] == "validation"),
            "test_rows": sum(1 for row in rows if row["split_name"] == "test"),
            "training_rows_excluded_from_held_out_diagnostics": sum(
                1 for row in rows if row["split_name"] == "training"
            ),
            "survey_weight_nonmissing": sum(
                1 for row in rows if row["survey_weight"] is not None
            ),
        },
        "source_sha256": {
            "experiment_manifest.json": sha256_file(experiment_dir / "experiment_manifest.json"),
            "predictions.csv": sha256_file(experiment_dir / "predictions.csv"),
            "metrics.json": sha256_file(experiment_dir / "metrics.json"),
            "property_period_snapshot.csv": sha256_file(
                project_root
                / "data"
                / "processed"
                / "releases"
                / release
                / "property_period_snapshot.csv"
            ),
        },
        "experiment_output_sha256": experiment_manifest["output_sha256"],
        "config_sha256": sha256_file(config_path),
        "output_sha256": output_hashes,
        "claim_boundary": {
            "public_proxy_task_only": True,
            "is_wapda_data": False,
            "is_validated_wasc_or_wapda_forecast": False,
            "rhfs_labels_merged": False,
            "nyc_hpd_opened": False,
            "tuning_authorized": False,
            "model_promoted": False,
        },
        "decision": decision_utility["authorization"],
    }
    (output_dir / "review_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return output_dir


def audit_ahs_diagnostic_review(project_root: Path, output_dir: Path) -> dict[str, Any]:
    """Audit that the diagnostic review is immutable, non-fitting, and checksum-bound."""
    manifest = json.loads((output_dir / "review_manifest.json").read_text(encoding="utf-8"))
    review_id = manifest["review_id"]
    spec, config_path = _load_spec(project_root, review_id)
    _validate_spec(
        spec,
        manifest["dataset_release"],
        manifest["split_id"],
        manifest["preprocessor_id"],
        manifest["experiment_id"],
        review_id,
    )
    experiment_dir = _experiment_dir(
        project_root,
        manifest["dataset_release"],
        manifest["split_id"],
        manifest["preprocessor_id"],
        manifest["experiment_id"],
    )
    experiment_manifest = _load_verified_experiment_manifest(experiment_dir)
    checks: list[dict[str, Any]] = []

    _check(
        checks,
        "experiment_artifacts_unchanged",
        manifest.get("experiment_output_sha256") == experiment_manifest.get("output_sha256")
        and manifest.get("source_sha256", {}).get("predictions.csv")
        == sha256_file(experiment_dir / "predictions.csv")
        and manifest.get("source_sha256", {}).get("metrics.json")
        == sha256_file(experiment_dir / "metrics.json")
        and manifest.get("source_sha256", {}).get("experiment_manifest.json")
        == sha256_file(experiment_dir / "experiment_manifest.json"),
        {
            "experiment_dir": str(experiment_dir),
        },
    )
    _check(
        checks,
        "review_config_unchanged",
        manifest.get("config_sha256") == sha256_file(config_path),
        None,
    )
    output_drift = {
        name: {
            "expected": expected,
            "actual": sha256_file(output_dir / name)
            if (output_dir / name).is_file()
            else None,
        }
        for name, expected in manifest.get("output_sha256", {}).items()
        if not (output_dir / name).is_file() or sha256_file(output_dir / name) != expected
    }
    _check(checks, "review_output_checksums", not output_drift, output_drift or None)
    _check(
        checks,
        "no_model_fitting_or_selection",
        manifest.get("model_fitting") is False
        and manifest.get("hyperparameter_search") is False
        and manifest.get("model_selection") is False
        and manifest.get("promotion_authorized") is False
        and spec.get("model_fitting") is False
        and spec.get("hyperparameter_search") is False
        and spec.get("model_selection") is False
        and spec.get("promotion_authorized") is False,
        {
            "promotion_authorized": manifest.get("promotion_authorized"),
            "model_fitting": manifest.get("model_fitting"),
        },
    )
    _check(
        checks,
        "claim_boundary_preserved",
        manifest.get("claim_boundary")
        == {
            "public_proxy_task_only": True,
            "is_wapda_data": False,
            "is_validated_wasc_or_wapda_forecast": False,
            "rhfs_labels_merged": False,
            "nyc_hpd_opened": False,
            "tuning_authorized": False,
            "model_promoted": False,
        },
        manifest.get("claim_boundary"),
    )

    rows = _load_joined_rows(
        project_root, manifest["dataset_release"], experiment_dir, experiment_manifest
    )
    rebuilt = {
        "residual_summary.json": _residual_summary(rows, HIGH_COST_THRESHOLD),
        "subgroup_metrics.json": _subgroup_metrics(rows, spec, HIGH_COST_THRESHOLD),
        "survey_weight_metrics.json": _survey_weight_metrics(
            rows, spec, HIGH_COST_THRESHOLD
        ),
        "decision_utility.json": _decision_utility(
            _residual_summary(rows, HIGH_COST_THRESHOLD),
            _subgroup_metrics(rows, spec, HIGH_COST_THRESHOLD),
            _survey_weight_metrics(rows, spec, HIGH_COST_THRESHOLD),
            rows,
            HIGH_COST_THRESHOLD,
        ),
    }
    rebuilt_match = True
    mismatch: dict[str, Any] = {}
    for name, payload in rebuilt.items():
        stored_text = (output_dir / name).read_text(encoding="utf-8")
        rebuilt_text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
        if stored_text != rebuilt_text:
            rebuilt_match = False
            mismatch[name] = {
                "stored_sha256": sha256_file(output_dir / name),
                "rebuilt_sha256": sha256(rebuilt_text.encode("utf-8")).hexdigest(),
            }
    _check(checks, "review_tables_reproducible_from_frozen_predictions", rebuilt_match, mismatch or None)
    _check(
        checks,
        "held_out_row_counts",
        manifest.get("counts", {}).get("prediction_rows") == len(rows)
        and manifest.get("counts", {}).get("validation_rows")
        == sum(1 for row in rows if row["split_name"] == "validation")
        and manifest.get("counts", {}).get("test_rows")
        == sum(1 for row in rows if row["split_name"] == "test"),
        manifest.get("counts"),
    )
    decision = json.loads((output_dir / "decision_utility.json").read_text(encoding="utf-8"))
    _check(
        checks,
        "tuning_and_promotion_remain_unauthorized",
        decision.get("authorization", {}).get("authorize_hyperparameter_search") is False
        and decision.get("authorization", {}).get("authorize_model_promotion") is False
        and decision.get("authorization", {}).get("recommended_primary_estimator")
        == "type_median_as_mae_reference_only"
        and decision.get("authorization", {}).get("recommended_high_cost_triage")
        == "prior_cost_baseline",
        decision.get("authorization"),
    )
    _check(
        checks,
        "distribution_local_analysis_only",
        manifest.get("distribution") == "local-analysis-only",
        manifest.get("distribution"),
    )
    _check(
        checks,
        "threshold_matches_frozen_experiment",
        float(manifest.get("high_cost_threshold_usd", -1)) == HIGH_COST_THRESHOLD
        and float(spec.get("high_cost_threshold_usd", -1)) == HIGH_COST_THRESHOLD,
        manifest.get("high_cost_threshold_usd"),
    )

    failed = [check["check_id"] for check in checks if check["status"] == "failed"]
    return {
        "review_id": review_id,
        "experiment_id": manifest["experiment_id"],
        "dataset_release": manifest["dataset_release"],
        "task_id": manifest["task_id"],
        "status": "passed" if not failed else "failed",
        "summary": {"passed": len(checks) - len(failed), "failed": len(failed)},
        "failed_checks": failed,
        "checks": checks,
    }


def calculate_unweighted_metrics(
    actual: list[float],
    predicted: list[float],
    threshold: float,
) -> dict[str, Any]:
    """Calculate unweighted regression and threshold-retrieval metrics without model deps."""
    if len(actual) != len(predicted):
        raise ValueError("metric arrays must have equal lengths")
    if not actual:
        raise ValueError("cannot calculate metrics for an empty view")
    if any(not math.isfinite(value) for value in actual + predicted):
        raise ValueError("metric inputs must be finite")
    abs_errors = [abs(pred - act) for act, pred in zip(actual, predicted)]
    sq_errors = [(pred - act) ** 2 for act, pred in zip(actual, predicted)]
    true_positive = false_positive = true_negative = false_negative = 0
    for act, pred in zip(actual, predicted):
        actual_high = act >= threshold
        predicted_high = pred >= threshold
        if actual_high and predicted_high:
            true_positive += 1
        elif not actual_high and predicted_high:
            false_positive += 1
        elif not actual_high and not predicted_high:
            true_negative += 1
        else:
            false_negative += 1
    precision = _safe_ratio(true_positive, true_positive + false_positive)
    recall = _safe_ratio(true_positive, true_positive + false_negative)
    f1 = (
        None
        if precision is None or recall is None or precision + recall == 0
        else 2 * precision * recall / (precision + recall)
    )
    return {
        "count": len(actual),
        "mae_usd": float(sum(abs_errors) / len(abs_errors)),
        "rmse_usd": float(math.sqrt(sum(sq_errors) / len(sq_errors))),
        "actual_high_cost_count": true_positive + false_negative,
        "predicted_high_cost_count": true_positive + false_positive,
        "high_cost_true_positive": true_positive,
        "high_cost_false_positive": false_positive,
        "high_cost_true_negative": true_negative,
        "high_cost_false_negative": false_negative,
        "high_cost_precision": precision,
        "high_cost_recall": recall,
        "high_cost_f1": f1,
    }


def calculate_weighted_metrics(
    actual: list[float],
    predicted: list[float],
    weights: list[float],
    threshold: float,
) -> dict[str, Any]:
    """Calculate survey-weighted MAE/RMSE and high-cost retrieval metrics."""
    if not (len(actual) == len(predicted) == len(weights)):
        raise ValueError("weighted metric arrays must have equal lengths")
    if not actual:
        raise ValueError("cannot calculate weighted metrics for an empty view")
    if any(weight <= 0 or not math.isfinite(weight) for weight in weights):
        raise ValueError("survey weights must be positive and finite")
    if any(not math.isfinite(value) for value in actual + predicted):
        raise ValueError("metric inputs must be finite")
    total_weight = sum(weights)
    abs_error = sum(weight * abs(pred - act) for act, pred, weight in zip(actual, predicted, weights))
    sq_error = sum(weight * (pred - act) ** 2 for act, pred, weight in zip(actual, predicted, weights))
    true_positive = false_positive = true_negative = false_negative = 0.0
    for act, pred, weight in zip(actual, predicted, weights):
        actual_high = act >= threshold
        predicted_high = pred >= threshold
        if actual_high and predicted_high:
            true_positive += weight
        elif not actual_high and predicted_high:
            false_positive += weight
        elif not actual_high and not predicted_high:
            true_negative += weight
        else:
            false_negative += weight
    precision = _safe_ratio(true_positive, true_positive + false_positive)
    recall = _safe_ratio(true_positive, true_positive + false_negative)
    f1 = (
        None
        if precision is None or recall is None or precision + recall == 0
        else 2 * precision * recall / (precision + recall)
    )
    return {
        "count": len(actual),
        "weight_sum": float(total_weight),
        "mae_usd": float(abs_error / total_weight),
        "rmse_usd": float(math.sqrt(sq_error / total_weight)),
        "actual_high_cost_weight": float(true_positive + false_negative),
        "predicted_high_cost_weight": float(true_positive + false_positive),
        "high_cost_true_positive_weight": float(true_positive),
        "high_cost_false_positive_weight": float(false_positive),
        "high_cost_true_negative_weight": float(true_negative),
        "high_cost_false_negative_weight": float(false_negative),
        "high_cost_precision": precision,
        "high_cost_recall": recall,
        "high_cost_f1": f1,
    }


def _load_spec(project_root: Path, review_id: str) -> tuple[dict[str, Any], Path]:
    if review_id != REVIEW_ID:
        raise ValueError(f"supported AHS diagnostic review is {REVIEW_ID!r}")
    path = project_root / "configs" / "reviews" / "ahs_diagnostic_review_v1.toml"
    with path.open("rb") as handle:
        return tomllib.load(handle), path


def _validate_spec(
    spec: dict[str, Any],
    release: str,
    split_id: str,
    preprocessor_id: str,
    experiment_id: str,
    review_id: str,
) -> None:
    expected = {
        "review_id": review_id,
        "dataset_release": release,
        "split_id": split_id,
        "preprocessor_id": preprocessor_id,
        "experiment_id": experiment_id,
        "task_id": TASK_ID,
    }
    if any(spec.get(key) != value for key, value in expected.items()):
        raise ValueError("AHS diagnostic review specification does not match the request")
    if float(spec.get("high_cost_threshold_usd", -1)) != HIGH_COST_THRESHOLD:
        raise ValueError("diagnostic review must use the frozen USD 1,428 threshold")
    if list(spec.get("systems", [])) != list(SYSTEM_NAMES):
        raise ValueError("diagnostic review system order or set changed")
    if spec.get("model_fitting") is not False or spec.get("model_selection") is not False:
        raise ValueError("diagnostic review cannot fit or select models")
    if spec.get("hyperparameter_search") is not False:
        raise ValueError("diagnostic review cannot authorize hyperparameter search")
    if spec.get("promotion_authorized") is not False:
        raise ValueError("diagnostic review cannot authorize promotion")
    if spec.get("distribution") != "local-analysis-only":
        raise ValueError("diagnostic review remains local-analysis-only")


def _experiment_dir(
    project_root: Path,
    release: str,
    split_id: str,
    preprocessor_id: str,
    experiment_id: str,
) -> Path:
    return (
        project_root
        / "artifacts"
        / "experiments"
        / release
        / split_id
        / preprocessor_id
        / experiment_id
    )


def _review_dir(
    project_root: Path,
    release: str,
    split_id: str,
    preprocessor_id: str,
    experiment_id: str,
    review_id: str,
) -> Path:
    return (
        project_root
        / "artifacts"
        / "reviews"
        / release
        / split_id
        / preprocessor_id
        / experiment_id
        / review_id
    )


def _load_verified_experiment_manifest(experiment_dir: Path) -> dict[str, Any]:
    manifest_path = experiment_dir / "experiment_manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"missing experiment manifest: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("experiment_id") != EXPERIMENT_ID:
        raise ValueError("diagnostic review requires ahs-baselines-models-v1")
    if manifest.get("task_id") != TASK_ID:
        raise ValueError("diagnostic review task mismatch")
    if manifest.get("claim_boundary", {}).get("model_selection") is True:
        raise ValueError("source experiment unexpectedly selected a model")
    for name, expected in manifest.get("output_sha256", {}).items():
        path = experiment_dir / name
        if not path.is_file() or sha256_file(path) != expected:
            raise ValueError(f"experiment checksum drift before diagnostic review: {name}")
    return manifest


def _load_joined_rows(
    project_root: Path,
    release: str,
    experiment_dir: Path,
    experiment_manifest: dict[str, Any],
) -> list[dict[str, Any]]:
    predictions_path = experiment_dir / "predictions.csv"
    if sha256_file(predictions_path) != experiment_manifest["output_sha256"]["predictions.csv"]:
        raise ValueError("predictions.csv checksum drift")
    snapshot_path = (
        project_root
        / "data"
        / "processed"
        / "releases"
        / release
        / "property_period_snapshot.csv"
    )
    snapshot_by_id = _load_snapshot_attributes(snapshot_path)
    rows: list[dict[str, Any]] = []
    with predictions_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for raw in reader:
            snapshot = snapshot_by_id.get(raw["snapshot_id"])
            if snapshot is None:
                raise ValueError(f"prediction snapshot missing from release: {raw['snapshot_id']}")
            target = float(raw["target_amount_usd"])
            row = {
                "snapshot_id": raw["snapshot_id"],
                "split_name": raw["split_name"],
                "label_wave_year": int(raw["label_wave_year"]),
                "include_in_primary_metrics": _as_bool(raw["include_in_primary_metrics"]),
                "include_in_pre_2023_cap_sensitivity": _as_bool(
                    raw["include_in_pre_2023_cap_sensitivity"]
                ),
                "target_amount_usd": target,
                "is_high_cost": _as_bool(raw["is_high_cost"]),
                "target_band": _target_band(target, HIGH_COST_THRESHOLD),
                "building_type_code": snapshot["building_type_code"] or "missing",
                "division_code": snapshot["division_code"] or "missing",
                "survey_weight": snapshot["survey_weight"],
                "predictions": {
                    name: float(raw[f"prediction_{name}_usd"]) for name in SYSTEM_NAMES
                },
            }
            rows.append(row)
    if len(rows) != experiment_manifest.get("counts", {}).get("rows"):
        raise ValueError("prediction row count does not match experiment manifest")
    return rows


def _load_snapshot_attributes(path: Path) -> dict[str, dict[str, Any]]:
    attributes: dict[str, dict[str, Any]] = {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            weight_raw = (row.get("survey_weight") or "").strip()
            weight = None
            if weight_raw not in {"", "NA", "N/A", "nan", "NaN"}:
                weight = float(weight_raw)
                if not math.isfinite(weight) or weight <= 0:
                    weight = None
            attributes[row["snapshot_id"]] = {
                "building_type_code": (row.get("building_type_code") or "").strip(),
                "division_code": (row.get("division_code") or "").strip(),
                "survey_weight": weight,
            }
    return attributes


def _residual_summary(rows: list[dict[str, Any]], threshold: float) -> dict[str, Any]:
    summary: dict[str, Any] = {"threshold_usd": threshold, "systems": {}}
    for system in SYSTEM_NAMES:
        summary["systems"][system] = {
            "primary": {
                split: _residual_block(
                    [
                        row
                        for row in rows
                        if row["split_name"] == split and row["include_in_primary_metrics"]
                    ],
                    system,
                    threshold,
                )
                for split in ("validation", "test")
            },
            "pre_2023_cap_sensitivity": {
                split: _residual_block(
                    [
                        row
                        for row in rows
                        if row["split_name"] == split
                        and row["include_in_pre_2023_cap_sensitivity"]
                    ],
                    system,
                    threshold,
                )
                for split in ("validation", "test")
            },
        }
    return summary


def _residual_block(
    rows: list[dict[str, Any]], system: str, threshold: float
) -> dict[str, Any]:
    if not rows:
        raise ValueError(f"no rows available for residual summary: {system}")
    residuals = [row["predictions"][system] - row["target_amount_usd"] for row in rows]
    abs_residuals = [abs(value) for value in residuals]
    actual = [row["target_amount_usd"] for row in rows]
    predicted = [row["predictions"][system] for row in rows]
    metrics = calculate_unweighted_metrics(actual, predicted, threshold)
    by_band = {
        band: _band_residual_stats(
            [
                (row["predictions"][system] - row["target_amount_usd"], row["target_amount_usd"])
                for row in rows
                if row["target_band"] == band
            ]
        )
        for band in ("zero", "positive_below_threshold", "high_cost")
    }
    return {
        "count": len(rows),
        "mae_usd": metrics["mae_usd"],
        "rmse_usd": metrics["rmse_usd"],
        "high_cost_f1": metrics["high_cost_f1"],
        "mean_residual_usd": _mean(residuals),
        "median_residual_usd": _percentile(residuals, 50),
        "p90_abs_error_usd": _percentile(abs_residuals, 90),
        "p99_abs_error_usd": _percentile(abs_residuals, 99),
        "max_abs_error_usd": max(abs_residuals),
        "negative_prediction_count": sum(1 for value in predicted if value < 0),
        "by_target_band": by_band,
    }


def _band_residual_stats(pairs: list[tuple[float, float]]) -> dict[str, Any]:
    if not pairs:
        return {
            "count": 0,
            "mae_usd": None,
            "mean_residual_usd": None,
            "p90_abs_error_usd": None,
        }
    residuals = [residual for residual, _ in pairs]
    abs_residuals = [abs(residual) for residual in residuals]
    return {
        "count": len(pairs),
        "mae_usd": _mean(abs_residuals),
        "mean_residual_usd": _mean(residuals),
        "p90_abs_error_usd": _percentile(abs_residuals, 90),
    }


def _subgroup_metrics(
    rows: list[dict[str, Any]], spec: dict[str, Any], threshold: float
) -> dict[str, Any]:
    minimum_rows = int(spec["minimum_subgroup_rows"])
    result: dict[str, Any] = {
        "minimum_subgroup_rows": minimum_rows,
        "dimensions": {},
    }
    for dimension in spec["subgroup_dimensions"]:
        result["dimensions"][dimension] = {
            "primary": {
                split: _dimension_split_metrics(
                    [
                        row
                        for row in rows
                        if row["split_name"] == split and row["include_in_primary_metrics"]
                    ],
                    dimension,
                    threshold,
                    minimum_rows,
                )
                for split in ("validation", "test")
            },
            "pre_2023_cap_sensitivity": {
                split: _dimension_split_metrics(
                    [
                        row
                        for row in rows
                        if row["split_name"] == split
                        and row["include_in_pre_2023_cap_sensitivity"]
                    ],
                    dimension,
                    threshold,
                    minimum_rows,
                )
                for split in ("validation", "test")
            },
        }
    return result


def _dimension_split_metrics(
    rows: list[dict[str, Any]],
    dimension: str,
    threshold: float,
    minimum_rows: int,
) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        key = str(row[dimension])
        groups.setdefault(key, []).append(row)
    reported: dict[str, Any] = {}
    suppressed: list[dict[str, Any]] = []
    for key, group_rows in sorted(groups.items(), key=lambda item: (-len(item[1]), item[0])):
        if len(group_rows) < minimum_rows:
            suppressed.append({"group": key, "count": len(group_rows)})
            continue
        reported[key] = {
            "count": len(group_rows),
            "systems": {
                system: calculate_unweighted_metrics(
                    [row["target_amount_usd"] for row in group_rows],
                    [row["predictions"][system] for row in group_rows],
                    threshold,
                )
                for system in SYSTEM_NAMES
            },
        }
    return {
        "groups_reported": reported,
        "groups_suppressed_below_minimum_rows": suppressed,
    }


def _survey_weight_metrics(
    rows: list[dict[str, Any]], spec: dict[str, Any], threshold: float
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "weight_field": spec["survey_weight_field"],
        "views": {},
    }
    for view_name, flag in (
        ("primary", "include_in_primary_metrics"),
        ("pre_2023_cap_sensitivity", "include_in_pre_2023_cap_sensitivity"),
    ):
        result["views"][view_name] = {}
        for split in ("validation", "test"):
            split_rows = [
                row for row in rows if row["split_name"] == split and row[flag]
            ]
            weighted_rows = [row for row in split_rows if row["survey_weight"] is not None]
            coverage = {
                "rows": len(split_rows),
                "weighted_rows": len(weighted_rows),
                "weight_coverage_rate": (
                    None if not split_rows else len(weighted_rows) / len(split_rows)
                ),
                "weight_sum": float(sum(row["survey_weight"] for row in weighted_rows)),
            }
            unweighted = {
                system: calculate_unweighted_metrics(
                    [row["target_amount_usd"] for row in split_rows],
                    [row["predictions"][system] for row in split_rows],
                    threshold,
                )
                for system in SYSTEM_NAMES
            }
            weighted = {
                system: calculate_weighted_metrics(
                    [row["target_amount_usd"] for row in weighted_rows],
                    [row["predictions"][system] for row in weighted_rows],
                    [float(row["survey_weight"]) for row in weighted_rows],
                    threshold,
                )
                for system in SYSTEM_NAMES
            }
            ranking_changes = []
            unweighted_mae_order = sorted(
                SYSTEM_NAMES, key=lambda name: unweighted[name]["mae_usd"]
            )
            weighted_mae_order = sorted(
                SYSTEM_NAMES, key=lambda name: weighted[name]["mae_usd"]
            )
            if unweighted_mae_order != weighted_mae_order:
                ranking_changes.append(
                    {
                        "metric": "mae_usd",
                        "unweighted_order": unweighted_mae_order,
                        "weighted_order": weighted_mae_order,
                    }
                )
            result["views"][view_name][split] = {
                "coverage": coverage,
                "unweighted": unweighted,
                "survey_weighted": weighted,
                "ranking_changes": ranking_changes,
            }
    return result


def _decision_utility(
    residual_summary: dict[str, Any],
    subgroup_metrics: dict[str, Any],
    survey_weight_metrics: dict[str, Any],
    rows: list[dict[str, Any]],
    threshold: float,
) -> dict[str, Any]:
    primary_test = {
        system: residual_summary["systems"][system]["primary"]["test"]
        for system in SYSTEM_NAMES
    }
    primary_validation = {
        system: residual_summary["systems"][system]["primary"]["validation"]
        for system in SYSTEM_NAMES
    }
    sensitivity_test = {
        system: residual_summary["systems"][system]["pre_2023_cap_sensitivity"]["test"]
        for system in SYSTEM_NAMES
    }
    mae_rank_validation = sorted(
        SYSTEM_NAMES, key=lambda name: primary_validation[name]["mae_usd"]
    )
    mae_rank_primary_test = sorted(
        SYSTEM_NAMES, key=lambda name: primary_test[name]["mae_usd"]
    )
    mae_rank_sensitivity_test = sorted(
        SYSTEM_NAMES, key=lambda name: sensitivity_test[name]["mae_usd"]
    )
    f1_rank_primary_test = sorted(
        SYSTEM_NAMES,
        key=lambda name: (
            primary_test[name]["high_cost_f1"] is None,
            -(primary_test[name]["high_cost_f1"] or -1.0),
        ),
    )
    negative_predictions = {
        system: {
            "validation": primary_validation[system]["negative_prediction_count"],
            "primary_test": primary_test[system]["negative_prediction_count"],
            "sensitivity_test": sensitivity_test[system]["negative_prediction_count"],
        }
        for system in SYSTEM_NAMES
    }
    high_cost_band = {
        system: residual_summary["systems"][system]["primary"]["test"]["by_target_band"][
            "high_cost"
        ]
        for system in SYSTEM_NAMES
    }
    zero_band = {
        system: residual_summary["systems"][system]["primary"]["test"]["by_target_band"][
            "zero"
        ]
        for system in SYSTEM_NAMES
    }
    weighted_primary_test = survey_weight_metrics["views"]["primary"]["test"]
    weight_ranking_changed = bool(weighted_primary_test["ranking_changes"])
    building_type_test = subgroup_metrics["dimensions"]["building_type_code"]["primary"][
        "test"
    ]["groups_reported"]
    worst_building_types = sorted(
        (
            {
                "building_type_code": key,
                "count": payload["count"],
                "type_median_mae_usd": payload["systems"]["type_median"]["mae_usd"],
                "gradient_boosting_mae_usd": payload["systems"]["gradient_boosting"][
                    "mae_usd"
                ],
                "prior_cost_high_cost_f1": payload["systems"]["prior_cost"]["high_cost_f1"],
            }
            for key, payload in building_type_test.items()
        ),
        key=lambda item: item["type_median_mae_usd"],
        reverse=True,
    )[:5]

    conflicting_rankings = {
        "validation_mae_leader": mae_rank_validation[0],
        "primary_test_mae_leader": mae_rank_primary_test[0],
        "sensitivity_test_mae_leader": mae_rank_sensitivity_test[0],
        "primary_test_high_cost_f1_leader": f1_rank_primary_test[0],
        "rankings_agree": len(
            {
                mae_rank_validation[0],
                mae_rank_primary_test[0],
                mae_rank_sensitivity_test[0],
            }
        )
        == 1
        and mae_rank_primary_test[0] == f1_rank_primary_test[0],
    }
    return {
        "threshold_usd": threshold,
        "objective_conflict": conflicting_rankings,
        "mae_rankings": {
            "validation": mae_rank_validation,
            "primary_test": mae_rank_primary_test,
            "pre_2023_cap_sensitivity_test": mae_rank_sensitivity_test,
        },
        "high_cost_f1_rankings": {
            "primary_test": f1_rank_primary_test,
        },
        "negative_prediction_counts": negative_predictions,
        "primary_test_error_concentration": {
            "high_cost_band": high_cost_band,
            "zero_band": zero_band,
            "worst_building_types_by_type_median_mae": worst_building_types,
        },
        "survey_weight_effect": {
            "primary_test_weight_coverage_rate": weighted_primary_test["coverage"][
                "weight_coverage_rate"
            ],
            "mae_ranking_changed_under_weights": weight_ranking_changed,
            "ranking_changes": weighted_primary_test["ranking_changes"],
        },
        "authorization": {
            "authorize_hyperparameter_search": False,
            "authorize_model_promotion": False,
            "recommended_primary_estimator": "type_median_as_mae_reference_only",
            "recommended_high_cost_triage": "prior_cost_baseline",
            "rationale": [
                "Validation MAE and sensitivity-test MAE favor type_median, while primary-test MAE favors gradient_boosting by a small margin.",
                "High-cost F1 favors prior_cost, so a single MAE winner is not decision-sufficient.",
                "Linear regression retains negative predictions under the no-clipping policy.",
                "Survey weights do not authorize promotion; they are reported only as a sensitivity check.",
                "No tuning criterion was frozen, so search would invent a selection policy after seeing held-out patterns.",
            ],
        },
        "claim_boundary": {
            "public_proxy_task_only": True,
            "is_wapda_data": False,
            "is_validated_wasc_or_wapda_forecast": False,
        },
        "held_out_row_counts": {
            "validation": sum(1 for row in rows if row["split_name"] == "validation"),
            "test": sum(1 for row in rows if row["split_name"] == "test"),
        },
    }


def _target_band(amount: float, threshold: float) -> str:
    if amount == 0:
        return "zero"
    if amount >= threshold:
        return "high_cost"
    return "positive_below_threshold"


def _as_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"true", "1"}:
        return True
    if normalized in {"false", "0"}:
        return False
    raise ValueError(f"invalid boolean literal: {value!r}")


def _mean(values: list[float]) -> float:
    return float(sum(values) / len(values))


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        raise ValueError("cannot calculate percentile of an empty list")
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    rank = (percentile / 100.0) * (len(ordered) - 1)
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return float(ordered[lower])
    weight = rank - lower
    return float(ordered[lower] * (1 - weight) + ordered[upper] * weight)


def _safe_ratio(numerator: float, denominator: float) -> float | None:
    if denominator == 0:
        return None
    return float(numerator / denominator)


def _check(checks: list[dict[str, Any]], check_id: str, passed: bool, evidence: Any) -> None:
    checks.append(
        {
            "check_id": check_id,
            "status": "passed" if passed else "failed",
            "evidence": evidence,
        }
    )
