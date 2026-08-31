"""Validation-only hyperparameter tuning for the AHS XGBoost comparison."""

from __future__ import annotations

import itertools
import json
from datetime import datetime, timezone
from pathlib import Path
import tomllib
from typing import Any

from caip_maintenance.data.ahs import DATASET_RELEASE, TASK_ID
from caip_maintenance.data.ahs_split import SPLIT_ID
from caip_maintenance.data.common import sha256_file, write_csv
from caip_maintenance.features.ahs_preprocessing import FEATURE_ENGINEERING_PREPROCESSOR_ID
from caip_maintenance.modeling.ahs_experiment import (
    calculate_metrics,
    _experiment_dir,
    _fit_baselines,
    _fit_evidence,
    _json_parameters,
    _load_inputs,
)
from caip_maintenance.modeling.ahs_xgboost_experiment import (
    MODEL_NAME,
    PREDICTION_FIELDS,
    _evaluate,
    _prediction_rows,
    _xgboost_dependencies,
)


EXPERIMENT_ID = "ahs-xgboost-tuning-v1"
EXPERIMENT_CONFIG = "ahs_xgboost_tuning_v1.toml"


def build_ahs_xgboost_tuning_experiment(
    project_root: Path,
    release: str = DATASET_RELEASE,
    split_id: str = SPLIT_ID,
    preprocessor_id: str = FEATURE_ENGINEERING_PREPROCESSOR_ID,
    experiment_id: str = EXPERIMENT_ID,
) -> Path:
    np, joblib, xgboost, versions = _xgboost_dependencies()
    spec, config_path = _load_spec(project_root, experiment_id)
    _validate_spec(spec, release, split_id, preprocessor_id, experiment_id)
    inputs = _load_inputs(project_root, release, split_id, preprocessor_id, np)
    training_mask = inputs["split_name"] == spec["fit_split"]
    selection_mask = (inputs["split_name"] == spec["selection_split"]) & inputs[
        "include_in_primary_metrics"
    ]
    baselines, baseline_predictions = _fit_baselines(inputs, training_mask, np)
    best_params, best_mae, search_results = _select_best_params(
        spec, xgboost, inputs, training_mask, selection_mask, np
    )
    model = xgboost.XGBRegressor(**best_params)
    model.fit(inputs["features"][training_mask], inputs["target"][training_mask])
    predictions = baseline_predictions | {MODEL_NAME: model.predict(inputs["features"])}
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
    model_path = output_dir / "models" / f"{MODEL_NAME}.joblib"
    joblib.dump(model, model_path, compress=3)
    write_csv(output_dir / "predictions.csv", PREDICTION_FIELDS, _prediction_rows(inputs, predictions))
    (output_dir / "metrics.json").write_text(
        json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_dir / "tuning_selection.json").write_text(
        json.dumps(
            {
                "selection_split": spec["selection_split"],
                "selection_view": spec["selection_view"],
                "selection_metric": spec["selection_metric"],
                "models": {
                    MODEL_NAME: {
                        "validation_primary_mae_usd": best_mae,
                        "search_result_count": len(search_results),
                        "selected_parameters": best_params,
                        "search_results": search_results,
                    }
                },
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    manifest = {
        "experiment_id": experiment_id,
        "dataset_release": release,
        "split_id": split_id,
        "preprocessor_id": preprocessor_id,
        "task_id": TASK_ID,
        "status": "completed_validation_tuned_local_analysis_only",
        "built_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "distribution": spec["distribution"],
        "fit_contract": _fit_evidence(inputs, training_mask, np),
        "config_sha256": sha256_file(config_path),
        "software_versions": versions,
        "model_contracts": {
            MODEL_NAME: {
                "artifact": str(model_path.relative_to(output_dir)),
                "parameters": _json_parameters(model.get_params(deep=False)),
            }
        },
    }
    (output_dir / "experiment_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return output_dir


def audit_ahs_xgboost_tuning_experiment(project_root: Path, output_dir: Path) -> dict[str, Any]:
    manifest = json.loads((output_dir / "experiment_manifest.json").read_text(encoding="utf-8"))
    _, config_path = _load_spec(project_root, manifest["experiment_id"])
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


def _select_best_params(
    spec: dict[str, Any],
    xgboost: Any,
    inputs: dict[str, Any],
    training_mask: Any,
    selection_mask: Any,
    np: Any,
) -> tuple[dict[str, Any], float, list[dict[str, Any]]]:
    grid_spec = spec["models"][MODEL_NAME]["search_grid"]
    keys = sorted(grid_spec)
    search_results: list[dict[str, Any]] = []
    best_mae = float("inf")
    best_params: dict[str, Any] | None = None
    seed = int(spec["random_seed"])
    for values in itertools.product(*(grid_spec[key] for key in keys)):
        params = {
            "objective": "reg:squarederror",
            "tree_method": str(spec["models"][MODEL_NAME]["tree_method"]),
            "n_jobs": int(spec["models"][MODEL_NAME]["n_jobs"]),
            "reg_lambda": 1.0,
            "reg_alpha": 0.0,
            "random_state": seed,
            **dict(zip(keys, values)),
        }
        model = xgboost.XGBRegressor(**params)
        model.fit(inputs["features"][training_mask], inputs["target"][training_mask])
        predicted = model.predict(inputs["features"][selection_mask])
        mae = float(np.mean(np.abs(predicted - inputs["target"][selection_mask])))
        search_results.append({"parameters": params, "validation_primary_mae_usd": mae})
        if mae < best_mae:
            best_mae = mae
            best_params = dict(params)
    if best_params is None:
        raise ValueError("no XGBoost tuning candidates")
    return best_params, best_mae, search_results


def _load_spec(project_root: Path, experiment_id: str) -> tuple[dict[str, Any], Path]:
    if experiment_id != EXPERIMENT_ID:
        raise ValueError(f"supported XGBoost tuning experiment is {EXPERIMENT_ID!r}")
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
        raise ValueError("XGBoost tuning experiment specification mismatch")
    if preprocessor_id != FEATURE_ENGINEERING_PREPROCESSOR_ID:
        raise ValueError("XGBoost tuning requires ahs-feature-engineering-v1")
    if spec["selection_split"] != "validation" or spec["selection_view"] != "primary":
        raise ValueError("XGBoost hyperparameters must be selected on validation primary MAE")
