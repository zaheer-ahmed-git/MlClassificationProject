"""Build the separate AHS future routine-maintenance proxy release."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
import io
import json
from pathlib import Path
from typing import Any
import zipfile

from .ahs_gate import (
    CORE_FEATURE_FIELDS,
    MISSING_CODES,
    SOURCE_ID,
    SOURCE_RELEASE,
    WAVE_ARCHIVES,
    clean_ahs_value,
    eligible_label,
    load_passed_gate,
)
from .common import asset_token, row_digest, sha256_file, stable_id, write_csv


DATASET_RELEASE = "public-corpus-v0.2.0-ahs"
TASK_ID = "future_routine_cost_proxy_v1"
TRANSFORM_VERSION = "ahs_adjacent_wave_v1"

FEATURE_MAP: tuple[tuple[str, str, str], ...] = (
    ("tenure_code", "TENURE", "code"),
    ("building_type_code", "BLD", "code"),
    ("year_built", "YRBUILT", "number"),
    ("unit_size_code", "UNITSIZE", "code"),
    ("total_rooms", "TOTROOMS", "number"),
    ("bathrooms_code", "BATHROOMS", "code"),
    ("bedrooms", "BEDROOMS", "number"),
    ("unit_floors", "UNITFLOORS", "number"),
    ("foundation_type_code", "FOUNDTYPE", "code"),
    ("garage_code", "GARAGE", "code"),
    ("heating_type_code", "HEATTYPE", "code"),
    ("heating_fuel_code", "HEATFUEL", "code"),
    ("primary_air_conditioning_code", "ACPRIMARY", "code"),
    ("sewage_type_code", "SEWTYPE", "code"),
    ("lot_size_code", "LOTSIZE", "code"),
    ("owns_lot_code", "OWNLOT", "code"),
    ("roof_leak_code", "LEAKOROOF", "code"),
    ("roof_hole_code", "ROOFHOLE", "code"),
    ("roof_sag_code", "ROOFSAG", "code"),
    ("roof_shingle_condition_code", "ROOFSHIN", "code"),
    ("sewage_breakdown_code", "SEWBREAK", "code"),
    ("household_income_usd", "HINCP", "number"),
    ("prior_routine_maintenance_usd", "MAINTAMT", "number"),
    ("division_code", "DIVISION", "code"),
    ("cbsa_code", "OMB13CBSA", "code"),
    ("survey_weight", "WEIGHT", "number"),
)

DOCUMENT_FILES = tuple(
    name
    for year, archive in WAVE_ARCHIVES.items()
    for name in (
        archive,
        f"{year}_AHS_Mini_Codebook_National.pdf",
        f"{year}_AHS_Definitions.pdf",
        f"{year}_AHS_Historical_Changes.pdf",
        f"{year}_AHS_Items_Booklet.pdf",
    )
) + (
    "AHS_Codebook_Reference.pdf",
    "Sample_Case_History_File_2015_to_2023.pdf",
    "Sample_Case_History_File_2015_to_2023.zip",
)

BRIDGE_FIELDS = [
    "source_id",
    "analytical_asset_id",
    "native_grain",
    "source_asset_token",
    "unit_count",
    "survey_weight",
]
OBSERVATION_FIELDS = [
    "cost_observation_id",
    "analytical_asset_id",
    "source_id",
    "period_start",
    "period_end",
    "amount_local_nominal",
    "currency",
    "cost_category",
    "label_origin",
    "scope_fidelity",
    "capital_included",
    "appliance_separable",
    "coverage_status",
    "zero_valid",
    "operating_expense_reconciliation",
    "source_wave_year",
    "source_response_maximum_usd",
]
SNAPSHOT_BASE_FIELDS = [
    "snapshot_id",
    "analytical_asset_id",
    "source_id",
    "asset_grain",
    "as_of_date",
    "task_mode",
    "source_wave_year",
]
SNAPSHOT_FIELDS = SNAPSHOT_BASE_FIELDS + [
    output
    for output, _, _ in FEATURE_MAP
    for output in (output, f"{output}_missing_reason")
]
LABEL_FIELDS = [
    "snapshot_id",
    "task_id",
    "label_start",
    "label_end",
    "target_amount_local_nominal",
    "target_currency",
    "target_definition",
    "label_origin",
    "scope_fidelity",
    "coverage_complete",
    "zero_valid",
    "is_exact_wapda_target",
    "feature_wave_year",
    "label_wave_year",
    "horizon_years",
    "source_response_maximum_usd",
]
LINEAGE_FIELDS = [
    "lineage_id",
    "target_table",
    "target_key",
    "document_id",
    "source_row_locator",
    "source_row_sha256",
    "source_fields_json",
    "transform_version",
    "verification_status",
]


@dataclass(frozen=True)
class SourceRecord:
    row_number: int
    values: dict[str, str]
    projection_sha256: str


@dataclass(frozen=True)
class WaveData:
    features: dict[str, SourceRecord]
    labels: dict[str, SourceRecord]


def harmonize(project_root: Path, release: str = DATASET_RELEASE) -> Path:
    """Build AHS only after a source-hash-bound GO decision exists."""
    if release != DATASET_RELEASE:
        raise ValueError(f"supported AHS release is {DATASET_RELEASE!r}")
    gate = load_passed_gate(project_root)
    raw_dir = project_root / "data" / "raw" / "public" / SOURCE_ID / SOURCE_RELEASE
    output_dir = project_root / "data" / "processed" / "releases" / release
    if output_dir.exists():
        raise FileExistsError(
            f"release already exists: {output_dir}; release directories are immutable"
        )

    wave_data = {
        year: _read_wave(raw_dir / archive)
        for year, archive in WAVE_ARCHIVES.items()
    }
    output_dir.mkdir(parents=True)

    bridges_by_asset: dict[str, dict[str, Any]] = {}
    bridge_lineage_by_asset: dict[str, dict[str, str]] = {}
    observations: list[dict[str, Any]] = []
    snapshots: list[dict[str, Any]] = []
    labels: list[dict[str, Any]] = []
    lineage: list[dict[str, str]] = []
    built_pair_counts: list[dict[str, int]] = []

    years = sorted(WAVE_ARCHIVES)
    for earlier, later in zip(years, years[1:]):
        controls = sorted(
            wave_data[earlier].features.keys() & wave_data[later].labels.keys()
        )
        built_pair_counts.append(
            {"earlier_wave": earlier, "later_wave": later, "eligible_pair_rows": len(controls)}
        )
        earlier_document_id = _document_id(WAVE_ARCHIVES[earlier])
        later_document_id = _document_id(WAVE_ARCHIVES[later])
        for control in controls:
            feature_record = wave_data[earlier].features[control]
            label_record = wave_data[later].labels[control]
            asset_id = asset_token(SOURCE_ID, control)
            snapshot_id = stable_id("snapshot", asset_id, earlier, TASK_ID)
            observation_id = stable_id("cost-observation", asset_id, later, TASK_ID)

            if asset_id not in bridges_by_asset:
                bridges_by_asset[asset_id] = {
                    "source_id": SOURCE_ID,
                    "analytical_asset_id": asset_id,
                    "native_grain": "housing_unit_wave",
                    "source_asset_token": asset_id,
                    "unit_count": "1",
                    "survey_weight": "",
                }
                bridge_lineage_by_asset[asset_id] = _lineage(
                    "source_asset_bridge",
                    asset_id,
                    earlier_document_id,
                    feature_record,
                    ["CONTROL"],
                )

            snapshot: dict[str, Any] = {
                "snapshot_id": snapshot_id,
                "analytical_asset_id": asset_id,
                "source_id": SOURCE_ID,
                "asset_grain": "housing_unit",
                "as_of_date": f"{earlier}-12-31",
                "task_mode": TASK_ID,
                "source_wave_year": earlier,
            }
            for output_name, source_name, value_type in FEATURE_MAP:
                value, reason = _normalized_value(
                    feature_record.values[source_name], value_type
                )
                snapshot[output_name] = value
                snapshot[f"{output_name}_missing_reason"] = reason
            snapshots.append(snapshot)
            lineage.append(
                _lineage(
                    "property_period_snapshot",
                    snapshot_id,
                    earlier_document_id,
                    feature_record,
                    [source for _, source, _ in FEATURE_MAP],
                )
            )

            amount = eligible_label(label_record.values)
            if amount is None:
                raise ValueError("internal AHS eligibility drift while building labels")
            label_origin = (
                "public_survey_source_edited"
                if clean_ahs_value(label_record.values["JMAINTAMT"]) == "1"
                else "public_survey_puf_value"
            )
            response_maximum = "100000" if later == 2023 else "10000"
            observations.append(
                {
                    "cost_observation_id": observation_id,
                    "analytical_asset_id": asset_id,
                    "source_id": SOURCE_ID,
                    "period_start": f"{later}-01-01",
                    "period_end": f"{later}-12-31",
                    "amount_local_nominal": _format_number(amount),
                    "currency": "USD",
                    "cost_category": "routine_maintenance_typical_year",
                    "label_origin": label_origin,
                    "scope_fidelity": "future_biennial_routine_cost_proxy",
                    "capital_included": False,
                    "appliance_separable": True,
                    "coverage_status": "eligible_completed_owner_response",
                    "zero_valid": amount == 0,
                    "operating_expense_reconciliation": "not_testable",
                    "source_wave_year": later,
                    "source_response_maximum_usd": response_maximum,
                }
            )
            label = {
                "snapshot_id": snapshot_id,
                "task_id": TASK_ID,
                "label_start": f"{later}-01-01",
                "label_end": f"{later}-12-31",
                "target_amount_local_nominal": _format_number(amount),
                "target_currency": "USD",
                "target_definition": "AHS later-wave annual routine maintenance cost amount",
                "label_origin": label_origin,
                "scope_fidelity": "future_biennial_routine_cost_proxy",
                "coverage_complete": True,
                "zero_valid": amount == 0,
                "is_exact_wapda_target": False,
                "feature_wave_year": earlier,
                "label_wave_year": later,
                "horizon_years": "2",
                "source_response_maximum_usd": response_maximum,
            }
            labels.append(label)
            lineage.append(
                _lineage(
                    "annual_cost_observation",
                    observation_id,
                    later_document_id,
                    label_record,
                    ["CONTROL", "INTSTATUS", "TENURE", "MAINTAMT", "JMAINTAMT"],
                )
            )
            lineage.append(
                _lineage(
                    "property_period_label",
                    f"{snapshot_id}|{TASK_ID}",
                    later_document_id,
                    label_record,
                    ["CONTROL", "INTSTATUS", "TENURE", "MAINTAMT", "JMAINTAMT"],
                )
            )

    expected_pairs = gate["pair_counts"]
    if built_pair_counts != expected_pairs:
        raise ValueError("AHS build counts differ from the recorded gate; rerun assess-ahs")

    bridges = sorted(bridges_by_asset.values(), key=lambda row: row["analytical_asset_id"])
    lineage.extend(bridge_lineage_by_asset.values())
    observations.sort(key=lambda row: row["cost_observation_id"])
    snapshots.sort(key=lambda row: row["snapshot_id"])
    labels.sort(key=lambda row: row["snapshot_id"])
    lineage.sort(key=lambda row: (row["target_table"], row["target_key"]))

    row_counts = {
        "source_asset_bridge.csv": write_csv(
            output_dir / "source_asset_bridge.csv", BRIDGE_FIELDS, bridges
        ),
        "annual_cost_observation.csv": write_csv(
            output_dir / "annual_cost_observation.csv", OBSERVATION_FIELDS, observations
        ),
        "property_period_snapshot.csv": write_csv(
            output_dir / "property_period_snapshot.csv", SNAPSHOT_FIELDS, snapshots
        ),
        "property_period_label.csv": write_csv(
            output_dir / "property_period_label.csv", LABEL_FIELDS, labels
        ),
        "record_lineage.csv": write_csv(
            output_dir / "record_lineage.csv", LINEAGE_FIELDS, lineage
        ),
    }
    row_counts["source_document.csv"] = write_csv(
        output_dir / "source_document.csv",
        [
            "document_id",
            "source_id",
            "source_release",
            "file_name",
            "sha256",
            "byte_size",
            "media_type",
            "retrieved_on",
        ],
        _source_documents(raw_dir),
    )
    qa = {
        "status": "built_pending_independent_audit",
        "gate_decision": gate["decision"],
        "gate_distinct_linked_units": gate["distinct_linked_units"],
        "authentic_assets": len(bridges),
        "feature_label_pairs": len(labels),
        "pair_counts": built_pair_counts,
        "explicit_valid_zero_labels": sum(
            row["target_amount_local_nominal"] == "0" for row in labels
        ),
        "task_id": TASK_ID,
    }
    (output_dir / "qa_build_summary.json").write_text(
        json.dumps(qa, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    manifest = {
        "dataset_release": release,
        "dataset_status": "local_analysis_only_license_review_pending",
        "built_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "source_id": SOURCE_ID,
        "source_release": SOURCE_RELEASE,
        "source_archive_sha256": {
            archive: sha256_file(raw_dir / archive) for archive in WAVE_ARCHIVES.values()
        },
        "transform_version": TRANSFORM_VERSION,
        "task_ids": [TASK_ID],
        "modeling_view": "ahs_only_separate_from_rhfs",
        "row_counts": row_counts,
        "output_sha256": {
            path.name: sha256_file(path)
            for path in sorted(output_dir.iterdir())
            if path.is_file() and path.name != "manifest.json"
        },
        "limitations": [
            "AHS is a separate modeling view and must not be stacked with RHFS labels.",
            "The label is a later-wave typical-year survey amount, not an operational 12-month ledger.",
            "The 2023 response maximum changed from $10,000 to $100,000 and is explicitly marked.",
            "Amounts are public U.S. survey values and are not observed WAPDA outcomes.",
            "Redistribution remains blocked until the source license review is recorded.",
        ],
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return output_dir


def _read_wave(archive_path: Path) -> WaveData:
    features: dict[str, SourceRecord] = {}
    labels: dict[str, SourceRecord] = {}
    source_fields = {
        "CONTROL",
        "INTSTATUS",
        "TENURE",
        "MAINTAMT",
        "JMAINTAMT",
        *CORE_FEATURE_FIELDS,
        *(source for _, source, _ in FEATURE_MAP),
    }
    with zipfile.ZipFile(archive_path) as archive, archive.open("household.csv") as binary:
        reader = csv.DictReader(io.TextIOWrapper(binary, encoding="utf-8-sig", newline=""))
        missing = source_fields.difference(reader.fieldnames or [])
        if missing:
            raise ValueError(f"AHS schema drift in {archive_path.name}: {sorted(missing)}")
        seen: set[str] = set()
        for row_number, row in enumerate(reader, start=2):
            control = clean_ahs_value(row["CONTROL"])
            if not control:
                raise ValueError(f"empty CONTROL at {archive_path.name} row {row_number}")
            if control in seen:
                raise ValueError(f"duplicate CONTROL in {archive_path.name}: {control}")
            seen.add(control)
            feature_eligible = clean_ahs_value(row["INTSTATUS"]) == "1" and all(
                clean_ahs_value(row[field]) not in MISSING_CODES
                for field in CORE_FEATURE_FIELDS
            )
            label_eligible = eligible_label(row) is not None
            if not feature_eligible and not label_eligible:
                continue
            projection = {field: row[field] for field in sorted(source_fields)}
            record = SourceRecord(row_number, projection, row_digest(projection))
            if feature_eligible:
                features[control] = record
            if label_eligible:
                labels[control] = record
    return WaveData(features=features, labels=labels)


def _normalized_value(value: str, value_type: str) -> tuple[str | None, str | None]:
    cleaned = clean_ahs_value(value)
    if cleaned in MISSING_CODES:
        reasons = {
            "": "not_reported",
            "-6": "not_applicable",
            "-7": "source_sentinel_-7",
            "-8": "source_sentinel_-8",
            "-9": "not_reported",
            "N": "not_available",
        }
        return None, reasons[cleaned]
    if value_type == "number":
        try:
            return _format_number(float(cleaned)), None
        except ValueError as exc:
            raise ValueError(f"non-numeric AHS feature value: {cleaned!r}") from exc
    return cleaned, None


def _lineage(
    table: str,
    key: str,
    document_id: str,
    record: SourceRecord,
    fields: list[str],
) -> dict[str, str]:
    return {
        "lineage_id": stable_id("lineage", table, key),
        "target_table": table,
        "target_key": key,
        "document_id": document_id,
        "source_row_locator": f"zip_member:household.csv;csv_row:{record.row_number}",
        "source_row_sha256": record.projection_sha256,
        "source_fields_json": json.dumps(sorted(fields), separators=(",", ":")),
        "transform_version": TRANSFORM_VERSION,
        "verification_status": "automated_source_field_projection_link",
    }


def _document_id(name: str) -> str:
    return stable_id("source-document", SOURCE_ID, SOURCE_RELEASE, name)


def _source_documents(raw_dir: Path) -> list[dict[str, Any]]:
    rows = []
    for name in DOCUMENT_FILES:
        path = raw_dir / name
        if not path.is_file():
            raise FileNotFoundError(f"missing source document: {path}")
        rows.append(
            {
                "document_id": _document_id(name),
                "source_id": SOURCE_ID,
                "source_release": SOURCE_RELEASE,
                "file_name": name,
                "sha256": sha256_file(path),
                "byte_size": path.stat().st_size,
                "media_type": "application/zip" if path.suffix == ".zip" else "application/pdf",
                "retrieved_on": "2026-08-08",
            }
        )
    return rows


def _format_number(value: float) -> str:
    return str(int(value)) if value.is_integer() else format(value, ".10g")
