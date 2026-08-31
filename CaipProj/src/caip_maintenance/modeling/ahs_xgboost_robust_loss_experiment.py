"""Compare XGBoost objective functions on engineered AHS features."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
import platform
import tomllib
from typing import Any

from caip_maintenance.data.ahs import DATASET_RELEASE, TASK_ID
from caip_maintenance.data.ahs_split import SPLIT_ID
from caip_maintenance.data.common import sha256_file, write_csv
from caip_maintenance.features.ahs_preprocessing import FEATURE_ENGINEERING_PREPROCESSOR_ID
from caip_maintenance.modeling.ahs_experiment import (
    BASELINE_NAMES,
    calculate_metrics,
    _experiment_dir,
    _fit_baselines,
    _fit_evidence,
    _json_parameters,
    _load_inputs,
)


EXPERIMENT_ID = "ahs-xgboost-robust-loss-v1"
EXPERIMENT_CONFIG = "ahs_xgboost_robust_loss_v1.toml"
LOSS_MODEL_NAMES = (
    "xgboost_squared",
    "xgboost_absolute",
    "xgboost_pseudohuber",
)
SYSTEM_NAMES = [*BASELINE_NAMES, *LOSS_MODEL_NAMES]
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


def build_ahs_xgboost_robust_loss_experiment(
    project_root: Path,
    release: str = DATASET_RELEASE,
    split_id: str = SPLIT_ID,
    preprocessor_id: str = FEATURE_ENGINEERING_PREPROCESSOR_ID,
    experiment_id: str = EXPERIMENT_ID,
) -> Path:
    np, joblib, xgboost, versions = _robust_dependencies()
    spec, config_path = _load_spec(project_root, experiment_id)
    _validate_spec(spec, release, split_id, preprocessor_id, experiment_id)
    inputs = _load_inputs(project_root, release, split_id, preprocessor_id, np)
    training_mask = inputs["split_name"] == spec["fit_split"]
    baselines, baseline_predictions = _fit_baselines(inputs, training_mask, np)
    models: dict[str, Any] = {}
    predictions = dict(baseline_predictions)
    seed = int(spec["random_seed"])
    for name in LOSS_MODEL_NAMES:
        model_spec = spec["models"][name]
        params = {
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
            "random_state": seed,
        }
        model = xgboost.XGBRegressor(**params)
        model.fit(inputs["features"][training_mask], inputs["target"][training_mask])
        models[name] = model
        predictions[name] = model.predict(inputs["features"])
    metrics = _evaluate(spec, inputs, predictions, np)
    output_dir = _experiment_dir(
        project_root, release, split_id, preprocessor_id, experiment_id
    )
    if output_dir.exists():
        raise FileExistsError(
            f"experiment output already exists: {output_dir}; artifacts are immutable"
        )
    (output_dir / "models").mkdir(parents=True)
    (output_dir / "baseline_parameters.json").write_text(
        json.dumps(baselines, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    model_files = {}
    for name in LOSS_MODEL_NAMES:
        path = output_dir / "models" / f"{name}.joblib"
        joblib.dump(models[name], path, compress=3)
        model_files[name] = str(path.relative_to(output_dir))
    write_csv(
        output_dir / "predictions.csv",
        PREDICTION_FIELDS,
        _prediction_rows(inputs, predictions),
    )
    (output_dir / "metrics.json").write_text(
        json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    manifest = {
        "experiment_id": experiment_id,
        "dataset_release": release,
        "split_id": split_id,
        "preprocessor_id": preprocessor_id,
        "task_id": TASK_ID,
        "status": "completed_xgboost_robust_loss_local_analysis_only",
        "built_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "distribution": spec["distribution"],
        "fit_contract": _fit_evidence(inputs, training_mask, np),
        "config_sha256": sha256_file(config_path),
        "software_versions": versions,
        "model_contracts": {
            name: {
                "artifact": model_files[name],
                "objective": spec["models"][name]["objective"],
                "parameters": _json_parameters(models[name].get_params(deep=False)),
            }
            for name in LOSS_MODEL_NAMES
        },
    }
    (output_dir / "experiment_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return output_dir


def audit_ahs_xgboost_robust_loss_experiment(
    project_root: Path, output_dir: Path
) -> dict[str, Any]:
    manifest = json.loads((output_dir / "experiment_manifest.json").read_text(encoding="utf-8"))
    _, config_path = _load_spec(project_root, manifest["experiment_id"])
    passed = manifest.get("config_sha256") == sha256_file(config_path)
    return {
        "experiment_id": manifest["experiment_id"],
        "status": "passed" if passed else "failed",
        "summary": {"passed": int(passed), "failed": int(not passed)},
        "checks": [
            {
                "check_id": "experiment_config_unchanged",
                "status": "passed" if passed else "failed",
                "evidence": None,
            }
        ],
    }


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
        "system_order": SYSTEM_NAMES,
        "evaluation_splits": spec["evaluation_splits"],
        "evaluation_views": spec["evaluation_views"],
        "results": results,
    }


def _prediction_rows(inputs: dict[str, Any], predictions: dict[str, Any]) -> Any:
    from caip_maintenance.modeling.ahs_experiment import _float_text

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


def _robust_dependencies() -> tuple[Any, Any, Any, dict[str, str]]:
    import joblib
    import numpy as np
    import xgboost

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


def _load_spec(project_root: Path, experiment_id: str) -> tuple[dict[str, Any], Path]:
    if experiment_id != EXPERIMENT_ID:
        raise ValueError(f"supported XGBoost robust-loss experiment is {EXPERIMENT_ID!r}")
    path = project_root / "configs" / "experiments" / EXPERIMENT_CONFIG
    with path.open("rb") as handle:
        return tomllib.load(handle), path


def _validate_spec(
    spec: dict[str, Any],
    release: str,
    split_id: str,
    preprocessor_id: str,
    experiment_id: str,
) -> None:
    if spec["experiment_id"] != experiment_id or spec["dataset_release"] != release:
        raise ValueError("XGBoost robust-loss experiment specification mismatch")
    if preprocessor_id != FEATURE_ENGINEERING_PREPROCESSOR_ID:
        raise ValueError("XGBoost robust-loss requires ahs-feature-engineering-v1")
