"""Fit and audit the training-only AHS preprocessing contract."""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
import math
from pathlib import Path
import tomllib
from typing import Any, Iterator

from caip_maintenance.data.ahs import DATASET_RELEASE, FEATURE_MAP, TASK_ID
from caip_maintenance.data.ahs_split import SPLIT_ID
from caip_maintenance.data.common import sha256_file, write_csv
from caip_maintenance.features.ahs_derived_features import (
    combined_feature_map,
    enrich_snapshot,
)


PREPROCESSOR_ID = "ahs-training-fold-v1"
FEATURE_ENGINEERING_PREPROCESSOR_ID = "ahs-feature-engineering-v1"
PREPROCESSOR_CONFIGS = {
    PREPROCESSOR_ID: "ahs_training_fold_v1.toml",
    FEATURE_ENGINEERING_PREPROCESSOR_ID: "ahs_feature_engineering_v1.toml",
}
SUPPORTED_PREPROCESSOR_IDS = frozenset(PREPROCESSOR_CONFIGS)
HIGH_COST_THRESHOLD_VERSION = "ahs-high-cost-training-top20-v1"
TARGET_FIELDS = [
    "snapshot_id",
    "split_name",
    "task_id",
    "target_amount_local_nominal",
    "target_currency",
    "feature_wave_year",
    "label_wave_year",
    "source_response_maximum_usd",
    "response_cap_regime",
    "include_in_primary_metrics",
    "include_in_pre_2023_cap_sensitivity",
    "high_cost_threshold_version",
    "is_high_cost",
    "target_was_imputed",
    "target_was_clipped",
]


def build_ahs_preprocessing(
    project_root: Path,
    release: str = DATASET_RELEASE,
    split_id: str = SPLIT_ID,
    preprocessor_id: str = PREPROCESSOR_ID,
) -> Path:
    """Fit transforms on AHS training rows and transform all frozen split rows."""
    spec, config_path = _load_spec(project_root, preprocessor_id)
    _validate_spec(spec, release, split_id, preprocessor_id)
    inputs = _load_inputs(project_root, release, split_id)
    fit = _fit_training_contract(inputs, spec)

    output_dir = (
        project_root
        / "data"
        / "processed"
        / "preprocessing"
        / release
        / split_id
        / preprocessor_id
    )
    if output_dir.exists():
        raise FileExistsError(
            f"preprocessing output already exists: {output_dir}; artifacts are immutable"
        )
    output_dir.mkdir(parents=True)

    artifact = _artifact(spec, config_path, inputs, fit)
    artifact_path = output_dir / "preprocessor.json"
    artifact_path.write_text(
        json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    feature_path = output_dir / "feature_matrix.csv"
    target_path = output_dir / "target_metadata.csv"
    feature_count, target_count = _write_outputs(
        inputs, fit, spec, feature_path, target_path
    )
    manifest = {
        "preprocessor_id": preprocessor_id,
        "preprocessing_contract_version": spec["preprocessing_contract_version"],
        "dataset_release": release,
        "split_id": split_id,
        "task_id": TASK_ID,
        "status": "fitted_training_only_local_analysis_only",
        "built_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "distribution": spec["distribution"],
        "fit_split": spec["fit_split"],
        "source_sha256": inputs["source_sha256"],
        "config_sha256": sha256_file(config_path),
        "counts": {
            "feature_rows": feature_count,
            "target_rows": target_count,
            "fit_rows": fit["fit_row_count"],
            "feature_columns_excluding_key": len(fit["output_columns"]),
            "candidate_features": len(_candidate_features(spec)),
            "value_features_included": sum(
                parameter["value_feature_included"]
                for parameter in fit["feature_parameters"]
            ),
            "value_features_excluded_for_training_missingness": sum(
                not parameter["value_feature_included"]
                for parameter in fit["feature_parameters"]
            ),
        },
        "target_policy": {
            "imputation": spec["target_imputation"],
            "clipping": spec["target_clipping"],
            "cap_sensitivity_metadata_preserved": True,
        },
        "high_cost_policy": artifact["high_cost_policy"],
        "output_sha256": {
            "preprocessor.json": sha256_file(artifact_path),
            "feature_matrix.csv": sha256_file(feature_path),
            "target_metadata.csv": sha256_file(target_path),
        },
        "prohibited_claims": [
            "observed WAPDA outcome",
            "exact WAPDA next-12-month target",
            "validated WASC forecast",
            "trained model or model result",
        ],
    }
    (output_dir / "preprocessing_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return output_dir


def audit_ahs_preprocessing(project_root: Path, output_dir: Path) -> dict[str, Any]:
    """Recompute the fit contract and audit leakage, transformations, and targets."""
    manifest = json.loads(
        (output_dir / "preprocessing_manifest.json").read_text(encoding="utf-8")
    )
    artifact = json.loads((output_dir / "preprocessor.json").read_text(encoding="utf-8"))
    release = manifest["dataset_release"]
    split_id = manifest["split_id"]
    preprocessor_id = manifest["preprocessor_id"]
    spec, config_path = _load_spec(project_root, preprocessor_id)
    _validate_spec(spec, release, split_id, preprocessor_id)
    inputs = _load_inputs(project_root, release, split_id)
    expected_fit = _fit_training_contract(inputs, spec)
    expected_artifact = _artifact(spec, config_path, inputs, expected_fit)
    checks: list[dict[str, Any]] = []

    _check(
        checks,
        "source_inputs_unchanged",
        manifest["source_sha256"] == inputs["source_sha256"],
        None,
    )
    _check(
        checks,
        "preprocessing_config_unchanged",
        manifest["config_sha256"] == sha256_file(config_path),
        None,
    )
    output_drift = {
        name: {
            "expected": expected,
            "actual": sha256_file(output_dir / name)
            if (output_dir / name).is_file()
            else None,
        }
        for name, expected in manifest["output_sha256"].items()
        if not (output_dir / name).is_file()
        or sha256_file(output_dir / name) != expected
    }
    _check(checks, "output_checksums", not output_drift, output_drift)
    _check(
        checks,
        "artifact_recomputes_from_training_only",
        artifact == expected_artifact,
        {
            "fit_split": artifact.get("fit_split"),
            "fit_rows": artifact.get("fit_row_count"),
            "fit_snapshot_ids_sha256": artifact.get("fit_snapshot_ids_sha256"),
        },
    )
    _check(
        checks,
        "training_ids_are_the_only_fit_ids",
        artifact.get("fit_snapshot_ids_sha256")
        == _snapshot_id_digest(
            snapshot_id
            for snapshot_id, assignment in inputs["assignments"].items()
            if assignment["split_name"] == "training"
        )
        and artifact.get("fit_row_count")
        == sum(
            assignment["split_name"] == "training"
            for assignment in inputs["assignments"].values()
        ),
        None,
    )
    _check(
        checks,
        "target_imputation_and_clipping_prohibited",
        artifact.get("target_policy")
        == {
            "cap_sensitivity_metadata_preserved": True,
            "clipping": "prohibited",
            "imputation": "prohibited",
        },
        artifact.get("target_policy"),
    )

    feature_failures, feature_rows = _audit_feature_matrix(
        inputs, expected_fit, spec, output_dir / "feature_matrix.csv"
    )
    _check(
        checks,
        "feature_matrix_reproduces_frozen_transform",
        feature_failures == 0,
        {"rows": feature_rows, "mismatches": feature_failures},
    )
    target_failures, target_rows = _audit_targets(
        inputs, expected_fit, output_dir / "target_metadata.csv"
    )
    _check(
        checks,
        "targets_and_cap_metadata_preserved_without_clipping",
        target_failures == 0,
        {"rows": target_rows, "mismatches": target_failures},
    )
    _check(
        checks,
        "row_counts_match_frozen_split",
        feature_rows == target_rows == len(inputs["assignments"]),
        {
            "feature_rows": feature_rows,
            "target_rows": target_rows,
            "split_rows": len(inputs["assignments"]),
        },
    )
    _check(
        checks,
        "missingness_indicators_cover_all_candidates",
        all(
            f"{name}__is_missing" in expected_fit["output_columns"]
            for name, _, _ in _candidate_features(spec)
        ),
        None,
    )
    _check(
        checks,
        "high_cost_threshold_is_training_label_quantile",
        artifact.get("high_cost_policy") == expected_artifact["high_cost_policy"],
        artifact.get("high_cost_policy"),
    )

    failed = [check["check_id"] for check in checks if check["status"] == "failed"]
    return {
        "dataset_release": release,
        "split_id": split_id,
        "preprocessor_id": preprocessor_id,
        "status": "passed" if not failed else "failed",
        "summary": {"passed": len(checks) - len(failed), "failed": len(failed)},
        "failed_checks": failed,
        "checks": checks,
    }


def _load_spec(project_root: Path, preprocessor_id: str) -> tuple[dict[str, Any], Path]:
    config_name = PREPROCESSOR_CONFIGS.get(preprocessor_id)
    if config_name is None:
        supported = ", ".join(sorted(SUPPORTED_PREPROCESSOR_IDS))
        raise ValueError(f"supported AHS preprocessors are: {supported}")
    path = project_root / "configs" / "preprocessing" / config_name
    with path.open("rb") as handle:
        return tomllib.load(handle), path


def _candidate_features(spec: dict[str, Any]) -> tuple[tuple[str, str, str], ...]:
    include_derived = bool(spec.get("include_derived_features", False))
    return combined_feature_map(include_derived)


def _validate_spec(
    spec: dict[str, Any], release: str, split_id: str, preprocessor_id: str
) -> None:
    if preprocessor_id not in SUPPORTED_PREPROCESSOR_IDS:
        raise ValueError(f"unsupported AHS preprocessor: {preprocessor_id!r}")
    if preprocessor_id == PREPROCESSOR_ID and spec.get("include_derived_features"):
        raise ValueError("ahs-training-fold-v1 must not include derived features")
    if (
        preprocessor_id == FEATURE_ENGINEERING_PREPROCESSOR_ID
        and not spec.get("include_derived_features")
    ):
        raise ValueError("ahs-feature-engineering-v1 requires derived features")
    if (
        spec["preprocessor_id"] != preprocessor_id
        or spec["dataset_release"] != release
        or spec["split_id"] != split_id
        or spec["task_id"] != TASK_ID
    ):
        raise ValueError("AHS preprocessing specification does not match the request")
    if spec["fit_split"] != "training":
        raise ValueError("AHS preprocessing must fit on the training split only")
    if spec["numeric_imputer"] != "median":
        raise ValueError("unsupported numeric imputer")
    if spec["numeric_scaler"] != "standard_population":
        raise ValueError("unsupported numeric scaler")
    if spec["categorical_encoder"] != "one_hot_with_reserved_missing_and_unknown":
        raise ValueError("unsupported categorical encoder")
    if not 0 <= float(spec["max_training_missing_fraction"]) <= 1:
        raise ValueError("invalid training missingness limit")
    if (
        float(spec["high_cost_quantile"]) != 0.8
        or spec["high_cost_quantile_method"] != "nearest_rank"
        or spec["high_cost_comparison"] != "greater_than_or_equal"
    ):
        raise ValueError("AHS high-cost policy must be training top 20 percent")
    if spec["target_imputation"] != "prohibited" or spec["target_clipping"] != "prohibited":
        raise ValueError("AHS preprocessing must not impute or clip targets")
    if spec["distribution"] != "local-analysis-only":
        raise ValueError("AHS preprocessing remains local-analysis-only")


def _load_inputs(project_root: Path, release: str, split_id: str) -> dict[str, Any]:
    release_dir = project_root / "data" / "processed" / "releases" / release
    split_dir = project_root / "data" / "processed" / "splits" / release / split_id
    release_manifest_path = release_dir / "manifest.json"
    split_manifest_path = split_dir / "split_manifest.json"
    release_manifest = json.loads(release_manifest_path.read_text(encoding="utf-8"))
    split_manifest = json.loads(split_manifest_path.read_text(encoding="utf-8"))
    if (
        release_manifest.get("dataset_release") != DATASET_RELEASE
        or release_manifest.get("task_ids") != [TASK_ID]
        or release_manifest.get("modeling_view") != "ahs_only_separate_from_rhfs"
    ):
        raise ValueError("preprocessing source is not the isolated approved AHS release")
    if (
        split_manifest.get("dataset_release") != release
        or split_manifest.get("split_id") != split_id
        or split_manifest.get("task_id") != TASK_ID
        or split_manifest.get("distribution") != "local-analysis-only"
    ):
        raise ValueError("preprocessing source is not the frozen AHS split")

    snapshot_path = release_dir / "property_period_snapshot.csv"
    label_path = release_dir / "property_period_label.csv"
    assignment_path = split_dir / "split_assignment.csv"
    expected_sources = {
        "release_manifest.json": sha256_file(release_manifest_path),
        "property_period_snapshot.csv": sha256_file(snapshot_path),
        "property_period_label.csv": sha256_file(label_path),
        "split_manifest.json": sha256_file(split_manifest_path),
        "split_assignment.csv": sha256_file(assignment_path),
    }
    if expected_sources["property_period_snapshot.csv"] != release_manifest[
        "output_sha256"
    ].get("property_period_snapshot.csv"):
        raise ValueError("AHS snapshot checksum drift")
    if expected_sources["property_period_label.csv"] != release_manifest[
        "output_sha256"
    ].get("property_period_label.csv"):
        raise ValueError("AHS label checksum drift")
    if expected_sources["split_assignment.csv"] != split_manifest["output_sha256"].get(
        "split_assignment.csv"
    ):
        raise ValueError("AHS split assignment checksum drift")
    if split_manifest.get("source_release_manifest_sha256") != expected_sources[
        "release_manifest.json"
    ]:
        raise ValueError("AHS split no longer points to the current release manifest")

    assignments = _read_keyed_csv(assignment_path, "snapshot_id")
    labels = _read_keyed_csv(label_path, "snapshot_id")
    if set(assignments) != set(labels):
        raise ValueError("AHS split and label snapshot sets differ")
    if {row["split_name"] for row in assignments.values()} != {
        "training",
        "validation",
        "test",
    }:
        raise ValueError("AHS preprocessing requires all three frozen splits")
    if any(row["task_id"] != TASK_ID for row in labels.values()):
        raise ValueError("AHS labels contain an unexpected task")
    return {
        "release_dir": release_dir,
        "split_dir": split_dir,
        "snapshot_path": snapshot_path,
        "label_path": label_path,
        "assignment_path": assignment_path,
        "assignments": assignments,
        "labels": labels,
        "source_sha256": expected_sources,
    }


def _fit_training_contract(inputs: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    feature_map = _candidate_features(spec)
    training_ids = {
        snapshot_id
        for snapshot_id, row in inputs["assignments"].items()
        if row["split_name"] == spec["fit_split"]
    }
    if not training_ids:
        raise ValueError("AHS preprocessing has no training rows")
    values: dict[str, list[float]] = {
        name: [] for name, _, kind in feature_map if kind == "number"
    }
    categories: dict[str, set[str]] = {
        name: set() for name, _, kind in feature_map if kind == "code"
    }
    missing_counts = {name: 0 for name, _, _ in feature_map}
    seen_training_ids: set[str] = set()
    with inputs["snapshot_path"].open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            snapshot_id = row["snapshot_id"]
            if snapshot_id not in training_ids:
                continue
            seen_training_ids.add(snapshot_id)
            snapshot = enrich_snapshot(row) if spec.get("include_derived_features") else row
            for name, _, kind in feature_map:
                raw = snapshot[name]
                if raw == "":
                    missing_counts[name] += 1
                elif kind == "number":
                    values[name].append(_finite_float(raw, name))
                else:
                    categories[name].add(raw)
    if seen_training_ids != training_ids:
        raise ValueError("training split references missing AHS snapshots")

    max_missing = float(spec["max_training_missing_fraction"])
    parameters: list[dict[str, Any]] = []
    output_columns: list[str] = []
    for name, source, kind in feature_map:
        missing_count = missing_counts[name]
        missing_fraction = missing_count / len(training_ids)
        included = missing_fraction <= max_missing
        parameter: dict[str, Any] = {
            "feature_name": name,
            "source_field": source,
            "source_type": kind,
            "fit_nonmissing_rows": len(training_ids) - missing_count,
            "fit_missing_rows": missing_count,
            "fit_missing_fraction": missing_fraction,
            "max_training_missing_fraction": max_missing,
            "value_feature_included": included,
            "value_exclusion_reason": None
            if included
            else "training_missing_fraction_above_limit",
            "missing_indicator_column": f"{name}__is_missing",
        }
        if kind == "number":
            if included and not values[name]:
                raise ValueError(f"included numeric feature has no training values: {name}")
            if included:
                median = _median(values[name])
                fitted_values = values[name] + [median] * missing_count
                mean = sum(fitted_values) / len(fitted_values)
                variance = sum((value - mean) ** 2 for value in fitted_values) / len(
                    fitted_values
                )
                scale = math.sqrt(variance) or 1.0
                value_column = f"{name}__standardized"
                parameter.update(
                    {
                        "imputer": {"strategy": "median", "fill_value": median},
                        "scaler": {
                            "strategy": "standard_population",
                            "mean_after_imputation": mean,
                            "scale": scale,
                            "zero_variance_scale_replaced_with_one": variance == 0,
                        },
                        "value_output_column": value_column,
                    }
                )
                output_columns.append(value_column)
        else:
            learned_categories = sorted(categories[name])
            if included:
                category_columns = [
                    f"{name}__category_{index:03d}"
                    for index in range(len(learned_categories))
                ]
                missing_column = f"{name}__category_missing"
                unknown_column = f"{name}__category_unknown"
                parameter["encoder"] = {
                    "strategy": "one_hot",
                    "training_categories": learned_categories,
                    "category_output_columns": category_columns,
                    "reserved_missing_token": spec["categorical_missing_token"],
                    "reserved_missing_output_column": missing_column,
                    "reserved_unknown_token": spec["categorical_unknown_token"],
                    "reserved_unknown_output_column": unknown_column,
                }
                output_columns.extend(category_columns)
                output_columns.extend([missing_column, unknown_column])
        output_columns.append(parameter["missing_indicator_column"])
        parameters.append(parameter)

    training_targets = [
        _target_decimal(inputs["labels"][snapshot_id]) for snapshot_id in training_ids
    ]
    threshold = _nearest_rank(training_targets, float(spec["high_cost_quantile"]))
    return {
        "fit_row_count": len(training_ids),
        "fit_snapshot_ids_sha256": _snapshot_id_digest(training_ids),
        "feature_parameters": parameters,
        "output_columns": output_columns,
        "high_cost_threshold": _decimal_text(threshold),
    }


def _artifact(
    spec: dict[str, Any],
    config_path: Path,
    inputs: dict[str, Any],
    fit: dict[str, Any],
) -> dict[str, Any]:
    return {
        "preprocessor_id": spec["preprocessor_id"],
        "preprocessing_contract_version": spec["preprocessing_contract_version"],
        "dataset_release": spec["dataset_release"],
        "split_id": spec["split_id"],
        "task_id": spec["task_id"],
        "fit_split": spec["fit_split"],
        "fit_row_count": fit["fit_row_count"],
        "fit_snapshot_ids_sha256": fit["fit_snapshot_ids_sha256"],
        "source_sha256": inputs["source_sha256"],
        "config_sha256": sha256_file(config_path),
        "feature_policy": {
            "candidate_feature_count": len(_candidate_features(spec)),
            "include_derived_features": bool(spec.get("include_derived_features", False)),
            "missing_indicators_for_all_candidates": True,
            "value_exclusion_rule": "training_missing_fraction_above_limit",
            "max_training_missing_fraction": float(
                spec["max_training_missing_fraction"]
            ),
            "validation_or_test_statistics_used": False,
        },
        "feature_parameters": fit["feature_parameters"],
        "feature_matrix_columns": ["snapshot_id", *fit["output_columns"]],
        "target_metadata_columns": TARGET_FIELDS,
        "target_policy": {
            "imputation": spec["target_imputation"],
            "clipping": spec["target_clipping"],
            "cap_sensitivity_metadata_preserved": True,
        },
        "high_cost_policy": {
            "threshold_version": HIGH_COST_THRESHOLD_VERSION,
            "fit_split": spec["fit_split"],
            "fit_label_rows": fit["fit_row_count"],
            "quantile": float(spec["high_cost_quantile"]),
            "quantile_method": spec["high_cost_quantile_method"],
            "comparison": spec["high_cost_comparison"],
            "threshold_amount_local_nominal": fit["high_cost_threshold"],
            "ties_at_threshold_may_exceed_twenty_percent": True,
        },
        "distribution": spec["distribution"],
        "model_fitted": False,
    }


def _write_outputs(
    inputs: dict[str, Any],
    fit: dict[str, Any],
    spec: dict[str, Any],
    feature_path: Path,
    target_path: Path,
) -> tuple[int, int]:
    feature_rows = _iter_transformed_rows(inputs, fit, spec)
    feature_count = write_csv(
        feature_path, ["snapshot_id", *fit["output_columns"]], feature_rows
    )
    target_count = write_csv(
        target_path, TARGET_FIELDS, _iter_target_rows(inputs, fit)
    )
    return feature_count, target_count


def _iter_transformed_rows(
    inputs: dict[str, Any], fit: dict[str, Any], spec: dict[str, Any]
) -> Iterator[dict[str, Any]]:
    feature_map = _candidate_features(spec)
    parameters = {item["feature_name"]: item for item in fit["feature_parameters"]}
    seen: set[str] = set()
    with inputs["snapshot_path"].open("r", encoding="utf-8", newline="") as handle:
        for snapshot in csv.DictReader(handle):
            snapshot_id = snapshot["snapshot_id"]
            if snapshot_id not in inputs["assignments"]:
                continue
            seen.add(snapshot_id)
            working = enrich_snapshot(snapshot) if spec.get("include_derived_features") else snapshot
            output: dict[str, Any] = {"snapshot_id": snapshot_id}
            for name, _, kind in feature_map:
                raw = working[name]
                parameter = parameters[name]
                is_missing = raw == ""
                if parameter["value_feature_included"] and kind == "number":
                    value = (
                        parameter["imputer"]["fill_value"]
                        if is_missing
                        else _finite_float(raw, name)
                    )
                    output[parameter["value_output_column"]] = _float_text(
                        (value - parameter["scaler"]["mean_after_imputation"])
                        / parameter["scaler"]["scale"]
                    )
                elif parameter["value_feature_included"]:
                    encoder = parameter["encoder"]
                    category_index = {
                        category: index
                        for index, category in enumerate(encoder["training_categories"])
                    }
                    selected = category_index.get(raw) if not is_missing else None
                    for index, column in enumerate(encoder["category_output_columns"]):
                        output[column] = int(index == selected)
                    output[encoder["reserved_missing_output_column"]] = int(is_missing)
                    output[encoder["reserved_unknown_output_column"]] = int(
                        not is_missing and raw not in category_index
                    )
                output[parameter["missing_indicator_column"]] = int(is_missing)
            yield output
    if seen != set(inputs["assignments"]):
        raise ValueError("AHS snapshot table does not cover the frozen split")


def _iter_target_rows(
    inputs: dict[str, Any], fit: dict[str, Any]
) -> Iterator[dict[str, Any]]:
    threshold = Decimal(fit["high_cost_threshold"])
    with inputs["snapshot_path"].open("r", encoding="utf-8", newline="") as handle:
        for snapshot in csv.DictReader(handle):
            snapshot_id = snapshot["snapshot_id"]
            assignment = inputs["assignments"].get(snapshot_id)
            if assignment is None:
                continue
            label = inputs["labels"][snapshot_id]
            yield _target_output_row(assignment, label, threshold)


def _target_output_row(
    assignment: dict[str, str], label: dict[str, str], threshold: Decimal
) -> dict[str, Any]:
    target = _target_decimal(label)
    if assignment["feature_wave_year"] != label["feature_wave_year"]:
        raise ValueError("AHS feature-wave metadata differs between split and label")
    if assignment["label_wave_year"] != label["label_wave_year"]:
        raise ValueError("AHS label-wave metadata differs between split and label")
    if assignment["task_id"] != label["task_id"]:
        raise ValueError("AHS task metadata differs between split and label")
    return {
        "snapshot_id": label["snapshot_id"],
        "split_name": assignment["split_name"],
        "task_id": label["task_id"],
        "target_amount_local_nominal": label["target_amount_local_nominal"],
        "target_currency": label["target_currency"],
        "feature_wave_year": label["feature_wave_year"],
        "label_wave_year": label["label_wave_year"],
        "source_response_maximum_usd": label["source_response_maximum_usd"],
        "response_cap_regime": assignment["response_cap_regime"],
        "include_in_primary_metrics": assignment["include_in_primary_metrics"],
        "include_in_pre_2023_cap_sensitivity": assignment[
            "include_in_pre_2023_cap_sensitivity"
        ],
        "high_cost_threshold_version": HIGH_COST_THRESHOLD_VERSION,
        "is_high_cost": target >= threshold,
        "target_was_imputed": False,
        "target_was_clipped": False,
    }


def _audit_feature_matrix(
    inputs: dict[str, Any], fit: dict[str, Any], spec: dict[str, Any], path: Path
) -> tuple[int, int]:
    if not path.is_file():
        return 1, 0
    expected_rows = _iter_transformed_rows(inputs, fit, spec)
    failures = 0
    rows = 0
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != ["snapshot_id", *fit["output_columns"]]:
            failures += 1
        for expected, actual in _zip_exact(expected_rows, reader):
            rows += 1
            expected_text = {key: _csv_text(value) for key, value in expected.items()}
            if expected_text != actual:
                failures += 1
    return failures, rows


def _audit_targets(
    inputs: dict[str, Any], fit: dict[str, Any], path: Path
) -> tuple[int, int]:
    if not path.is_file():
        return 1, 0
    expected_rows = _iter_target_rows(inputs, fit)
    failures = 0
    rows = 0
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != TARGET_FIELDS:
            failures += 1
        for expected, actual in _zip_exact(expected_rows, reader):
            rows += 1
            expected_text = {key: _csv_text(value) for key, value in expected.items()}
            if expected_text != actual:
                failures += 1
    return failures, rows


def _zip_exact(
    expected: Iterator[dict[str, Any]], actual: Iterator[dict[str, str]]
) -> Iterator[tuple[dict[str, Any], dict[str, str]]]:
    sentinel = object()
    while True:
        left = next(expected, sentinel)
        right = next(actual, sentinel)
        if left is sentinel and right is sentinel:
            return
        if left is sentinel or right is sentinel:
            yield ({}, {})
            return
        yield left, right


def _read_keyed_csv(path: Path, key: str) -> dict[str, dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    keyed = {row[key]: row for row in rows}
    if len(keyed) != len(rows) or "" in keyed:
        raise ValueError(f"duplicate or empty {key} in {path.name}")
    return keyed


def _finite_float(raw: str, feature_name: str) -> float:
    try:
        value = float(raw)
    except ValueError as exc:
        raise ValueError(f"non-numeric AHS feature {feature_name}: {raw!r}") from exc
    if not math.isfinite(value):
        raise ValueError(f"non-finite AHS feature {feature_name}")
    return value


def _target_decimal(label: dict[str, str]) -> Decimal:
    raw = label["target_amount_local_nominal"]
    if raw == "":
        raise ValueError("AHS target is missing; target imputation is prohibited")
    try:
        target = Decimal(raw)
    except InvalidOperation as exc:
        raise ValueError(f"invalid AHS target: {raw!r}") from exc
    if not target.is_finite() or target < 0:
        raise ValueError(f"invalid AHS target: {raw!r}")
    return target


def _median(values: list[float]) -> float:
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2


def _nearest_rank(values: list[Decimal], quantile: float) -> Decimal:
    if not values:
        raise ValueError("cannot fit a high-cost threshold without training labels")
    rank = max(1, math.ceil(quantile * len(values)))
    return sorted(values)[rank - 1]


def _snapshot_id_digest(snapshot_ids: Any) -> str:
    material = "".join(f"{snapshot_id}\n" for snapshot_id in sorted(snapshot_ids))
    return sha256(material.encode("utf-8")).hexdigest()


def _decimal_text(value: Decimal) -> str:
    return format(value, "f")


def _float_text(value: float) -> str:
    return format(value, ".17g")


def _csv_text(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return ""
    return str(value)


def _check(checks: list[dict[str, Any]], check_id: str, passed: bool, evidence: Any) -> None:
    checks.append(
        {
            "check_id": check_id,
            "status": "passed" if passed else "failed",
            "evidence": evidence,
        }
    )
