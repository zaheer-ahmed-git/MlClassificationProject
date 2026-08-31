"""Transform one cutoff-safe AHS/WAPDA-model snapshot for fitted-model inference."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from caip_maintenance.features.ahs_derived_features import enrich_snapshot
from caip_maintenance.features.ahs_preprocessing import (
    FEATURE_ENGINEERING_PREPROCESSOR_ID,
    PREPROCESSOR_CONFIGS,
)


def load_preprocessor_artifact(project_root: Path, preprocessor_id: str) -> dict[str, Any]:
    """Load a frozen training-fit preprocessor JSON artifact."""
    artifact_path = (
        project_root
        / "data"
        / "processed"
        / "preprocessing"
        / "public-corpus-v0.2.0-ahs"
        / "ahs-grouped-temporal-v1"
        / preprocessor_id
        / "preprocessor.json"
    )
    if not artifact_path.is_file():
        raise FileNotFoundError(
            f"preprocessor artifact not found: {artifact_path}. "
            "Run preprocess-ahs before starting the app."
        )
    return json.loads(artifact_path.read_text(encoding="utf-8"))


def feature_column_names(preprocessor: dict[str, Any]) -> list[str]:
    columns = preprocessor["feature_matrix_columns"]
    if not columns or columns[0] != "snapshot_id":
        raise ValueError("preprocessor feature_matrix_columns must start with snapshot_id")
    return list(columns[1:])


def transform_snapshot(
    snapshot: dict[str, str],
    preprocessor: dict[str, Any],
    *,
    include_derived: bool | None = None,
) -> dict[str, float]:
    """Return one model-input row keyed by frozen matrix column names."""
    if include_derived is None:
        include_derived = preprocessor["preprocessor_id"] == FEATURE_ENGINEERING_PREPROCESSOR_ID
    working = enrich_snapshot(snapshot) if include_derived else dict(snapshot)
    parameters = {item["feature_name"]: item for item in preprocessor["feature_parameters"]}
    output: dict[str, float] = {}
    for parameter in preprocessor["feature_parameters"]:
        name = parameter["feature_name"]
        kind = parameter["source_type"]
        raw = working.get(name, "")
        is_missing = raw == ""
        if parameter["value_feature_included"] and kind == "number":
            value = (
                float(parameter["imputer"]["fill_value"])
                if is_missing
                else _finite_float(raw, name)
            )
            scaled = (
                value - float(parameter["scaler"]["mean_after_imputation"])
            ) / float(parameter["scaler"]["scale"])
            output[parameter["value_output_column"]] = scaled
        elif parameter["value_feature_included"]:
            encoder = parameter["encoder"]
            category_index = {
                category: index
                for index, category in enumerate(encoder["training_categories"])
            }
            selected = category_index.get(raw) if not is_missing else None
            for index, column in enumerate(encoder["category_output_columns"]):
                output[column] = float(index == selected)
            output[encoder["reserved_missing_output_column"]] = float(is_missing)
            output[encoder["reserved_unknown_output_column"]] = float(
                not is_missing and raw not in category_index
            )
        output[parameter["missing_indicator_column"]] = float(is_missing)
    expected = feature_column_names(preprocessor)
    if set(output) != set(expected):
        missing = set(expected) - set(output)
        extra = set(output) - set(expected)
        raise ValueError(f"transform column mismatch: missing={missing}, extra={extra}")
    return {name: output[name] for name in expected}


def vector_from_transform(
    transform: dict[str, float], preprocessor: dict[str, Any]
) -> list[float]:
    columns = feature_column_names(preprocessor)
    return [transform[name] for name in columns]


def _finite_float(raw: str, feature_name: str) -> float:
    value = float(raw)
    if not (value == value and abs(value) != float("inf")):
        raise ValueError(f"non-finite numeric value for {feature_name!r}")
    return value


def preprocessor_config_path(project_root: Path, preprocessor_id: str) -> Path:
    config_name = PREPROCESSOR_CONFIGS[preprocessor_id]
    return project_root / "configs" / "preprocessing" / config_name
