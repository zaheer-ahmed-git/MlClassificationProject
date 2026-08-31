"""Train, evaluate, persist, and audit the frozen AHS XGBoost comparison."""

from __future__ import annotations

import csv
from datetime import datetime, timezone
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
    FEATURE_ENGINEERING_PREPROCESSOR_ID,
    HIGH_COST_THRESHOLD_VERSION,
    PREPROCESSOR_ID,
)
from caip_maintenance.modeling.ahs_experiment import (
    BASELINE_NAMES,
    calculate_metrics,
    _check,
    _experiment_dir,
    _fit_baselines,
    _fit_evidence,
    _float_text,
    _json_parameters,
    _load_inputs,
)


EXPERIMENT_ID = "ahs-xgboost-v1"
FEATURE_ENGINEERING_EXPERIMENT_ID = "ahs-xgboost-feature-engineering-v1"
EXPERIMENT_CONFIGS = {
    EXPERIMENT_ID: "ahs_xgboost_v1.toml",
    FEATURE_ENGINEERING_EXPERIMENT_ID: "ahs_xgboost_feature_engineering_v1.toml",
}
SUPPORTED_EXPERIMENT_IDS = frozenset(EXPERIMENT_CONFIGS)
MODEL_NAME = "xgboost"
SYSTEM_NAMES = [*BASELINE_NAMES, MODEL_NAME]
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


def build_ahs_xgboost_experiment(
    project_root: Path,
    release: str = DATASET_RELEASE,
    split_id: str = SPLIT_ID,
    preprocessor_id: str = PREPROCESSOR_ID,
    experiment_id: str = EXPERIMENT_ID,
) -> Path:
    """Fit frozen baselines and XGBoost on training rows, then evaluate held-out rows."""
    np, joblib, xgboost, versions = _xgboost_dependencies()
    spec, config_path = _load_xgboost_spec(project_root, experiment_id)
    _validate_xgboost_spec(spec, release, split_id, preprocessor_id, experiment_id)
    inputs = _load_inputs(project_root, release, split_id, preprocessor_id, np)
    training_mask = inputs["split_name"] == spec["fit_split"]
    if int(training_mask.sum()) == 0:
        raise ValueError("AHS XGBoost experiment has no training rows")

    baselines, baseline_predictions = _fit_baselines(inputs, training_mask, np)
    model, model_predictions = _fit_xgboost(
        spec, inputs["features"], inputs["target"], training_mask, xgboost, np
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
    model_path = output_dir / "models" / f"{MODEL_NAME}.joblib"
    joblib.dump(model, model_path, compress=3)

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
    model_contract = {
        "artifact": str(model_path.relative_to(output_dir)),
        "estimator": spec["models"][MODEL_NAME]["estimator"],
        "parameters": _json_parameters(model.get_params(deep=False)),
        "fit_split": spec["fit_split"],
        "fit_rows": int(training_mask.sum()),
        "target_transform": "none",
        "prediction_inverse_transform": "none",
        "fit_snapshot_ids_sha256": fit_evidence["fit_snapshot_ids_sha256"],
        "training_feature_rows_sha256": fit_evidence["training_feature_rows_sha256"],
        "training_targets_sha256": fit_evidence["training_targets_sha256"],
    }
    artifact_hashes = {
        "baseline_parameters.json": sha256_file(baseline_path),
        "predictions.csv": sha256_file(prediction_path),
        "metrics.json": sha256_file(metrics_path),
        model_contract["artifact"]: sha256_file(model_path),
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
            "target_transform": "none",
            "prediction_inverse_transform": "none",
            "baselines_fit_on": "original_usd_labels",
            "metrics_evaluated_in": "original_usd",
            **fit_evidence,
        },
        "baseline_contracts": baselines,
        "model_contracts": {MODEL_NAME: model_contract},
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


def audit_ahs_xgboost_experiment(
    project_root: Path, output_dir: Path
) -> dict[str, Any]:
    """Audit immutable inputs, training-only state, metrics, and model reload predictions."""
    np, joblib, _, _ = _xgboost_dependencies()
    manifest_path = output_dir / "experiment_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    experiment_id = manifest["experiment_id"]
    spec, config_path = _load_xgboost_spec(project_root, experiment_id)
    _validate_xgboost_spec(
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
    recorded_model_contract = manifest.get("model_contracts", {}).get(MODEL_NAME, {})
    model_fit_contract_matches = (
        recorded_model_contract.get("fit_split") == "training"
        and recorded_model_contract.get("fit_rows") == int(training_mask.sum())
        and recorded_model_contract.get("estimator")
        == spec["models"][MODEL_NAME]["estimator"]
        and all(
            recorded_model_contract.get(key) == value
            for key, value in expected_fit.items()
        )
    )
    _check(
        checks,
        "training_ids_and_values_are_the_only_fit_inputs",
        all(recorded_fit.get(key) == value for key, value in expected_fit.items())
        and recorded_fit.get("fit_rows") == int(training_mask.sum())
        and recorded_fit.get("fit_split") == "training"
        and recorded_fit.get("held_out_labels_used_for_fit") is False
        and model_fit_contract_matches,
        {
            "fit_rows": recorded_fit.get("fit_rows"),
            "fit_snapshot_ids_sha256": recorded_fit.get("fit_snapshot_ids_sha256"),
            "model_fit_contract_matches": model_fit_contract_matches,
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

    stored_predictions, prediction_failures = _read_xgboost_predictions(
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

    reload_mismatch = 1
    model_predictions: dict[str, Any] = {}
    checksums_passed = not output_drift
    if checksums_passed:
        contract = manifest["model_contracts"][MODEL_NAME]
        model = joblib.load(output_dir / contract["artifact"])
        current = model.predict(inputs["features"])
        model_predictions[MODEL_NAME] = current
        reload_mismatch = int(not np.array_equal(current, stored_predictions[MODEL_NAME]))
    _check(
        checks,
        "saved_model_reloads_with_identical_predictions",
        reload_mismatch == 0,
        {
            "mismatched_models": reload_mismatch,
            "deserialization_performed_after_checksum_verification": checksums_passed,
        },
    )

    all_predictions = expected_baseline_predictions | model_predictions
    expected_metrics = (
        _evaluate(spec, inputs, all_predictions, np)
        if MODEL_NAME in model_predictions
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


def _load_xgboost_spec(project_root: Path, experiment_id: str) -> tuple[dict[str, Any], Path]:
    config_name = EXPERIMENT_CONFIGS.get(experiment_id)
    if config_name is None:
        supported = ", ".join(sorted(SUPPORTED_EXPERIMENT_IDS))
        raise ValueError(f"supported AHS XGBoost experiments are: {supported}")
    path = project_root / "configs" / "experiments" / config_name
    with path.open("rb") as handle:
        return tomllib.load(handle), path


def _validate_xgboost_spec(
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
        raise ValueError("AHS XGBoost experiment specification does not match the request")
    if experiment_id not in SUPPORTED_EXPERIMENT_IDS:
        raise ValueError(f"unsupported AHS XGBoost experiment: {experiment_id!r}")
    if (
        experiment_id == FEATURE_ENGINEERING_EXPERIMENT_ID
        and preprocessor_id != FEATURE_ENGINEERING_PREPROCESSOR_ID
    ):
        raise ValueError(
            "ahs-xgboost-feature-engineering-v1 requires ahs-feature-engineering-v1"
        )
    if experiment_id == EXPERIMENT_ID and preprocessor_id != PREPROCESSOR_ID:
        raise ValueError("ahs-xgboost-v1 requires ahs-training-fold-v1")
    if spec.get("fit_split") != "training":
        raise ValueError("AHS XGBoost models must fit on training rows only")
    if spec.get("evaluation_splits") != ["validation", "test"]:
        raise ValueError("AHS XGBoost evaluation must use the frozen validation and test splits")
    if spec.get("evaluation_views") != ["primary", "pre_2023_cap_sensitivity"]:
        raise ValueError("AHS XGBoost evaluation must report both frozen cap views")
    if (
        spec.get("target_currency") != "USD"
        or spec.get("high_cost_threshold_version") != HIGH_COST_THRESHOLD_VERSION
        or float(spec.get("high_cost_threshold_usd", -1)) != 1428.0
    ):
        raise ValueError("AHS XGBoost experiment must use the frozen USD 1,428 threshold")
    if spec.get("metric_primary") != "mae":
        raise ValueError("AHS XGBoost experiment primary metric must be MAE")
    if spec.get("hyperparameter_search") is not False or spec.get("model_selection") is not False:
        raise ValueError("this fixed comparison cannot tune or select on held-out labels")
    if spec.get("prediction_clipping") != "none":
        raise ValueError("AHS XGBoost experiment predictions must not be silently clipped")
    if spec.get("sample_weighting") != "none":
        raise ValueError("unsupported AHS XGBoost experiment weighting")
    if spec.get("distribution") != "local-analysis-only":
        raise ValueError("AHS XGBoost experiment remains local-analysis-only")
    if list(spec.get("baselines", {})) != BASELINE_NAMES:
        raise ValueError("AHS XGBoost baseline order or set changed")
    if list(spec.get("models", {})) != [MODEL_NAME]:
        raise ValueError("AHS XGBoost experiment must contain only the xgboost model")
    if spec["models"][MODEL_NAME]["estimator"] != "xgboost.XGBRegressor":
        raise ValueError("AHS XGBoost experiment must use xgboost.XGBRegressor")


def _fit_xgboost(
    spec: dict[str, Any],
    features: Any,
    target: Any,
    training_mask: Any,
    xgboost: Any,
    np: Any,
) -> tuple[Any, dict[str, Any]]:
    model_spec = spec["models"][MODEL_NAME]
    parameters = {
        "objective": str(model_spec["objective"]),
        "n_estimators": int(model_spec["n_estimators"]),
        "learning_rate": float(model_spec["learning_rate"]),
        "max_depth": int(model_spec["max_depth"]),
        "min_child_weight": float(model_spec["min_child_weight"]),
        "subsample": float(model_spec["subsample"]),
        "colsample_bytree": float(model_spec["colsample_bytree"]),
        "reg_lambda": float(model_spec["reg_lambda"]),
        "reg_alpha": float(model_spec["reg_alpha"]),
        "tree_method": str(model_spec["tree_method"]),
        "n_jobs": int(model_spec["n_jobs"]),
        "random_state": int(spec["random_seed"]),
    }
    model = xgboost.XGBRegressor(**parameters)
    model.fit(features[training_mask], target[training_mask])
    predictions = model.predict(features)
    if not math.isfinite(float(predictions.min())) or not math.isfinite(float(predictions.max())):
        raise ValueError("xgboost produced non-finite predictions")
    return model, {MODEL_NAME: np.asarray(predictions, dtype=np.float64)}


def _evaluate(
    spec: dict[str, Any], inputs: dict[str, Any], predictions: dict[str, Any], np: Any
) -> dict[str, Any]:
    threshold = float(spec["high_cost_threshold_usd"])
    view_masks = {
        "primary": inputs["include_in_primary_metrics"],
        "pre_2023_cap_sensitivity": inputs["include_in_pre_2023_cap_sensitivity"],
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
    return {
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


def _read_xgboost_predictions(
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
            for name in SYSTEM_NAMES:
                predictions[name][index] = float(row[f"prediction_{name}_usd"])
            rows += 1
    if rows != len(inputs["snapshot_id"]):
        failures += 1
    return predictions, failures


def _xgboost_dependencies() -> tuple[Any, Any, Any, dict[str, str]]:
    try:
        import joblib
        import numpy as np
        import xgboost
    except ImportError as exc:
        raise RuntimeError(
            "AHS XGBoost modeling requires xgboost from requirements-modeling.txt"
        ) from exc
    return (
        np,
        joblib,
        xgboost,
        {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "joblib": joblib.__version__,
            "xgboost": xgboost.__version__,
        },
    )
