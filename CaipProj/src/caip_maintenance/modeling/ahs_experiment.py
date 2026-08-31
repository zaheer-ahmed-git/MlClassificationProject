"""Train, evaluate, persist, and audit the frozen AHS proxy comparison."""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
from pathlib import Path
import platform
import tomllib
from typing import Any

from caip_maintenance.data.ahs import DATASET_RELEASE, TASK_ID
from caip_maintenance.data.ahs_split import SPLIT_ID
from caip_maintenance.data.common import sha256_file, write_csv
from caip_maintenance.features.ahs_preprocessing import (
    HIGH_COST_THRESHOLD_VERSION,
    PREPROCESSOR_ID,
)


EXPERIMENT_ID = "ahs-baselines-models-v1"
LOG1P_EXPERIMENT_ID = "ahs-baselines-models-log1p-v1"
FEATURE_ENGINEERING_EXPERIMENT_ID = "ahs-feature-engineering-v1"
EXPERIMENT_CONFIGS = {
    EXPERIMENT_ID: "ahs_baselines_models_v1.toml",
    LOG1P_EXPERIMENT_ID: "ahs_baselines_models_log1p_v1.toml",
    FEATURE_ENGINEERING_EXPERIMENT_ID: "ahs_feature_engineering_v1.toml",
}
SUPPORTED_EXPERIMENT_IDS = frozenset(EXPERIMENT_CONFIGS)
TARGET_TRANSFORM_NONE = "none"
TARGET_TRANSFORM_LOG1P = "log1p"
SYSTEM_NAMES = [
    "training_median",
    "type_median",
    "prior_cost",
    "linear_regression",
    "random_forest",
    "gradient_boosting",
]
BASELINE_NAMES = SYSTEM_NAMES[:3]
MODEL_NAMES = SYSTEM_NAMES[3:]
PREDICTION_FIELDS = [
    "snapshot_id",
    "split_name",
    "label_wave_year",
    "include_in_primary_metrics",
    "include_in_pre_2023_cap_sensitivity",
    "target_amount_usd",
    "is_high_cost",
    *[f"prediction_{name}_usd" for name in SYSTEM_NAMES],
]


def build_ahs_experiment(
    project_root: Path,
    release: str = DATASET_RELEASE,
    split_id: str = SPLIT_ID,
    preprocessor_id: str = PREPROCESSOR_ID,
    experiment_id: str = EXPERIMENT_ID,
) -> Path:
    """Fit baselines and fixed models on training rows, then evaluate held-out rows."""
    np, joblib, estimators, versions = _modeling_dependencies()
    spec, config_path = _load_spec(project_root, experiment_id)
    _validate_spec(spec, release, split_id, preprocessor_id, experiment_id)
    inputs = _load_inputs(project_root, release, split_id, preprocessor_id, np)
    training_mask = inputs["split_name"] == spec["fit_split"]
    if int(training_mask.sum()) == 0:
        raise ValueError("AHS experiment has no training rows")

    target_transform = _target_transform(spec)
    baselines, baseline_predictions = _fit_baselines(inputs, training_mask, np)
    models, model_predictions = _fit_models(
        spec,
        inputs["features"],
        inputs["target"],
        training_mask,
        estimators,
        target_transform,
        np,
    )
    predictions = baseline_predictions | model_predictions
    metrics = _evaluate(spec, inputs, predictions, np)

    output_dir = _experiment_dir(
        project_root, release, split_id, preprocessor_id, experiment_id
    )
    if output_dir.exists():
        raise FileExistsError(
            f"experiment output already exists: {output_dir}; artifacts are immutable"
        )
    (output_dir / "models").mkdir(parents=True)

    baseline_path = output_dir / "baseline_parameters.json"
    baseline_path.write_text(
        json.dumps(baselines, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    model_files: dict[str, str] = {}
    for name in MODEL_NAMES:
        path = output_dir / "models" / f"{name}.joblib"
        joblib.dump(models[name], path, compress=3)
        model_files[name] = str(path.relative_to(output_dir))

    prediction_path = output_dir / "predictions.csv"
    write_csv(
        prediction_path,
        PREDICTION_FIELDS,
        _prediction_rows(inputs, predictions),
    )
    metrics_path = output_dir / "metrics.json"
    metrics_path.write_text(
        json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    fit_evidence = _fit_evidence(inputs, training_mask, np)
    model_contracts = {
        name: {
            "artifact": model_files[name],
            "estimator": spec["models"][name]["estimator"],
            "parameters": _json_parameters(models[name].get_params(deep=False)),
            "fit_split": spec["fit_split"],
            "fit_rows": int(training_mask.sum()),
            "target_transform": target_transform,
            "prediction_inverse_transform": _prediction_inverse_transform(
                target_transform
            ),
            "fit_snapshot_ids_sha256": fit_evidence["fit_snapshot_ids_sha256"],
            "training_feature_rows_sha256": fit_evidence[
                "training_feature_rows_sha256"
            ],
            "training_targets_sha256": fit_evidence["training_targets_sha256"],
        }
        for name in MODEL_NAMES
    }
    artifact_hashes = {
        "baseline_parameters.json": sha256_file(baseline_path),
        "predictions.csv": sha256_file(prediction_path),
        "metrics.json": sha256_file(metrics_path),
        **{
            relative_path: sha256_file(output_dir / relative_path)
            for relative_path in model_files.values()
        },
    }
    manifest = {
        "experiment_id": experiment_id,
        "experiment_contract_version": spec["experiment_contract_version"],
        "dataset_release": release,
        "split_id": split_id,
        "preprocessor_id": preprocessor_id,
        "task_id": TASK_ID,
        "status": "completed_fixed_comparison_local_analysis_only",
        "built_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "distribution": spec["distribution"],
        "execution_order": SYSTEM_NAMES,
        "fit_contract": {
            "fit_split": spec["fit_split"],
            "fit_rows": int(training_mask.sum()),
            "held_out_labels_used_for_fit": False,
            "hyperparameter_search": spec["hyperparameter_search"],
            "model_selection": spec["model_selection"],
            "all_models_use_identical_frozen_features": True,
            "prediction_clipping": spec["prediction_clipping"],
            "sample_weighting": spec["sample_weighting"],
            "target_transform": target_transform,
            "prediction_inverse_transform": _prediction_inverse_transform(
                target_transform
            ),
            "baselines_fit_on": "original_usd_labels",
            "metrics_evaluated_in": "original_usd",
            **fit_evidence,
        },
        "baseline_contracts": baselines,
        "model_contracts": model_contracts,
        "evaluation_contract": {
            "splits": spec["evaluation_splits"],
            "views": spec["evaluation_views"],
            "primary_metric": spec["metric_primary"],
            "metrics": spec["metrics"],
            "target_currency": spec["target_currency"],
            "metrics_evaluated_in": "original_usd",
            "high_cost_threshold_version": spec["high_cost_threshold_version"],
            "high_cost_threshold_usd": float(spec["high_cost_threshold_usd"]),
            "held_out_labels_used_for_metrics_only": True,
        },
        "counts": {
            "rows": len(inputs["snapshot_id"]),
            "features": int(inputs["features"].shape[1]),
            "rows_by_split": {
                name: int((inputs["split_name"] == name).sum())
                for name in ("training", "validation", "test")
            },
        },
        "source_sha256": inputs["source_sha256"],
        "config_sha256": sha256_file(config_path),
        "software_versions": versions,
        "output_sha256": artifact_hashes,
        "claim_boundary": {
            "public_proxy_task_only": True,
            "is_wapda_data": False,
            "is_validated_wasc_or_wapda_forecast": False,
            "rhfs_labels_merged": False,
            "nyc_hpd_opened": False,
        },
    }
    (output_dir / "experiment_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return output_dir


def audit_ahs_experiment(project_root: Path, output_dir: Path) -> dict[str, Any]:
    """Audit immutable inputs, training-only state, metrics, and model reload predictions."""
    np, joblib, _, _ = _modeling_dependencies()
    manifest_path = output_dir / "experiment_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    experiment_id = manifest["experiment_id"]
    spec, config_path = _load_spec(project_root, experiment_id)
    _validate_spec(
        spec,
        manifest["dataset_release"],
        manifest["split_id"],
        manifest["preprocessor_id"],
        experiment_id,
    )
    inputs = _load_inputs(
        project_root,
        manifest["dataset_release"],
        manifest["split_id"],
        manifest["preprocessor_id"],
        np,
    )
    checks: list[dict[str, Any]] = []
    _check(
        checks,
        "source_preprocessing_artifacts_unchanged",
        manifest.get("source_sha256") == inputs["source_sha256"],
        None,
    )
    _check(
        checks,
        "experiment_config_unchanged",
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
        if not (output_dir / name).is_file()
        or sha256_file(output_dir / name) != expected
    }
    _check(checks, "output_checksums", not output_drift, output_drift)

    training_mask = inputs["split_name"] == spec["fit_split"]
    expected_fit = _fit_evidence(inputs, training_mask, np)
    recorded_fit = manifest.get("fit_contract", {})
    recorded_model_contracts = manifest.get("model_contracts", {})
    model_fit_contracts_match = all(
        name in recorded_model_contracts
        and recorded_model_contracts[name].get("fit_split") == "training"
        and recorded_model_contracts[name].get("fit_rows") == int(training_mask.sum())
        and recorded_model_contracts[name].get("estimator")
        == spec["models"][name]["estimator"]
        and all(
            recorded_model_contracts[name].get(key) == value
            for key, value in expected_fit.items()
        )
        for name in MODEL_NAMES
    )
    _check(
        checks,
        "training_ids_and_values_are_the_only_fit_inputs",
        all(recorded_fit.get(key) == value for key, value in expected_fit.items())
        and recorded_fit.get("fit_rows") == int(training_mask.sum())
        and recorded_fit.get("fit_split") == "training"
        and recorded_fit.get("held_out_labels_used_for_fit") is False
        and model_fit_contracts_match,
        {
            "fit_rows": recorded_fit.get("fit_rows"),
            "fit_snapshot_ids_sha256": recorded_fit.get("fit_snapshot_ids_sha256"),
            "all_model_fit_contracts_match": model_fit_contracts_match,
        },
    )
    expected_baselines, expected_baseline_predictions = _fit_baselines(
        inputs, training_mask, np
    )
    stored_baselines = json.loads(
        (output_dir / "baseline_parameters.json").read_text(encoding="utf-8")
    )
    _check(
        checks,
        "baselines_recompute_from_training_only",
        stored_baselines == expected_baselines
        and manifest.get("baseline_contracts") == expected_baselines,
        None,
    )

    stored_predictions, prediction_failures = _read_predictions(
        output_dir / "predictions.csv", inputs, np
    )
    _check(
        checks,
        "prediction_rows_match_frozen_rows_without_clipping",
        prediction_failures == 0,
        {"rows": len(inputs["snapshot_id"]), "mismatches": prediction_failures},
    )
    baseline_mismatches = sum(
        not np.array_equal(
            stored_predictions[name], expected_baseline_predictions[name]
        )
        for name in BASELINE_NAMES
    )
    _check(
        checks,
        "baseline_predictions_reproduce",
        baseline_mismatches == 0,
        {"mismatched_systems": baseline_mismatches},
    )

    reload_mismatches = 0
    model_predictions: dict[str, Any] = {}
    checksums_passed = not output_drift
    target_transform = _target_transform(spec)
    if checksums_passed:
        for name in MODEL_NAMES:
            contract = manifest["model_contracts"][name]
            model_path = output_dir / contract["artifact"]
            model = joblib.load(model_path)
            current = _predict_in_original_usd(
                model, inputs["features"], target_transform, np
            )
            model_predictions[name] = current
            if not np.array_equal(current, stored_predictions[name]):
                reload_mismatches += 1
    else:
        reload_mismatches = len(MODEL_NAMES)
    _check(
        checks,
        "saved_models_reload_with_identical_predictions",
        reload_mismatches == 0,
        {
            "mismatched_models": reload_mismatches,
            "deserialization_performed_after_checksum_verification": checksums_passed,
        },
    )

    all_predictions = expected_baseline_predictions | model_predictions
    expected_metrics = (
        _evaluate(spec, inputs, all_predictions, np)
        if len(model_predictions) == len(MODEL_NAMES)
        else None
    )
    stored_metrics = json.loads((output_dir / "metrics.json").read_text(encoding="utf-8"))
    _check(
        checks,
        "metrics_recompute_from_held_out_predictions",
        expected_metrics == stored_metrics,
        None,
    )
    _check(
        checks,
        "same_rows_threshold_and_views_for_every_system",
        stored_metrics.get("system_order") == SYSTEM_NAMES
        and stored_metrics.get("evaluation_splits") == spec["evaluation_splits"]
        and stored_metrics.get("evaluation_views") == spec["evaluation_views"]
        and stored_metrics.get("high_cost_threshold_usd")
        == float(spec["high_cost_threshold_usd"]),
        None,
    )
    _check(
        checks,
        "public_proxy_claim_boundary_preserved",
        manifest.get("claim_boundary")
        == {
            "public_proxy_task_only": True,
            "is_wapda_data": False,
            "is_validated_wasc_or_wapda_forecast": False,
            "rhfs_labels_merged": False,
            "nyc_hpd_opened": False,
        },
        manifest.get("claim_boundary"),
    )

    failed = [check["check_id"] for check in checks if check["status"] == "failed"]
    return {
        "experiment_id": experiment_id,
        "dataset_release": manifest["dataset_release"],
        "task_id": manifest["task_id"],
        "status": "passed" if not failed else "failed",
        "summary": {"passed": len(checks) - len(failed), "failed": len(failed)},
        "failed_checks": failed,
        "checks": checks,
    }


def calculate_metrics(actual: Any, predicted: Any, threshold: float) -> dict[str, Any]:
    """Calculate unweighted regression and threshold-retrieval metrics."""
    np, _, _, _ = _modeling_dependencies()
    actual_array = np.asarray(actual, dtype=np.float64)
    predicted_array = np.asarray(predicted, dtype=np.float64)
    if actual_array.ndim != 1 or predicted_array.shape != actual_array.shape:
        raise ValueError("metric arrays must be one-dimensional and have equal shapes")
    if len(actual_array) == 0:
        raise ValueError("cannot calculate metrics for an empty view")
    if not np.isfinite(actual_array).all() or not np.isfinite(predicted_array).all():
        raise ValueError("metric inputs must be finite")
    error = predicted_array - actual_array
    actual_high = actual_array >= threshold
    predicted_high = predicted_array >= threshold
    true_positive = int((actual_high & predicted_high).sum())
    false_positive = int((~actual_high & predicted_high).sum())
    true_negative = int((~actual_high & ~predicted_high).sum())
    false_negative = int((actual_high & ~predicted_high).sum())
    precision = _safe_ratio(true_positive, true_positive + false_positive)
    recall = _safe_ratio(true_positive, true_positive + false_negative)
    f1 = (
        None
        if precision is None or recall is None or precision + recall == 0
        else 2 * precision * recall / (precision + recall)
    )
    return {
        "count": int(len(actual_array)),
        "mae_usd": float(np.mean(np.abs(error))),
        "rmse_usd": float(np.sqrt(np.mean(error**2))),
        "actual_high_cost_count": int(actual_high.sum()),
        "predicted_high_cost_count": int(predicted_high.sum()),
        "high_cost_true_positive": true_positive,
        "high_cost_false_positive": false_positive,
        "high_cost_true_negative": true_negative,
        "high_cost_false_negative": false_negative,
        "high_cost_precision": precision,
        "high_cost_recall": recall,
        "high_cost_f1": f1,
    }


def _modeling_dependencies() -> tuple[Any, Any, dict[str, Any], dict[str, str]]:
    try:
        import joblib
        import numpy as np
        import sklearn
        from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
        from sklearn.linear_model import LinearRegression
    except ImportError as exc:
        raise RuntimeError(
            "AHS modeling requires the declared requirements-modeling.txt dependencies"
        ) from exc
    return (
        np,
        joblib,
        {
            "linear_regression": LinearRegression,
            "random_forest": RandomForestRegressor,
            "gradient_boosting": HistGradientBoostingRegressor,
        },
        {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scikit_learn": sklearn.__version__,
            "joblib": joblib.__version__,
        },
    )


def _load_spec(project_root: Path, experiment_id: str) -> tuple[dict[str, Any], Path]:
    config_name = EXPERIMENT_CONFIGS.get(experiment_id)
    if config_name is None:
        supported = ", ".join(sorted(SUPPORTED_EXPERIMENT_IDS))
        raise ValueError(f"supported AHS experiments are: {supported}")
    path = project_root / "configs" / "experiments" / config_name
    with path.open("rb") as handle:
        return tomllib.load(handle), path


def _target_transform(spec: dict[str, Any]) -> str:
    transform = spec.get("target_transform", TARGET_TRANSFORM_NONE)
    if transform not in {TARGET_TRANSFORM_NONE, TARGET_TRANSFORM_LOG1P}:
        raise ValueError(f"unsupported AHS target transform: {transform!r}")
    return transform


def _prediction_inverse_transform(target_transform: str) -> str:
    if target_transform == TARGET_TRANSFORM_LOG1P:
        return "expm1"
    return "none"


def _predict_in_original_usd(
    model: Any, features: Any, target_transform: str, np: Any
) -> Any:
    current = model.predict(features)
    if target_transform == TARGET_TRANSFORM_LOG1P:
        current = np.expm1(current)
    return current


def _validate_spec(
    spec: dict[str, Any],
    release: str,
    split_id: str,
    preprocessor_id: str,
    experiment_id: str,
) -> None:
    expected = {
        "experiment_id": experiment_id,
        "dataset_release": release,
        "split_id": split_id,
        "preprocessor_id": preprocessor_id,
        "task_id": TASK_ID,
    }
    if any(spec.get(key) != value for key, value in expected.items()):
        raise ValueError("AHS experiment specification does not match the request")
    if experiment_id not in SUPPORTED_EXPERIMENT_IDS:
        raise ValueError(f"unsupported AHS experiment: {experiment_id!r}")
    target_transform = _target_transform(spec)
    if experiment_id == EXPERIMENT_ID and target_transform != TARGET_TRANSFORM_NONE:
        raise ValueError("ahs-baselines-models-v1 must keep the raw USD target")
    if experiment_id == LOG1P_EXPERIMENT_ID and target_transform != TARGET_TRANSFORM_LOG1P:
        raise ValueError("ahs-baselines-models-log1p-v1 must use the log1p target")
    if (
        experiment_id == FEATURE_ENGINEERING_EXPERIMENT_ID
        and preprocessor_id != "ahs-feature-engineering-v1"
    ):
        raise ValueError(
            "ahs-feature-engineering-v1 requires preprocessor ahs-feature-engineering-v1"
        )
    if target_transform == TARGET_TRANSFORM_LOG1P:
        if spec.get("metrics_evaluated_in") != "original_usd":
            raise ValueError("log1p experiment metrics must be evaluated in original USD")
        if spec.get("prediction_inverse_transform") != "expm1":
            raise ValueError("log1p experiment must invert predictions with expm1")
        if spec.get("comparison_baseline_experiment_id") != EXPERIMENT_ID:
            raise ValueError("log1p experiment must compare against ahs-baselines-models-v1")
    if spec.get("fit_split") != "training":
        raise ValueError("AHS models must fit on training rows only")
    if spec.get("evaluation_splits") != ["validation", "test"]:
        raise ValueError("AHS evaluation must use the frozen validation and test splits")
    if spec.get("evaluation_views") != ["primary", "pre_2023_cap_sensitivity"]:
        raise ValueError("AHS evaluation must report both frozen cap views")
    if (
        spec.get("target_currency") != "USD"
        or spec.get("high_cost_threshold_version") != HIGH_COST_THRESHOLD_VERSION
        or float(spec.get("high_cost_threshold_usd", -1)) != 1428.0
    ):
        raise ValueError("AHS experiment must use the frozen USD 1,428 threshold")
    if spec.get("metric_primary") != "mae":
        raise ValueError("AHS experiment primary metric must be MAE")
    if spec.get("hyperparameter_search") is not False or spec.get("model_selection") is not False:
        raise ValueError("this fixed comparison cannot tune or select on held-out labels")
    if spec.get("prediction_clipping") != "none":
        raise ValueError("AHS experiment predictions must not be silently clipped")
    if spec.get("sample_weighting") != "none":
        raise ValueError("unsupported AHS experiment weighting")
    if spec.get("distribution") != "local-analysis-only":
        raise ValueError("AHS experiment remains local-analysis-only")
    if list(spec.get("baselines", {})) != BASELINE_NAMES:
        raise ValueError("AHS baseline order or set changed")
    if list(spec.get("models", {})) != MODEL_NAMES:
        raise ValueError("AHS model order or set changed")


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


def _load_inputs(
    project_root: Path,
    release: str,
    split_id: str,
    preprocessor_id: str,
    np: Any,
) -> dict[str, Any]:
    directory = (
        project_root
        / "data"
        / "processed"
        / "preprocessing"
        / release
        / split_id
        / preprocessor_id
    )
    manifest_path = directory / "preprocessing_manifest.json"
    preprocessor_path = directory / "preprocessor.json"
    feature_path = directory / "feature_matrix.csv"
    target_path = directory / "target_metadata.csv"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    preprocessor = json.loads(preprocessor_path.read_text(encoding="utf-8"))
    if (
        manifest.get("dataset_release") != release
        or manifest.get("split_id") != split_id
        or manifest.get("preprocessor_id") != preprocessor_id
        or manifest.get("task_id") != TASK_ID
        or manifest.get("fit_split") != "training"
        or manifest.get("distribution") != "local-analysis-only"
    ):
        raise ValueError("experiment input is not the frozen AHS preprocessing artifact")
    if preprocessor.get("model_fitted") is not False:
        raise ValueError("AHS preprocessing source unexpectedly contains a model")
    if preprocessor.get("target_policy") != {
        "cap_sensitivity_metadata_preserved": True,
        "clipping": "prohibited",
        "imputation": "prohibited",
    }:
        raise ValueError("AHS preprocessing target policy changed")
    high_cost = preprocessor.get("high_cost_policy", {})
    if (
        high_cost.get("threshold_version") != HIGH_COST_THRESHOLD_VERSION
        or float(high_cost.get("threshold_amount_local_nominal", -1)) != 1428.0
        or high_cost.get("fit_split") != "training"
    ):
        raise ValueError("AHS preprocessing high-cost threshold is not frozen at USD 1,428")
    expected_outputs = manifest.get("output_sha256", {})
    for name, path in {
        "preprocessor.json": preprocessor_path,
        "feature_matrix.csv": feature_path,
        "target_metadata.csv": target_path,
    }.items():
        if sha256_file(path) != expected_outputs.get(name):
            raise ValueError(f"AHS preprocessing checksum drift: {name}")

    feature_columns = preprocessor["feature_matrix_columns"][1:]
    row_count = int(manifest["counts"]["feature_rows"])
    features = np.empty((row_count, len(feature_columns)), dtype=np.float64)
    snapshot_ids: list[str] = []
    with feature_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        if header != preprocessor["feature_matrix_columns"]:
            raise ValueError("AHS feature matrix schema changed")
        for index, row in enumerate(reader):
            if index >= row_count or len(row) != len(header):
                raise ValueError("AHS feature matrix row count or width changed")
            snapshot_ids.append(row[0])
            try:
                features[index, :] = row[1:]
            except ValueError as exc:
                raise ValueError("AHS feature matrix contains a non-numeric value") from exc
    if len(snapshot_ids) != row_count or len(set(snapshot_ids)) != row_count:
        raise ValueError("AHS feature matrix keys or row count changed")
    if not np.isfinite(features).all():
        raise ValueError("AHS feature matrix contains a non-finite value")

    target = np.empty(row_count, dtype=np.float64)
    split_name = np.empty(row_count, dtype=object)
    label_wave_year = np.empty(row_count, dtype=np.int64)
    primary = np.empty(row_count, dtype=bool)
    sensitivity = np.empty(row_count, dtype=bool)
    is_high_cost = np.empty(row_count, dtype=bool)
    with target_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = 0
        for index, row in enumerate(reader):
            if index >= row_count or row["snapshot_id"] != snapshot_ids[index]:
                raise ValueError("AHS target metadata is not aligned to the feature matrix")
            if row["task_id"] != TASK_ID or row["target_currency"] != "USD":
                raise ValueError("AHS target task or currency changed")
            if row["target_was_imputed"] != "false" or row["target_was_clipped"] != "false":
                raise ValueError("AHS target was imputed or clipped")
            target[index] = _finite_float(row["target_amount_local_nominal"], "target")
            split_name[index] = row["split_name"]
            label_wave_year[index] = int(row["label_wave_year"])
            primary[index] = _boolean(row["include_in_primary_metrics"])
            sensitivity[index] = _boolean(
                row["include_in_pre_2023_cap_sensitivity"]
            )
            is_high_cost[index] = _boolean(row["is_high_cost"])
            rows += 1
    if rows != row_count or set(split_name) != {"training", "validation", "test"}:
        raise ValueError("AHS target metadata rows or split values changed")
    if (target < 0).any() or not np.isfinite(target).all():
        raise ValueError("AHS target contains an invalid value")
    if not primary.all() or not np.array_equal(sensitivity, label_wave_year < 2023):
        raise ValueError("AHS primary or cap-sensitivity flags changed")
    if not np.array_equal(is_high_cost, target >= 1428.0):
        raise ValueError("AHS high-cost flags differ from the frozen threshold")

    return {
        "snapshot_id": snapshot_ids,
        "features": features,
        "feature_columns": feature_columns,
        "target": target,
        "split_name": split_name,
        "label_wave_year": label_wave_year,
        "include_in_primary_metrics": primary,
        "include_in_pre_2023_cap_sensitivity": sensitivity,
        "is_high_cost": is_high_cost,
        "preprocessor": preprocessor,
        "source_sha256": {
            "preprocessing_manifest.json": sha256_file(manifest_path),
            "preprocessor.json": sha256_file(preprocessor_path),
            "feature_matrix.csv": sha256_file(feature_path),
            "target_metadata.csv": sha256_file(target_path),
        },
    }


def _fit_baselines(
    inputs: dict[str, Any], training_mask: Any, np: Any
) -> tuple[dict[str, Any], dict[str, Any]]:
    target = inputs["target"]
    training_median = float(np.median(target[training_mask]))
    predictions: dict[str, Any] = {
        "training_median": np.full(len(target), training_median, dtype=np.float64)
    }

    type_values = _decoded_category(inputs, "building_type_code", np)
    type_parameter = _feature_parameter(inputs["preprocessor"], "building_type_code")
    training_categories = set(type_parameter["encoder"]["training_categories"])
    type_medians = {
        str(category): float(np.median(target[training_mask & (type_values == category)]))
        for category in sorted(set(type_values[training_mask]) & training_categories)
    }
    predictions["type_median"] = np.asarray(
        [type_medians.get(str(value), training_median) for value in type_values],
        dtype=np.float64,
    )

    prior_parameter = _feature_parameter(inputs["preprocessor"], "prior_routine_maintenance_usd")
    value_column = prior_parameter["value_output_column"]
    missing_column = prior_parameter["missing_indicator_column"]
    column_index = {name: index for index, name in enumerate(inputs["feature_columns"])}
    standardized = inputs["features"][:, column_index[value_column]]
    missing = inputs["features"][:, column_index[missing_column]] == 1.0
    prior_raw = (
        standardized * float(prior_parameter["scaler"]["scale"])
        + float(prior_parameter["scaler"]["mean_after_imputation"])
    )
    prior_predictions = prior_raw.copy()
    prior_predictions[missing] = training_median
    predictions["prior_cost"] = prior_predictions

    fit_ids_sha256 = _snapshot_digest(
        snapshot_id
        for snapshot_id, selected in zip(inputs["snapshot_id"], training_mask)
        if selected
    )
    baselines = {
        "training_median": {
            "rule": "constant_median_of_training_labels",
            "fit_split": "training",
            "fit_rows": int(training_mask.sum()),
            "fit_snapshot_ids_sha256": fit_ids_sha256,
            "prediction_usd": training_median,
        },
        "type_median": {
            "rule": "training_label_median_by_training_fitted_building_type",
            "group_feature": "building_type_code",
            "fit_split": "training",
            "fit_rows": int(training_mask.sum()),
            "fit_snapshot_ids_sha256": fit_ids_sha256,
            "group_median_usd": type_medians,
            "fallback": "global_training_median_for_missing_or_unseen_type",
            "fallback_prediction_usd": training_median,
        },
        "prior_cost": {
            "rule": "unscaled_earlier_wave_prior_routine_cost_when_nonmissing",
            "feature": "prior_routine_maintenance_usd",
            "fit_split": "training",
            "fit_rows": int(training_mask.sum()),
            "fit_snapshot_ids_sha256": fit_ids_sha256,
            "fallback": "global_training_median_when_prior_cost_missing",
            "fallback_prediction_usd": training_median,
            "missing_rows_all_splits": int(missing.sum()),
            "prediction_clipping": "none",
        },
    }
    return baselines, predictions


def _fit_models(
    spec: dict[str, Any],
    features: Any,
    target: Any,
    training_mask: Any,
    estimators: dict[str, Any],
    target_transform: str,
    np: Any,
) -> tuple[dict[str, Any], dict[str, Any]]:
    seed = int(spec["random_seed"])
    model_parameters = {
        "linear_regression": {
            "fit_intercept": bool(spec["models"]["linear_regression"]["fit_intercept"])
        },
        "random_forest": {
            "n_estimators": int(spec["models"]["random_forest"]["n_estimators"]),
            "max_depth": int(spec["models"]["random_forest"]["max_depth"]),
            "min_samples_leaf": int(
                spec["models"]["random_forest"]["min_samples_leaf"]
            ),
            "max_features": float(spec["models"]["random_forest"]["max_features"]),
            "n_jobs": int(spec["models"]["random_forest"]["n_jobs"]),
            "random_state": seed,
        },
        "gradient_boosting": {
            "learning_rate": float(
                spec["models"]["gradient_boosting"]["learning_rate"]
            ),
            "max_iter": int(spec["models"]["gradient_boosting"]["max_iter"]),
            "max_leaf_nodes": int(
                spec["models"]["gradient_boosting"]["max_leaf_nodes"]
            ),
            "min_samples_leaf": int(
                spec["models"]["gradient_boosting"]["min_samples_leaf"]
            ),
            "l2_regularization": float(
                spec["models"]["gradient_boosting"]["l2_regularization"]
            ),
            "random_state": seed,
        },
    }
    training_target = target[training_mask]
    if target_transform == TARGET_TRANSFORM_LOG1P:
        training_target = np.log1p(training_target)
    models: dict[str, Any] = {}
    predictions: dict[str, Any] = {}
    for name in MODEL_NAMES:
        model = estimators[name](**model_parameters[name])
        model.fit(features[training_mask], training_target)
        current = _predict_in_original_usd(model, features, target_transform, np)
        if not math.isfinite(float(current.min())) or not math.isfinite(float(current.max())):
            raise ValueError(f"{name} produced non-finite predictions")
        models[name] = model
        predictions[name] = current
    return models, predictions


def _evaluate(
    spec: dict[str, Any], inputs: dict[str, Any], predictions: dict[str, Any], np: Any
) -> dict[str, Any]:
    threshold = float(spec["high_cost_threshold_usd"])
    view_masks = {
        "primary": inputs["include_in_primary_metrics"],
        "pre_2023_cap_sensitivity": inputs[
            "include_in_pre_2023_cap_sensitivity"
        ],
    }
    results: dict[str, Any] = {}
    for system in SYSTEM_NAMES:
        results[system] = {}
        for view in spec["evaluation_views"]:
            results[system][view] = {}
            for split in spec["evaluation_splits"]:
                mask = view_masks[view] & (inputs["split_name"] == split)
                results[system][view][split] = calculate_metrics(
                    inputs["target"][mask], predictions[system][mask], threshold
                )
    payload = {
        "task_id": TASK_ID,
        "target_currency": "USD",
        "primary_metric": "mae",
        "high_cost_threshold_version": HIGH_COST_THRESHOLD_VERSION,
        "high_cost_threshold_usd": threshold,
        "prediction_clipping": "none",
        "sample_weighting": "none",
        "evaluation_splits": spec["evaluation_splits"],
        "evaluation_views": spec["evaluation_views"],
        "system_order": SYSTEM_NAMES,
        "results": results,
        "interpretation": "AHS public routine-maintenance proxy only; not a WASC or WAPDA forecast",
    }
    if _target_transform(spec) == TARGET_TRANSFORM_LOG1P:
        payload = {
            "task_id": payload["task_id"],
            "target_currency": payload["target_currency"],
            "metrics_evaluated_in": "original_usd",
            "target_transform": TARGET_TRANSFORM_LOG1P,
            "primary_metric": payload["primary_metric"],
            "high_cost_threshold_version": payload["high_cost_threshold_version"],
            "high_cost_threshold_usd": payload["high_cost_threshold_usd"],
            "prediction_clipping": payload["prediction_clipping"],
            "sample_weighting": payload["sample_weighting"],
            "evaluation_splits": payload["evaluation_splits"],
            "evaluation_views": payload["evaluation_views"],
            "system_order": payload["system_order"],
            "results": payload["results"],
            "interpretation": payload["interpretation"],
        }
    return payload


def _prediction_rows(inputs: dict[str, Any], predictions: dict[str, Any]) -> Any:
    for index, snapshot_id in enumerate(inputs["snapshot_id"]):
        yield {
            "snapshot_id": snapshot_id,
            "split_name": inputs["split_name"][index],
            "label_wave_year": int(inputs["label_wave_year"][index]),
            "include_in_primary_metrics": bool(
                inputs["include_in_primary_metrics"][index]
            ),
            "include_in_pre_2023_cap_sensitivity": bool(
                inputs["include_in_pre_2023_cap_sensitivity"][index]
            ),
            "target_amount_usd": _float_text(inputs["target"][index]),
            "is_high_cost": bool(inputs["is_high_cost"][index]),
            **{
                f"prediction_{name}_usd": _float_text(predictions[name][index])
                for name in SYSTEM_NAMES
            },
        }


def _read_predictions(
    path: Path, inputs: dict[str, Any], np: Any
) -> tuple[dict[str, Any], int]:
    predictions = {
        name: np.empty(len(inputs["snapshot_id"]), dtype=np.float64)
        for name in SYSTEM_NAMES
    }
    failures = 0
    if not path.is_file():
        return predictions, 1
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != PREDICTION_FIELDS:
            failures += 1
        rows = 0
        for index, row in enumerate(reader):
            if index >= len(inputs["snapshot_id"]):
                failures += 1
                break
            expected_metadata = {
                "snapshot_id": inputs["snapshot_id"][index],
                "split_name": str(inputs["split_name"][index]),
                "label_wave_year": str(int(inputs["label_wave_year"][index])),
                "include_in_primary_metrics": _bool_text(
                    inputs["include_in_primary_metrics"][index]
                ),
                "include_in_pre_2023_cap_sensitivity": _bool_text(
                    inputs["include_in_pre_2023_cap_sensitivity"][index]
                ),
                "target_amount_usd": _float_text(inputs["target"][index]),
                "is_high_cost": _bool_text(inputs["is_high_cost"][index]),
            }
            if any(row.get(key) != value for key, value in expected_metadata.items()):
                failures += 1
            for name in SYSTEM_NAMES:
                predictions[name][index] = _finite_float(
                    row[f"prediction_{name}_usd"], f"prediction_{name}_usd"
                )
            rows += 1
    if rows != len(inputs["snapshot_id"]):
        failures += 1
    return predictions, failures


def _fit_evidence(inputs: dict[str, Any], training_mask: Any, np: Any) -> dict[str, str]:
    selected_ids = [
        snapshot_id
        for snapshot_id, selected in zip(inputs["snapshot_id"], training_mask)
        if selected
    ]
    feature_digest = sha256()
    target_digest = sha256()
    for index in np.flatnonzero(training_mask):
        snapshot_id = inputs["snapshot_id"][int(index)]
        feature_digest.update(f"{snapshot_id}|".encode("utf-8"))
        feature_digest.update(inputs["features"][index].tobytes(order="C"))
        target_digest.update(
            f"{snapshot_id}|{_float_text(inputs['target'][index])}\n".encode("utf-8")
        )
    return {
        "fit_snapshot_ids_sha256": _snapshot_digest(selected_ids),
        "training_feature_rows_sha256": feature_digest.hexdigest(),
        "training_targets_sha256": target_digest.hexdigest(),
    }


def _decoded_category(inputs: dict[str, Any], feature_name: str, np: Any) -> Any:
    parameter = _feature_parameter(inputs["preprocessor"], feature_name)
    encoder = parameter["encoder"]
    column_index = {name: index for index, name in enumerate(inputs["feature_columns"])}
    value_columns = encoder["category_output_columns"]
    reserved_columns = [
        encoder["reserved_missing_output_column"],
        encoder["reserved_unknown_output_column"],
    ]
    encoded = inputs["features"][:, [column_index[name] for name in value_columns + reserved_columns]]
    if not np.all(encoded.sum(axis=1) == 1.0):
        raise ValueError(f"{feature_name} one-hot values are not exactly one-of-k")
    selected = encoded.argmax(axis=1)
    categories = np.asarray(
        [
            *encoder["training_categories"],
            encoder["reserved_missing_token"],
            encoder["reserved_unknown_token"],
        ],
        dtype=object,
    )
    return categories[selected]


def _feature_parameter(preprocessor: dict[str, Any], feature_name: str) -> dict[str, Any]:
    matches = [
        item
        for item in preprocessor["feature_parameters"]
        if item["feature_name"] == feature_name
    ]
    if len(matches) != 1 or matches[0].get("value_feature_included") is not True:
        raise ValueError(f"required frozen feature is unavailable: {feature_name}")
    return matches[0]


def _snapshot_digest(snapshot_ids: Any) -> str:
    material = "".join(f"{snapshot_id}\n" for snapshot_id in sorted(snapshot_ids))
    return sha256(material.encode("utf-8")).hexdigest()


def _json_parameters(parameters: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in parameters.items()
        if isinstance(value, (str, int, float, bool)) or value is None
    }


def _safe_ratio(numerator: int, denominator: int) -> float | None:
    return None if denominator == 0 else numerator / denominator


def _finite_float(raw: Any, field: str) -> float:
    try:
        value = float(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid numeric value for {field}") from exc
    if not math.isfinite(value):
        raise ValueError(f"non-finite numeric value for {field}")
    return value


def _boolean(raw: str) -> bool:
    if raw not in {"true", "false"}:
        raise ValueError(f"invalid boolean value: {raw!r}")
    return raw == "true"


def _bool_text(value: Any) -> str:
    return "true" if bool(value) else "false"


def _float_text(value: Any) -> str:
    return format(float(value), ".17g")


def _check(checks: list[dict[str, Any]], check_id: str, passed: bool, evidence: Any) -> None:
    checks.append(
        {
            "check_id": check_id,
            "status": "passed" if passed else "failed",
            "evidence": evidence,
        }
    )
