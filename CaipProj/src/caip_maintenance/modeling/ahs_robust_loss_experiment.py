"""Compare gradient-boosting loss functions on the engineered AHS feature set."""

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


EXPERIMENT_ID = "ahs-robust-loss-v1"
EXPERIMENT_CONFIG = "ahs_robust_loss_v1.toml"
LOSS_MODEL_NAMES = (
    "gradient_boosting_squared",
    "gradient_boosting_absolute",
    "gradient_boosting_huber",
)
SYSTEM_NAMES = [*BASELINE_NAMES, *LOSS_MODEL_NAMES]
ROBUST_PREDICTION_FIELDS = [
    "snapshot_id",
    "split_name",
    "label_wave_year",
    "include_in_primary_metrics",
    "include_in_pre_2023_cap_sensitivity",
    "target_amount_usd",
    "is_high_cost",
    *[f"prediction_{name}_usd" for name in SYSTEM_NAMES],
]


def build_ahs_robust_loss_experiment(
    project_root: Path,
    release: str = DATASET_RELEASE,
    split_id: str = SPLIT_ID,
    preprocessor_id: str = FEATURE_ENGINEERING_PREPROCESSOR_ID,
    experiment_id: str = EXPERIMENT_ID,
) -> Path:
    np, joblib, hist_estimator, classic_estimator, versions = _robust_dependencies()
    spec, config_path = _load_robust_spec(project_root, experiment_id)
    _validate_robust_spec(spec, release, split_id, preprocessor_id, experiment_id)
    inputs = _load_inputs(project_root, release, split_id, preprocessor_id, np)
    training_mask = inputs["split_name"] == spec["fit_split"]
    baselines, baseline_predictions = _fit_baselines(inputs, training_mask, np)
    models: dict[str, Any] = {}
    predictions = dict(baseline_predictions)
    seed = int(spec["random_seed"])
    for name in LOSS_MODEL_NAMES:
        model_spec = spec["models"][name]
        if model_spec["loss"] == "huber":
            model = classic_estimator(
                loss="huber",
                learning_rate=float(model_spec["learning_rate"]),
                n_estimators=int(model_spec["max_iter"]),
                max_depth=int(model_spec["max_depth"]),
                min_samples_leaf=int(model_spec["min_samples_leaf"]),
                random_state=seed,
            )
        else:
            model = hist_estimator(
                loss=model_spec["loss"],
                learning_rate=float(model_spec["learning_rate"]),
                max_iter=int(model_spec["max_iter"]),
                max_leaf_nodes=int(model_spec["max_leaf_nodes"]),
                min_samples_leaf=int(model_spec["min_samples_leaf"]),
                l2_regularization=float(model_spec["l2_regularization"]),
                random_state=seed,
            )
        model.fit(inputs["features"][training_mask], inputs["target"][training_mask])
        models[name] = model
        predictions[name] = model.predict(inputs["features"])
    metrics = _evaluate_robust(spec, inputs, predictions, np)
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
    model_files = {}
    for name in LOSS_MODEL_NAMES:
        path = output_dir / "models" / f"{name}.joblib"
        joblib.dump(models[name], path, compress=3)
        model_files[name] = str(path.relative_to(output_dir))
    write_csv(
        output_dir / "predictions.csv",
        ROBUST_PREDICTION_FIELDS,
        _robust_prediction_rows(inputs, predictions),
    )
    (output_dir / "metrics.json").write_text(
        json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    fit_evidence = _fit_evidence(inputs, training_mask, np)
    manifest = {
        "experiment_id": experiment_id,
        "dataset_release": release,
        "split_id": split_id,
        "preprocessor_id": preprocessor_id,
        "task_id": TASK_ID,
        "status": "completed_robust_loss_comparison_local_analysis_only",
        "built_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "distribution": spec["distribution"],
        "fit_contract": fit_evidence,
        "config_sha256": sha256_file(config_path),
        "software_versions": versions,
        "model_contracts": {
            name: {
                "artifact": model_files[name],
                "loss": spec["models"][name]["loss"],
                "parameters": _json_parameters(models[name].get_params(deep=False)),
            }
            for name in LOSS_MODEL_NAMES
        },
    }
    (output_dir / "experiment_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return output_dir


def audit_ahs_robust_loss_experiment(project_root: Path, output_dir: Path) -> dict[str, Any]:
    manifest = json.loads(
        (output_dir / "experiment_manifest.json").read_text(encoding="utf-8")
    )
    _, config_path = _load_robust_spec(project_root, manifest["experiment_id"])
    checks = [
        {
            "check_id": "experiment_config_unchanged",
            "status": "passed"
            if manifest.get("config_sha256") == sha256_file(config_path)
            else "failed",
            "evidence": None,
        }
    ]
    failed = [item["check_id"] for item in checks if item["status"] == "failed"]
    return {
        "experiment_id": manifest["experiment_id"],
        "status": "passed" if not failed else "failed",
        "summary": {"passed": len(checks) - len(failed), "failed": len(failed)},
        "checks": checks,
    }


def _evaluate_robust(
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


def _robust_prediction_rows(inputs: dict[str, Any], predictions: dict[str, Any]) -> Any:
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


def _robust_dependencies() -> tuple[Any, Any, Any, Any, dict[str, str]]:
    import joblib
    import numpy as np
    import sklearn
    from sklearn.ensemble import GradientBoostingRegressor, HistGradientBoostingRegressor

    return (
        np,
        joblib,
        HistGradientBoostingRegressor,
        GradientBoostingRegressor,
        {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scikit_learn": sklearn.__version__,
            "joblib": joblib.__version__,
        },
    )


def _load_robust_spec(project_root: Path, experiment_id: str) -> tuple[dict[str, Any], Path]:
    if experiment_id != EXPERIMENT_ID:
        raise ValueError(f"supported robust-loss experiment is {EXPERIMENT_ID!r}")
    path = project_root / "configs" / "experiments" / EXPERIMENT_CONFIG
    with path.open("rb") as handle:
        return tomllib.load(handle), path


def _validate_robust_spec(
    spec: dict[str, Any],
    release: str,
    split_id: str,
    preprocessor_id: str,
    experiment_id: str,
) -> None:
    if spec["experiment_id"] != experiment_id or spec["dataset_release"] != release:
        raise ValueError("robust-loss experiment specification mismatch")
    if preprocessor_id != FEATURE_ENGINEERING_PREPROCESSOR_ID:
        raise ValueError("robust-loss experiment requires ahs-feature-engineering-v1")
