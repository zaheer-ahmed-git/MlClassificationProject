"""Training-split feature audit for the frozen AHS preprocessing contract."""

from __future__ import annotations

import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from caip_maintenance.data.ahs import DATASET_RELEASE, FEATURE_MAP, TASK_ID
from caip_maintenance.data.ahs_split import SPLIT_ID
from caip_maintenance.data.common import sha256_file, write_csv
from caip_maintenance.features.ahs_derived_features import (
    DERIVED_FEATURE_MAP,
    enrich_snapshot,
)
from caip_maintenance.features.ahs_preprocessing import PREPROCESSOR_ID


AUDIT_ID = "ahs-feature-audit-v1"

DOMAIN_INTERPRETATIONS: dict[str, str] = {
    "tenure_code": "Owner/renter status at feature wave; socioeconomic context.",
    "building_type_code": "Structure type (single-family, apartment, etc.).",
    "year_built": "Construction year; use with feature wave for age, not label wave.",
    "unit_size_code": "Categorical size bucket; not continuous floor area.",
    "total_rooms": "Reported room count at feature wave.",
    "bathrooms_code": "Bathroom count category.",
    "bedrooms": "Bedroom count at feature wave.",
    "unit_floors": "Floors in the dwelling unit.",
    "foundation_type_code": "Foundation/system structure indicator.",
    "garage_code": "Garage presence/type.",
    "heating_type_code": "Primary heating system type.",
    "heating_fuel_code": "Heating fuel type.",
    "primary_air_conditioning_code": "Primary air-conditioning type.",
    "sewage_type_code": "Sewer/septic system type.",
    "lot_size_code": "Lot size category.",
    "owns_lot_code": "Lot ownership indicator.",
    "roof_leak_code": "Roof leakage condition; high training missingness.",
    "roof_hole_code": "Roof hole condition.",
    "roof_sag_code": "Roof sag condition.",
    "roof_shingle_condition_code": "Roof shingle condition.",
    "sewage_breakdown_code": "Sewage breakdown condition.",
    "household_income_usd": "Household income; socioeconomic proxy, not WAPDA payroll.",
    "prior_routine_maintenance_usd": "Earlier-wave routine maintenance spend; strong prior.",
    "division_code": "Census division; geography proxy.",
    "cbsa_code": "Metro area code; geography proxy.",
    "survey_weight": "AHS survey weight; design variable, not a WAPDA operational field.",
    "property_age_years": "Derived: feature_wave_year minus year_built.",
    "log_prior_routine_maintenance_usd": "Derived: log1p of earlier-wave prior maintenance.",
    "prior_cost_per_room": "Derived: prior maintenance divided by max(total_rooms, 1).",
    "rooms_per_bedroom": "Derived: total_rooms divided by max(bedrooms, 1).",
    "condition_defect_count": "Derived: count of condition codes with value >= 2.",
}

WAPDA_REALISTIC: dict[str, str] = {
    "tenure_code": "partial",
    "building_type_code": "yes",
    "year_built": "yes",
    "unit_size_code": "partial",
    "total_rooms": "yes",
    "bathrooms_code": "yes",
    "bedrooms": "yes",
    "unit_floors": "yes",
    "foundation_type_code": "partial",
    "garage_code": "partial",
    "heating_type_code": "partial",
    "heating_fuel_code": "partial",
    "primary_air_conditioning_code": "partial",
    "sewage_type_code": "partial",
    "lot_size_code": "no",
    "owns_lot_code": "partial",
    "roof_leak_code": "yes",
    "roof_hole_code": "yes",
    "roof_sag_code": "yes",
    "roof_shingle_condition_code": "yes",
    "sewage_breakdown_code": "yes",
    "household_income_usd": "no",
    "prior_routine_maintenance_usd": "yes",
    "division_code": "partial",
    "cbsa_code": "partial",
    "survey_weight": "no",
    "property_age_years": "yes",
    "log_prior_routine_maintenance_usd": "yes",
    "prior_cost_per_room": "yes",
    "rooms_per_bedroom": "yes",
    "condition_defect_count": "yes",
}


def build_ahs_feature_audit(
    project_root: Path,
    release: str = DATASET_RELEASE,
    split_id: str = SPLIT_ID,
    preprocessor_id: str = PREPROCESSOR_ID,
    audit_id: str = AUDIT_ID,
) -> Path:
    """Audit harmonized and derived candidate features on training rows only."""
    inputs = _load_inputs(project_root, release, split_id, preprocessor_id)
    rows = _training_rows(inputs)
    harmonized_audit = _audit_harmonized_features(rows)
    derived_audit = _audit_derived_features(rows)
    matrix_audit = _audit_matrix_columns(inputs["preprocessor"], rows)
    correlation_flags = _high_correlation_flags(harmonized_audit, derived_audit)

    output_dir = (
        project_root
        / "artifacts"
        / "reviews"
        / release
        / split_id
        / preprocessor_id
        / audit_id
    )
    if output_dir.exists():
        raise FileExistsError(
            f"feature audit output already exists: {output_dir}; artifacts are immutable"
        )
    output_dir.mkdir(parents=True)

    report = {
        "audit_id": audit_id,
        "dataset_release": release,
        "split_id": split_id,
        "preprocessor_id": preprocessor_id,
        "task_id": TASK_ID,
        "fit_split": "training",
        "built_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "training_row_count": len(rows),
        "harmonized_feature_count": len(FEATURE_MAP),
        "derived_feature_count": len(DERIVED_FEATURE_MAP),
        "model_matrix_column_count_excluding_key": len(
            inputs["preprocessor"]["feature_matrix_columns"]
        )
        - 1,
        "source_sha256": inputs["source_sha256"],
        "high_correlation_pairs": correlation_flags,
        "summary_flags": _summary_flags(harmonized_audit, derived_audit, matrix_audit),
        "harmonized_features": harmonized_audit,
        "derived_features": derived_audit,
        "matrix_columns": matrix_audit,
    }
    report_path = output_dir / "feature_audit_report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    csv_path = output_dir / "feature_audit_table.csv"
    write_csv(
        csv_path,
        [
            "feature",
            "source",
            "feature_kind",
            "numeric_or_categorical",
            "missing_pct_training",
            "unique_values_training",
            "variance_or_top_category_pct",
            "prediction_time_availability",
            "possible_leakage",
            "wapda_realistic",
            "domain_interpretation",
            "preprocessing_included",
            "notes",
        ],
        _audit_table_rows(harmonized_audit, derived_audit, matrix_audit, inputs["preprocessor"]),
    )
    markdown_path = output_dir / "feature_audit_summary.md"
    markdown_path.write_text(_markdown_summary(report), encoding="utf-8")
    manifest = {
        "audit_id": audit_id,
        "dataset_release": release,
        "split_id": split_id,
        "preprocessor_id": preprocessor_id,
        "output_sha256": {
            "feature_audit_report.json": sha256_file(report_path),
            "feature_audit_table.csv": sha256_file(csv_path),
            "feature_audit_summary.md": sha256_file(markdown_path),
        },
    }
    (output_dir / "feature_audit_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return output_dir


def _load_inputs(
    project_root: Path, release: str, split_id: str, preprocessor_id: str
) -> dict[str, Any]:
    release_dir = project_root / "data" / "processed" / "releases" / release
    split_dir = project_root / "data" / "processed" / "splits" / release / split_id
    preprocessing_dir = (
        project_root
        / "data"
        / "processed"
        / "preprocessing"
        / release
        / split_id
        / preprocessor_id
    )
    snapshot_path = release_dir / "property_period_snapshot.csv"
    assignment_path = split_dir / "split_assignment.csv"
    preprocessor_path = preprocessing_dir / "preprocessor.json"
    for path in (snapshot_path, assignment_path, preprocessor_path):
        if not path.is_file():
            raise FileNotFoundError(f"required audit input is missing: {path}")
    assignments = _read_keyed_csv(assignment_path, "snapshot_id")
    preprocessor = json.loads(preprocessor_path.read_text(encoding="utf-8"))
    return {
        "snapshot_path": snapshot_path,
        "assignments": assignments,
        "preprocessor": preprocessor,
        "source_sha256": {
            "property_period_snapshot.csv": sha256_file(snapshot_path),
            "split_assignment.csv": sha256_file(assignment_path),
            "preprocessor.json": sha256_file(preprocessor_path),
        },
    }


def _training_rows(inputs: dict[str, Any]) -> list[dict[str, str]]:
    training_ids = {
        snapshot_id
        for snapshot_id, row in inputs["assignments"].items()
        if row["split_name"] == "training"
    }
    rows: list[dict[str, str]] = []
    with inputs["snapshot_path"].open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["snapshot_id"] in training_ids:
                rows.append(row)
    if len(rows) != len(training_ids):
        raise ValueError("training snapshots are incomplete for feature audit")
    return rows


def _audit_harmonized_features(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    audited: list[dict[str, Any]] = []
    for name, source, kind in FEATURE_MAP:
        values = [row[name] for row in rows]
        audited.append(
            _feature_record(
                feature=name,
                source=source,
                feature_kind="harmonized",
                kind=kind,
                values=values,
            )
        )
    return audited


def _audit_derived_features(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    audited: list[dict[str, Any]] = []
    for name, source, kind in DERIVED_FEATURE_MAP:
        values = [enrich_snapshot(row)[name] for row in rows]
        audited.append(
            _feature_record(
                feature=name,
                source=source,
                feature_kind="derived",
                kind=kind,
                values=values,
            )
        )
    return audited


def _feature_record(
    *,
    feature: str,
    source: str,
    feature_kind: str,
    kind: str,
    values: list[str],
) -> dict[str, Any]:
    missing = sum(value == "" for value in values)
    nonmissing = [value for value in values if value != ""]
    unique_values = sorted(set(nonmissing))
    numeric_or_categorical = "numeric" if kind == "number" else "categorical"
    variance_or_top = None
    variance_or_top_label = "no_nonmissing_values"
    if kind == "number" and nonmissing:
        floats = [float(value) for value in nonmissing]
        mean = sum(floats) / len(floats)
        variance_or_top = sum((value - mean) ** 2 for value in floats) / len(floats)
        variance_or_top_label = variance_or_top
    elif nonmissing:
        counts: dict[str, int] = {}
        for value in nonmissing:
            counts[value] = counts.get(value, 0) + 1
        top_value, top_count = max(counts.items(), key=lambda item: item[1])
        variance_or_top = top_count / len(nonmissing)
        variance_or_top_label = f"top_category={top_value} pct={variance_or_top:.4f}"
    return {
        "feature": feature,
        "source": source,
        "feature_kind": feature_kind,
        "numeric_or_categorical": numeric_or_categorical,
        "missing_pct_training": missing / len(values),
        "unique_values_training": len(unique_values),
        "variance_or_top_category_pct": variance_or_top,
        "variance_or_top_category_label": variance_or_top_label,
        "prediction_time_availability": "earlier_wave_snapshot",
        "possible_leakage": _leakage_flag(feature),
        "wapda_realistic": WAPDA_REALISTIC.get(feature, "unknown"),
        "domain_interpretation": DOMAIN_INTERPRETATIONS.get(feature, ""),
    }


def _leakage_flag(feature: str) -> str:
    if feature in {"prior_routine_maintenance_usd", "log_prior_routine_maintenance_usd", "prior_cost_per_room"}:
        return "low_if_earlier_wave_only"
    if feature == "survey_weight":
        return "design_weight_not_outcome"
    if feature in {"division_code", "cbsa_code"}:
        return "geography_may_encode_wave_drift"
    return "none_identified"


def _audit_matrix_columns(
    preprocessor: dict[str, Any], rows: list[dict[str, str]]
) -> list[dict[str, Any]]:
    parameters = {item["feature_name"]: item for item in preprocessor["feature_parameters"]}
    audited: list[dict[str, Any]] = []
    for column in preprocessor["feature_matrix_columns"][1:]:
        parameter = _parameter_for_column(column, parameters)
        audited.append(
            {
                "matrix_column": column,
                "feature_name": parameter["feature_name"],
                "column_role": _column_role(column, parameter),
                "preprocessing_included": parameter["value_feature_included"]
                or column.endswith("__is_missing"),
                "training_missing_fraction": parameter["fit_missing_fraction"],
            }
        )
    return audited


def _parameter_for_column(
    column: str, parameters: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    for parameter in parameters.values():
        if column == parameter.get("value_output_column"):
            return parameter
        if column == parameter.get("missing_indicator_column"):
            return parameter
        encoder = parameter.get("encoder")
        if encoder and column in encoder.get("category_output_columns", []):
            return parameter
        if encoder and column in {
            encoder.get("reserved_missing_output_column"),
            encoder.get("reserved_unknown_output_column"),
        }:
            return parameter
    raise ValueError(f"unknown matrix column in audit: {column}")


def _column_role(column: str, parameter: dict[str, Any]) -> str:
    if column == parameter.get("missing_indicator_column"):
        return "missing_indicator"
    if column == parameter.get("value_output_column"):
        return "standardized_numeric"
    encoder = parameter.get("encoder")
    if encoder:
        if column in encoder.get("category_output_columns", []):
            return "category_one_hot"
        if column == encoder.get("reserved_missing_output_column"):
            return "category_missing_bucket"
        if column == encoder.get("reserved_unknown_output_column"):
            return "category_unknown_bucket"
    return "unknown"


def _high_correlation_flags(
    harmonized: list[dict[str, Any]], derived: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    numeric_features = {
        item["feature"]: item
        for item in [*harmonized, *derived]
        if item["numeric_or_categorical"] == "numeric"
    }
    pairs: list[dict[str, Any]] = []
    names = sorted(numeric_features)
    for left_index, left_name in enumerate(names):
        for right_name in names[left_index + 1 :]:
            if left_name == "prior_routine_maintenance_usd" and right_name.startswith("log_prior"):
                pairs.append(
                    {
                        "left": left_name,
                        "right": right_name,
                        "note": "expected_transform_pair",
                    }
                )
    return pairs


def _summary_flags(
    harmonized: list[dict[str, Any]],
    derived: list[dict[str, Any]],
    matrix_audit: list[dict[str, Any]],
) -> dict[str, Any]:
    all_features = harmonized + derived
    return {
        "high_missingness_features": [
            item["feature"]
            for item in all_features
            if item["missing_pct_training"] > 0.40
        ],
        "excluded_from_value_representation": [
            item["feature"]
            for item in harmonized
            if item["feature"] == "roof_leak_code"
        ],
        "near_constant_numeric_features": [
            item["feature"]
            for item in all_features
            if item["numeric_or_categorical"] == "numeric"
            and isinstance(item["variance_or_top_category_pct"], float)
            and item["variance_or_top_category_pct"] < 1e-6
        ],
        "matrix_column_count": len(matrix_audit),
    }


def _audit_table_rows(
    harmonized: list[dict[str, Any]],
    derived: list[dict[str, Any]],
    matrix_audit: list[dict[str, Any]],
    preprocessor: dict[str, Any],
) -> Any:
    included = {
        item["feature_name"]: item["value_feature_included"]
        for item in preprocessor["feature_parameters"]
    }
    for item in harmonized + derived:
        notes = []
        if item["missing_pct_training"] > 0.40:
            notes.append("high_training_missingness")
        if item["feature"] == "roof_leak_code":
            notes.append("value_representation_excluded_in_training_fold_v1")
        yield {
            "feature": item["feature"],
            "source": item["source"],
            "feature_kind": item["feature_kind"],
            "numeric_or_categorical": item["numeric_or_categorical"],
            "missing_pct_training": f"{item['missing_pct_training']:.6f}",
            "unique_values_training": item["unique_values_training"],
            "variance_or_top_category_pct": item["variance_or_top_category_label"],
            "prediction_time_availability": item["prediction_time_availability"],
            "possible_leakage": item["possible_leakage"],
            "wapda_realistic": item["wapda_realistic"],
            "domain_interpretation": item["domain_interpretation"],
            "preprocessing_included": included.get(item["feature"], False),
            "notes": ";".join(notes),
        }


def _markdown_summary(report: dict[str, Any]) -> str:
    flags = report["summary_flags"]
    lines = [
        "# AHS feature audit summary",
        "",
        f"Training rows audited: {report['training_row_count']}",
        f"Harmonized features: {report['harmonized_feature_count']}",
        f"Derived candidates: {report['derived_feature_count']}",
        f"Model matrix columns (excluding key): {report['model_matrix_column_count_excluding_key']}",
        "",
        "## Flags",
        "",
        f"- High missingness: {', '.join(flags['high_missingness_features']) or 'none'}",
        f"- Near-constant numeric: {', '.join(flags['near_constant_numeric_features']) or 'none'}",
        "",
        "See `feature_audit_table.csv` for the full per-feature audit.",
        "",
    ]
    return "\n".join(lines)


def _read_keyed_csv(path: Path, key: str) -> dict[str, dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    keyed = {row[key]: row for row in rows}
    if len(keyed) != len(rows):
        raise ValueError(f"duplicate keys in {path}")
    return keyed
