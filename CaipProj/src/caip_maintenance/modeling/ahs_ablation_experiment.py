"""Feature-group ablation using gradient boosting on engineered AHS features."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
import tomllib
from typing import Any

from caip_maintenance.data.ahs import DATASET_RELEASE, TASK_ID
from caip_maintenance.data.ahs_split import SPLIT_ID
from caip_maintenance.data.common import sha256_file, write_csv
from caip_maintenance.features.ahs_derived_features import matrix_columns_for_groups
from caip_maintenance.features.ahs_preprocessing import FEATURE_ENGINEERING_PREPROCESSOR_ID
from caip_maintenance.modeling.ahs_experiment import (
    BASELINE_NAMES,
    calculate_metrics,
    _check,
    _experiment_dir,
    _fit_baselines,
    _fit_evidence,
    _json_parameters,
    _load_inputs,
    _modeling_dependencies,
)


EXPERIMENT_ID = "ahs-feature-ablation-v1"
EXPERIMENT_CONFIG = "ahs_feature_ablation_v1.toml"


def build_ahs_ablation_experiment(
    project_root: Path,
    release: str = DATASET_RELEASE,
    split_id: str = SPLIT_ID,
    preprocessor_id: str = FEATURE_ENGINEERING_PREPROCESSOR_ID,
    experiment_id: str = EXPERIMENT_ID,
) -> Path:
    np, joblib, estimators, versions = _modeling_dependencies()
    spec, config_path = _load_ablation_spec(project_root, experiment_id)
    _validate_ablation_spec(spec, release, split_id, preprocessor_id, experiment_id)
    inputs = _load_inputs(project_root, release, split_id, preprocessor_id, np)
    training_mask = inputs["split_name"] == spec["fit_split"]
    baselines, baseline_predictions = _fit_baselines(inputs, training_mask, np)
    preprocessor = _load_preprocessor(project_root, release, split_id, preprocessor_id)
    ablation_names = sorted(spec["ablation_configs"])
    system_names = [*BASELINE_NAMES, *ablation_names]
    models: dict[str, Any] = {}
    predictions = dict(baseline_predictions)
    seed = int(spec["random_seed"])
    model_spec = spec["models"]["gradient_boosting"]
    for ablation_name in ablation_names:
        column_names = matrix_columns_for_groups(
            preprocessor,
            tuple(spec["ablation_configs"][ablation_name]["feature_groups"]),
        )
        indices = _column_indices(inputs["feature_columns"], column_names)
        features = inputs["features"][:, indices]
        model = estimators["gradient_boosting"](
            learning_rate=float(model_spec["learning_rate"]),
            max_iter=int(model_spec["max_iter"]),
            max_leaf_nodes=int(model_spec["max_leaf_nodes"]),
            min_samples_leaf=int(model_spec["min_samples_leaf"]),
            l2_regularization=float(model_spec["l2_regularization"]),
            random_state=seed,
        )
        model.fit(features[training_mask], inputs["target"][training_mask])
        models[ablation_name] = model
        predictions[ablation_name] = model.predict(features)
    metrics = _evaluate_ablation(spec, inputs, predictions, system_names, np)
    output_dir = _experiment_dir(
        project_root, release, split_id, preprocessor_id, experiment_id
    )
    if output_dir.exists():
        raise FileExistsError(
            f"experiment output already exists: {output_dir}; artifacts are immutable"
        )
    (output_dir / "models").mkdir(parents=True)
    ablation_contracts = {}
    for ablation_name in ablation_names:
        path = output_dir / "models" / f"{ablation_name}.joblib"
        joblib.dump(models[ablation_name], path, compress=3)
        column_names = matrix_columns_for_groups(
            preprocessor,
            tuple(spec["ablation_configs"][ablation_name]["feature_groups"]),
        )
        ablation_contracts[ablation_name] = {
            "artifact": str(path.relative_to(output_dir)),
            "feature_groups": spec["ablation_configs"][ablation_name]["feature_groups"],
            "matrix_column_count": len(column_names),
            "parameters": _json_parameters(models[ablation_name].get_params(deep=False)),
        }
    (output_dir / "baseline_parameters.json").write_text(
        json.dumps(baselines, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    write_csv(
        output_dir / "predictions.csv",
        _ablation_prediction_fields(system_names),
        _ablation_prediction_rows(inputs, predictions, system_names),
    )
    (output_dir / "metrics.json").write_text(
        json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_dir / "ablation_contracts.json").write_text(
        json.dumps(ablation_contracts, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    manifest = {
        "experiment_id": experiment_id,
        "dataset_release": release,
        "split_id": split_id,
        "preprocessor_id": preprocessor_id,
        "task_id": TASK_ID,
        "status": "completed_feature_ablation_local_analysis_only",
        "built_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "distribution": spec["distribution"],
        "fit_contract": _fit_evidence(inputs, training_mask, np),
        "config_sha256": sha256_file(config_path),
        "software_versions": versions,
        "ablation_contracts": ablation_contracts,
    }
    (output_dir / "experiment_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return output_dir


def audit_ahs_ablation_experiment(project_root: Path, output_dir: Path) -> dict[str, Any]:
    manifest = json.loads(
        (output_dir / "experiment_manifest.json").read_text(encoding="utf-8")
    )
    _, config_path = _load_ablation_spec(project_root, manifest["experiment_id"])
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


def _evaluate_ablation(
    spec: dict[str, Any],
    inputs: dict[str, Any],
    predictions: dict[str, Any],
    system_names: list[str],
    np: Any,
) -> dict[str, Any]:
    threshold = float(spec["high_cost_threshold_usd"])
    view_masks = {
        "primary": inputs["include_in_primary_metrics"],
        "pre_2023_cap_sensitivity": inputs["include_in_pre_2023_cap_sensitivity"],
    }
    results: dict[str, Any] = {}
    for system in system_names:
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
        "system_order": system_names,
        "evaluation_splits": spec["evaluation_splits"],
        "evaluation_views": spec["evaluation_views"],
        "results": results,
    }


def _column_indices(feature_columns: list[str], selected: list[str]) -> list[int]:
    index = {name: position for position, name in enumerate(feature_columns)}
    return [index[name] for name in selected]


def _load_preprocessor(
    project_root: Path, release: str, split_id: str, preprocessor_id: str
) -> dict[str, Any]:
    path = (
        project_root
        / "data"
        / "processed"
        / "preprocessing"
        / release
        / split_id
        / preprocessor_id
        / "preprocessor.json"
    )
    return json.loads(path.read_text(encoding="utf-8"))


def _ablation_prediction_fields(system_names: list[str]) -> list[str]:
    return [
        "snapshot_id",
        "split_name",
        "label_wave_year",
        "include_in_primary_metrics",
        "include_in_pre_2023_cap_sensitivity",
        "target_amount_usd",
        "is_high_cost",
        *[f"prediction_{name}_usd" for name in system_names],
    ]


def _ablation_prediction_rows(
    inputs: dict[str, Any], predictions: dict[str, Any], system_names: list[str]
) -> Any:
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
                for name in system_names
            },
        }


def _load_ablation_spec(project_root: Path, experiment_id: str) -> tuple[dict[str, Any], Path]:
    if experiment_id != EXPERIMENT_ID:
        raise ValueError(f"supported ablation experiment is {EXPERIMENT_ID!r}")
    path = project_root / "configs" / "experiments" / EXPERIMENT_CONFIG
    with path.open("rb") as handle:
        return tomllib.load(handle), path


def _validate_ablation_spec(
    spec: dict[str, Any],
    release: str,
    split_id: str,
    preprocessor_id: str,
    experiment_id: str,
) -> None:
    if spec["experiment_id"] != experiment_id or spec["dataset_release"] != release:
        raise ValueError("ablation experiment specification mismatch")
    if preprocessor_id != FEATURE_ENGINEERING_PREPROCESSOR_ID:
        raise ValueError("ablation experiment requires ahs-feature-engineering-v1")
