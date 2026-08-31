"""Validation-only hyperparameter tuning for the AHS proxy comparison."""

from __future__ import annotations

import itertools
import json
from datetime import datetime, timezone
from pathlib import Path
import tomllib
from typing import Any

from caip_maintenance.data.ahs import DATASET_RELEASE, TASK_ID
from caip_maintenance.data.ahs_split import SPLIT_ID
from caip_maintenance.data.common import sha256_file
from caip_maintenance.features.ahs_preprocessing import FEATURE_ENGINEERING_PREPROCESSOR_ID
from caip_maintenance.modeling.ahs_experiment import (
    BASELINE_NAMES,
    MODEL_NAMES,
    calculate_metrics,
    _check,
    _experiment_dir,
    _fit_baselines,
    _fit_evidence,
    _json_parameters,
    _load_inputs,
    _modeling_dependencies,
    _prediction_rows,
)


EXPERIMENT_ID = "ahs-model-tuning-v1"
EXPERIMENT_CONFIG = "ahs_model_tuning_v1.toml"
TUNED_MODEL_NAMES = ("random_forest", "gradient_boosting")


def build_ahs_tuning_experiment(
    project_root: Path,
    release: str = DATASET_RELEASE,
    split_id: str = SPLIT_ID,
    preprocessor_id: str = FEATURE_ENGINEERING_PREPROCESSOR_ID,
    experiment_id: str = EXPERIMENT_ID,
) -> Path:
    np, joblib, estimators, versions = _modeling_dependencies()
    spec, config_path = _load_tuning_spec(project_root, experiment_id)
    _validate_tuning_spec(spec, release, split_id, preprocessor_id, experiment_id)
    inputs = _load_inputs(project_root, release, split_id, preprocessor_id, np)
    training_mask = inputs["split_name"] == spec["fit_split"]
    selection_mask = (inputs["split_name"] == spec["selection_split"]) & inputs[
        "include_in_primary_metrics"
    ]
    baselines, baseline_predictions = _fit_baselines(inputs, training_mask, np)

    tuning_records: dict[str, Any] = {}
    models: dict[str, Any] = {}
    predictions: dict[str, Any] = dict(baseline_predictions)
    seed = int(spec["random_seed"])

    lr = estimators["linear_regression"](
        fit_intercept=bool(spec["models"]["linear_regression"]["fit_intercept"])
    )
    lr.fit(inputs["features"][training_mask], inputs["target"][training_mask])
    models["linear_regression"] = lr
    predictions["linear_regression"] = lr.predict(inputs["features"])

    for name in TUNED_MODEL_NAMES:
        best_params, best_mae, search_results = _select_best_params(
            spec,
            name,
            estimators[name],
            inputs,
            training_mask,
            selection_mask,
            seed,
            np,
        )
        model = estimators[name](**best_params)
        model.fit(inputs["features"][training_mask], inputs["target"][training_mask])
        models[name] = model
        predictions[name] = model.predict(inputs["features"])
        tuning_records[name] = {
            "selection_split": spec["selection_split"],
            "selection_view": spec["selection_view"],
            "selection_metric": spec["selection_metric"],
            "selected_parameters": best_params,
            "validation_primary_mae_usd": best_mae,
            "search_result_count": len(search_results),
            "search_results": search_results,
        }

    metrics = _evaluate_all(spec, inputs, predictions, np)
    output_dir = _experiment_dir(
        project_root, release, split_id, preprocessor_id, experiment_id
    )
    if output_dir.exists():
        raise FileExistsError(
            f"experiment output already exists: {output_dir}; artifacts are immutable"
        )
    (output_dir / "models").mkdir(parents=True)
    return _persist_tuning_artifacts(
        output_dir,
        spec,
        config_path,
        inputs,
        training_mask,
        baselines,
        models,
        predictions,
        metrics,
        tuning_records,
        versions,
        joblib,
        np,
    )


def audit_ahs_tuning_experiment(project_root: Path, output_dir: Path) -> dict[str, Any]:
    np, joblib, estimators, _ = _modeling_dependencies()
    manifest = json.loads(
        (output_dir / "experiment_manifest.json").read_text(encoding="utf-8")
    )
    spec, config_path = _load_tuning_spec(project_root, manifest["experiment_id"])
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
        "experiment_config_unchanged",
        manifest.get("config_sha256") == sha256_file(config_path),
        None,
    )
    stored_tuning = json.loads(
        (output_dir / "tuning_selection.json").read_text(encoding="utf-8")
    )
    _check(
        checks,
        "validation_only_selection_recorded",
        stored_tuning.get("selection_split") == "validation"
        and stored_tuning.get("selection_view") == "primary"
        and all(name in stored_tuning["models"] for name in TUNED_MODEL_NAMES),
        None,
    )
    failed = [check["check_id"] for check in checks if check["status"] == "failed"]
    return {
        "experiment_id": manifest["experiment_id"],
        "status": "passed" if not failed else "failed",
        "summary": {"passed": len(checks) - len(failed), "failed": len(failed)},
        "checks": checks,
    }


def _select_best_params(
    spec: dict[str, Any],
    model_name: str,
    estimator: Any,
    inputs: dict[str, Any],
    training_mask: Any,
    selection_mask: Any,
    seed: int,
    np: Any,
) -> tuple[dict[str, Any], float, list[dict[str, Any]]]:
    grid_spec = spec["models"][model_name]["search_grid"]
    keys = sorted(grid_spec)
    search_results: list[dict[str, Any]] = []
    best_mae = float("inf")
    best_params: dict[str, Any] | None = None
    for values in itertools.product(*(grid_spec[key] for key in keys)):
        params = dict(zip(keys, values))
        params["random_state"] = seed
        if model_name == "random_forest":
            params.setdefault("n_jobs", 1)
        if model_name == "gradient_boosting":
            params.pop("max_leaf_nodes", None)
        model = estimator(**params)
        model.fit(inputs["features"][training_mask], inputs["target"][training_mask])
        predicted = model.predict(inputs["features"][selection_mask])
        actual = inputs["target"][selection_mask]
        mae = float(np.mean(np.abs(predicted - actual)))
        search_results.append({"parameters": params, "validation_primary_mae_usd": mae})
        if mae < best_mae:
            best_mae = mae
            best_params = {key: value for key, value in params.items()}
    if best_params is None:
        raise ValueError(f"no tuning candidates for {model_name}")
    return best_params, best_mae, search_results


def _evaluate_all(
    spec: dict[str, Any], inputs: dict[str, Any], predictions: dict[str, Any], np: Any
) -> dict[str, Any]:
    threshold = float(spec["high_cost_threshold_usd"])
    view_masks = {
        "primary": inputs["include_in_primary_metrics"],
        "pre_2023_cap_sensitivity": inputs["include_in_pre_2023_cap_sensitivity"],
    }
    systems = [*BASELINE_NAMES, *MODEL_NAMES]
    results: dict[str, Any] = {}
    for system in systems:
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
        "hyperparameter_search": True,
        "model_selection": True,
        "selection_split": spec["selection_split"],
        "selection_view": spec["selection_view"],
        "evaluation_splits": spec["evaluation_splits"],
        "evaluation_views": spec["evaluation_views"],
        "system_order": systems,
        "results": results,
    }


def _persist_tuning_artifacts(
    output_dir: Path,
    spec: dict[str, Any],
    config_path: Path,
    inputs: dict[str, Any],
    training_mask: Any,
    baselines: dict[str, Any],
    models: dict[str, Any],
    predictions: dict[str, Any],
    metrics: dict[str, Any],
    tuning_records: dict[str, Any],
    versions: dict[str, str],
    joblib: Any,
    np: Any,
) -> Path:
    from caip_maintenance.data.common import write_csv
    from caip_maintenance.modeling.ahs_experiment import PREDICTION_FIELDS

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
    write_csv(prediction_path, PREDICTION_FIELDS, _prediction_rows(inputs, predictions))
    metrics_path = output_dir / "metrics.json"
    metrics_path.write_text(
        json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    tuning_path = output_dir / "tuning_selection.json"
    tuning_payload = {
        "selection_split": spec["selection_split"],
        "selection_view": spec["selection_view"],
        "selection_metric": spec["selection_metric"],
        "models": tuning_records,
    }
    tuning_path.write_text(
        json.dumps(tuning_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    fit_evidence = _fit_evidence(inputs, training_mask, np)
    manifest = {
        "experiment_id": spec["experiment_id"],
        "dataset_release": spec["dataset_release"],
        "split_id": spec["split_id"],
        "preprocessor_id": spec["preprocessor_id"],
        "task_id": TASK_ID,
        "status": "completed_validation_tuned_local_analysis_only",
        "built_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "distribution": spec["distribution"],
        "fit_contract": {
            "fit_split": spec["fit_split"],
            "held_out_labels_used_for_fit": False,
            "hyperparameter_search": True,
            "model_selection": True,
            "selection_split": spec["selection_split"],
            "selection_view": spec["selection_view"],
            **fit_evidence,
        },
        "config_sha256": sha256_file(config_path),
        "software_versions": versions,
        "model_contracts": {
            name: {
                "artifact": model_files[name],
                "parameters": _json_parameters(models[name].get_params(deep=False)),
            }
            for name in MODEL_NAMES
        },
    }
    (output_dir / "experiment_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return output_dir


def _load_tuning_spec(project_root: Path, experiment_id: str) -> tuple[dict[str, Any], Path]:
    if experiment_id != EXPERIMENT_ID:
        raise ValueError(f"supported tuning experiment is {EXPERIMENT_ID!r}")
    path = project_root / "configs" / "experiments" / EXPERIMENT_CONFIG
    with path.open("rb") as handle:
        return tomllib.load(handle), path


def _validate_tuning_spec(
    spec: dict[str, Any],
    release: str,
    split_id: str,
    preprocessor_id: str,
    experiment_id: str,
) -> None:
    if spec["experiment_id"] != experiment_id:
        raise ValueError("tuning experiment specification mismatch")
    if spec["dataset_release"] != release or spec["split_id"] != split_id:
        raise ValueError("tuning experiment release/split mismatch")
    if preprocessor_id != FEATURE_ENGINEERING_PREPROCESSOR_ID:
        raise ValueError("tuning experiment requires ahs-feature-engineering-v1 preprocessor")
    if spec["selection_split"] != "validation":
        raise ValueError("hyperparameters must be selected on validation rows only")
    if spec["selection_view"] != "primary":
        raise ValueError("hyperparameters must be selected on the primary view")
    if not spec.get("hyperparameter_search") or not spec.get("model_selection"):
        raise ValueError("tuning experiment must declare search and selection")
