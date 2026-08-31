"""Load audited experiment artifacts and score one property snapshot."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from caip_maintenance.features.ahs_inference import (
    feature_column_names,
    load_preprocessor_artifact,
    transform_snapshot,
    vector_from_transform,
)


DEFAULT_RELEASE = "public-corpus-v0.2.0-ahs"
DEFAULT_SPLIT = "ahs-grouped-temporal-v1"
DEFAULT_PREPROCESSOR = "ahs-feature-engineering-v1"
DEFAULT_EXPERIMENT = "ahs-xgboost-tuning-v1"
DEFAULT_MODEL = "xgboost"

DISCLAIMER = (
    "Decision-support demo only. Predictions use a WAPDA-modelled public proxy dataset "
    "(mapped AHS records), not observed WAPDA work orders. Amounts are in USD survey "
    "units, not PKR."
)


@dataclass(frozen=True)
class PredictionResult:
    predictions_usd: dict[str, float]
    high_cost_threshold_usd: float
    high_cost_flags: dict[str, bool]
    experiment_id: str
    preprocessor_id: str
    model_name: str
    disclaimer: str


@dataclass(frozen=True)
class InferenceBundle:
    project_root: Path
    release: str
    split_id: str
    preprocessor_id: str
    experiment_id: str
    preprocessor: dict[str, Any]
    baseline_parameters: dict[str, Any]
    model_name: str
    model: Any
    high_cost_threshold_usd: float
    feature_columns: list[str]


def default_experiment_dir(project_root: Path) -> Path:
    return (
        project_root
        / "artifacts"
        / "experiments"
        / DEFAULT_RELEASE
        / DEFAULT_SPLIT
        / DEFAULT_PREPROCESSOR
        / DEFAULT_EXPERIMENT
    )


def load_inference_bundle(
    project_root: Path,
    *,
    release: str = DEFAULT_RELEASE,
    split_id: str = DEFAULT_SPLIT,
    preprocessor_id: str = DEFAULT_PREPROCESSOR,
    experiment_id: str = DEFAULT_EXPERIMENT,
    model_name: str = DEFAULT_MODEL,
) -> InferenceBundle:
    """Load preprocessor artifact, baseline parameters, and one fitted model."""
    experiment_dir = (
        project_root
        / "artifacts"
        / "experiments"
        / release
        / split_id
        / preprocessor_id
        / experiment_id
    )
    manifest_path = experiment_dir / "experiment_manifest.json"
    baseline_path = experiment_dir / "baseline_parameters.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(
            f"experiment manifest not found: {manifest_path}. "
            "Train ahs-xgboost-tuning-v1 before starting the app."
        )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    contract = manifest["model_contracts"][model_name]
    model_path = experiment_dir / contract["artifact"]
    if not model_path.is_file():
        raise FileNotFoundError(f"model artifact not found: {model_path}")

    try:
        import joblib
    except ImportError as exc:
        raise RuntimeError(
            "inference requires joblib; install requirements-modeling.txt"
        ) from exc

    preprocessor = load_preprocessor_artifact(project_root, preprocessor_id)
    baseline_parameters = json.loads(baseline_path.read_text(encoding="utf-8"))
    threshold = float(preprocessor["high_cost_policy"]["threshold_amount_local_nominal"])
    model = joblib.load(model_path)
    return InferenceBundle(
        project_root=project_root,
        release=release,
        split_id=split_id,
        preprocessor_id=preprocessor_id,
        experiment_id=experiment_id,
        preprocessor=preprocessor,
        baseline_parameters=baseline_parameters,
        model_name=model_name,
        model=model,
        high_cost_threshold_usd=threshold,
        feature_columns=feature_column_names(preprocessor),
    )


def predict_snapshot(
    bundle: InferenceBundle, snapshot: dict[str, str]
) -> PredictionResult:
    """Score one harmonized snapshot with baselines and the loaded fitted model."""
    transform = transform_snapshot(snapshot, bundle.preprocessor)
    vector = vector_from_transform(transform, bundle.preprocessor)

    try:
        import numpy as np
    except ImportError as exc:
        raise RuntimeError("inference requires numpy") from exc

    feature_matrix = np.asarray([vector], dtype=np.float64)
    fitted_prediction = float(bundle.model.predict(feature_matrix)[0])
    predictions = {
        "training_median": _training_median(bundle.baseline_parameters),
        "type_median": _type_median(snapshot, bundle.baseline_parameters),
        "prior_cost": _prior_cost(snapshot, bundle.baseline_parameters),
        bundle.model_name: fitted_prediction,
    }
    flags = {
        name: value >= bundle.high_cost_threshold_usd
        for name, value in predictions.items()
    }
    return PredictionResult(
        predictions_usd=predictions,
        high_cost_threshold_usd=bundle.high_cost_threshold_usd,
        high_cost_flags=flags,
        experiment_id=bundle.experiment_id,
        preprocessor_id=bundle.preprocessor_id,
        model_name=bundle.model_name,
        disclaimer=DISCLAIMER,
    )


def _training_median(baseline_parameters: dict[str, Any]) -> float:
    return float(baseline_parameters["training_median"]["prediction_usd"])


def _type_median(snapshot: dict[str, str], baseline_parameters: dict[str, Any]) -> float:
    block = baseline_parameters["type_median"]
    building_type = snapshot.get("building_type_code", "")
    if building_type == "":
        return float(block["fallback_prediction_usd"])
    medians = block["group_median_usd"]
    return float(medians.get(building_type, block["fallback_prediction_usd"]))


def _prior_cost(snapshot: dict[str, str], baseline_parameters: dict[str, Any]) -> float:
    block = baseline_parameters["prior_cost"]
    raw = snapshot.get("prior_routine_maintenance_usd", "")
    if raw == "":
        return float(block["fallback_prediction_usd"])
    return float(raw)
