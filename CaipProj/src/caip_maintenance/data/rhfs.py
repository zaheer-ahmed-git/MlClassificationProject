"""Harmonize the 2024 RHFS public-use file without inventing records or labels."""

from __future__ import annotations

import csv
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from .common import asset_token, row_digest, sha256_file, stable_id, write_csv


SOURCE_ID = "rhfs_2024"
SOURCE_RELEASE = "v1.0"
DATASET_RELEASE = "public-corpus-v0.1.0-rhfs"
TRANSFORM_VERSION = "rhfs_2024_v1"
RAW_CSV = "rhfspuf2024.csv"
DOCUMENT_FILES = (
    "rhfspuf2024.csv",
    "Codebook-Version-1.pdf",
    "2024-RHFS-PUF-Version-Document.pdf",
)

# These source variables are retained as coded or numeric values. Their output names
# avoid implying more semantic precision than the official codebook supports.
FEATURE_MAP: tuple[tuple[str, str, str], ...] = (
    ("unit_count", "NUMUNITS_R", "number"),
    ("unit_count_category_code", "NUMCAT_R", "code"),
    ("building_count", "NUMBLD_R", "number"),
    ("bedroom_count", "BROOMS", "number"),
    ("studio_unit_count", "BED0_R", "number"),
    ("one_bedroom_unit_count", "BED1_R", "number"),
    ("two_bedroom_unit_count", "BED2_R", "number"),
    ("three_plus_bedroom_unit_count", "BED3_R", "number"),
    ("construction_year_band_code", "YRNEWBLG_R", "code"),
    ("rehabilitation_year_band_code", "YRPROPREHAB_R", "code"),
    ("condominium_code", "PROPCON", "code"),
    ("townhouse_or_rowhouse_code", "PROPTOWN", "code"),
    ("property_complex_code", "COMPLEX", "code"),
    ("commercial_space_code", "COMMSPACE", "code"),
    ("off_street_parking_code", "OFFSTPARK", "code"),
    ("ownership_entity_code", "OWNENT", "code"),
    ("management_arrangement_code", "MNGMNT", "code"),
    ("management_hours", "HRSMNGMNT", "number"),
    ("rent_control_status_code", "RCONTROL", "code"),
    ("government_subsidy_code", "RSUBSIDY", "code"),
    ("low_income_area_code", "LOWINAREA", "code"),
    ("historic_property_code", "HISTORIC", "code"),
    ("electricity_in_rent_code", "IELEC", "code"),
    ("gas_in_rent_code", "IGAS", "code"),
    ("water_in_rent_code", "IWATER", "code"),
    ("sewer_in_rent_code", "ISEWER", "code"),
    ("trash_in_rent_code", "ITRASH", "code"),
    ("parking_in_rent_code", "IPARKING", "code"),
    ("pool_in_rent_code", "IPOOL", "code"),
    ("occupied_unit_count", "TRENOC_R", "number"),
    ("vacant_unit_count", "TRENVA_R", "number"),
    ("market_value_usd", "MRKTVAL_R", "number"),
    ("market_value_per_unit_usd", "MRKTVALPU_R", "number"),
    ("survey_weight", "WEIGHT", "number"),
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
]

SNAPSHOT_BASE_FIELDS = [
    "snapshot_id",
    "analytical_asset_id",
    "source_id",
    "asset_grain",
    "as_of_date",
    "task_mode",
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


def harmonize(project_root: Path, release: str = DATASET_RELEASE) -> Path:
    """Build the first RHFS-backed local processed release."""
    if release != DATASET_RELEASE:
        raise ValueError(f"supported release is {DATASET_RELEASE!r}")
    raw_dir = project_root / "data" / "raw" / "public" / SOURCE_ID / SOURCE_RELEASE
    raw_csv = raw_dir / RAW_CSV
    if not raw_csv.is_file():
        raise FileNotFoundError(f"missing raw RHFS file: {raw_csv}")

    output_dir = project_root / "data" / "processed" / "releases" / release
    if output_dir.exists():
        raise FileExistsError(
            f"release already exists: {output_dir}; release directories are immutable"
        )
    output_dir.mkdir(parents=True)

    document_id = stable_id("source-document", SOURCE_ID, SOURCE_RELEASE, RAW_CSV)
    bridges: list[dict[str, Any]] = []
    observations: list[dict[str, Any]] = []
    snapshots: list[dict[str, Any]] = []
    labels: list[dict[str, Any]] = []
    lineage: list[dict[str, Any]] = []
    excluded = {
        "not_reported": 0,
        "not_applicable": 0,
        "ambiguous_zero_without_response_confirmation": 0,
        "operating_expense_reconciliation_failure": 0,
    }
    raw_rows = 0

    with raw_csv.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"CONTROLPUF", "OPREP", "PROPANS", "JPREP", "OPEX_R"}
        required.update(source for _, source, _ in FEATURE_MAP)
        missing_fields = required.difference(reader.fieldnames or [])
        if missing_fields:
            raise ValueError(f"RHFS schema drift: missing {sorted(missing_fields)}")

        for row_number, row in enumerate(reader, start=2):
            raw_rows += 1
            native_id = row["CONTROLPUF"]
            if not native_id:
                raise ValueError(f"empty RHFS native key at CSV row {row_number}")
            asset_id = asset_token(SOURCE_ID, native_id)
            snapshot_id = stable_id("snapshot", asset_id, "2023-12-31")
            source_hash = row_digest(row)
            locator = f"csv_row:{row_number}"

            bridge = {
                "source_id": SOURCE_ID,
                "analytical_asset_id": asset_id,
                "native_grain": "rental_property",
                "source_asset_token": asset_id,
                "unit_count": _number_or_none(row["NUMUNITS_R"]),
                "survey_weight": _number_or_none(row["WEIGHT"]),
            }
            bridges.append(bridge)
            lineage.append(
                _lineage(
                    "source_asset_bridge",
                    asset_id,
                    document_id,
                    locator,
                    source_hash,
                    ["CONTROLPUF", "NUMUNITS_R", "WEIGHT"],
                )
            )

            snapshot: dict[str, Any] = {
                "snapshot_id": snapshot_id,
                "analytical_asset_id": asset_id,
                "source_id": SOURCE_ID,
                "asset_grain": "rental_property",
                "as_of_date": "2023-12-31",
                "task_mode": "cross_sectional_held_out_estimation",
            }
            for output_name, source_name, value_type in FEATURE_MAP:
                value, reason = _normalized_value(row[source_name], value_type)
                snapshot[output_name] = value
                snapshot[f"{output_name}_missing_reason"] = reason
            snapshots.append(snapshot)
            lineage.append(
                _lineage(
                    "property_period_snapshot",
                    snapshot_id,
                    document_id,
                    locator,
                    source_hash,
                    [source for _, source, _ in FEATURE_MAP],
                )
            )

            maintenance = _source_amount(row["OPREP"])
            if maintenance is None:
                excluded["not_applicable" if row["OPREP"] == "-8" else "not_reported"] += 1
                continue
            if maintenance == 0 and row["PROPANS"] != "1":
                excluded["ambiguous_zero_without_response_confirmation"] += 1
                continue

            operating = _source_amount(row["OPEX_R"])
            if operating is not None and maintenance > operating:
                excluded["operating_expense_reconciliation_failure"] += 1
                continue
            reconciliation = "passed" if operating is not None else "not_testable"
            label_origin = (
                "public_survey_source_edited" if row["JPREP"] == "1" else "public_survey_reported"
            )
            observation_id = stable_id("cost-observation", asset_id, "2023")
            observation = {
                "cost_observation_id": observation_id,
                "analytical_asset_id": asset_id,
                "source_id": SOURCE_ID,
                "period_start": "2023-01-01",
                "period_end": "2023-12-31",
                "amount_local_nominal": _format_number(maintenance),
                "currency": "USD",
                "cost_category": "maintenance_and_repair",
                "label_origin": label_origin,
                "scope_fidelity": "annual_maintenance_proxy_appliance_unseparated",
                "capital_included": False,
                "appliance_separable": False,
                "coverage_status": "explicit_response",
                "zero_valid": maintenance == 0,
                "operating_expense_reconciliation": reconciliation,
            }
            observations.append(observation)
            label = {
                "snapshot_id": snapshot_id,
                "task_id": "annual_cost_estimation_v1",
                "label_start": "2023-01-01",
                "label_end": "2023-12-31",
                "target_amount_local_nominal": _format_number(maintenance),
                "target_currency": "USD",
                "target_definition": "RHFS annual maintenance and repair expense",
                "label_origin": label_origin,
                "scope_fidelity": "annual_maintenance_proxy_appliance_unseparated",
                "coverage_complete": True,
                "zero_valid": maintenance == 0,
                "is_exact_wapda_target": False,
            }
            labels.append(label)
            lineage.append(
                _lineage(
                    "annual_cost_observation",
                    observation_id,
                    document_id,
                    locator,
                    source_hash,
                    ["OPREP", "JPREP", "PROPANS", "OPEX_R"],
                )
            )
            lineage.append(
                _lineage(
                    "property_period_label",
                    f"{snapshot_id}|annual_cost_estimation_v1",
                    document_id,
                    locator,
                    source_hash,
                    ["OPREP", "JPREP", "PROPANS", "OPEX_R"],
                )
            )

    bridges.sort(key=lambda row: row["analytical_asset_id"])
    snapshots.sort(key=lambda row: row["snapshot_id"])
    observations.sort(key=lambda row: row["cost_observation_id"])
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
    source_documents = _source_documents(raw_dir)
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
        source_documents,
    )
    qa = {
        "status": "built_pending_independent_audit",
        "raw_rows": raw_rows,
        "authentic_assets": len(bridges),
        "label_bearing_assets": len(labels),
        "explicit_valid_zero_labels": sum(
            row["target_amount_local_nominal"] == "0" for row in labels
        ),
        "source_edited_labels": sum(
            row["label_origin"] == "public_survey_source_edited" for row in labels
        ),
        "excluded": excluded,
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
        "source_file_sha256": sha256_file(raw_csv),
        "transform_version": TRANSFORM_VERSION,
        "task_ids": ["annual_cost_estimation_v1"],
        "row_counts": row_counts,
        "output_sha256": {
            path.name: sha256_file(path)
            for path in sorted(output_dir.iterdir())
            if path.is_file() and path.name != "manifest.json"
        },
        "limitations": [
            "Cross-sectional held-out annual cost estimation, not future forecasting.",
            "Appliance expenditure cannot be separated from RHFS maintenance expense.",
            "Amounts are public U.S. survey outcomes and are not observed WAPDA costs.",
            "Redistribution remains blocked until the source license review is recorded.",
        ],
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return output_dir


def _source_documents(raw_dir: Path) -> list[dict[str, Any]]:
    rows = []
    for name in DOCUMENT_FILES:
        path = raw_dir / name
        if not path.is_file():
            raise FileNotFoundError(f"missing source document: {path}")
        media_type = "text/csv" if path.suffix == ".csv" else "application/pdf"
        rows.append(
            {
                "document_id": stable_id("source-document", SOURCE_ID, SOURCE_RELEASE, name),
                "source_id": SOURCE_ID,
                "source_release": SOURCE_RELEASE,
                "file_name": name,
                "sha256": sha256_file(path),
                "byte_size": path.stat().st_size,
                "media_type": media_type,
                "retrieved_on": "2026-08-07",
            }
        )
    return rows


def _lineage(
    table: str,
    key: str,
    document_id: str,
    locator: str,
    source_hash: str,
    fields: list[str],
) -> dict[str, str]:
    return {
        "lineage_id": stable_id("lineage", table, key),
        "target_table": table,
        "target_key": key,
        "document_id": document_id,
        "source_row_locator": locator,
        "source_row_sha256": source_hash,
        "source_fields_json": json.dumps(sorted(fields), separators=(",", ":")),
        "transform_version": TRANSFORM_VERSION,
        "verification_status": "automated_source_row_link",
    }


def _normalized_value(value: str, value_type: str) -> tuple[str | None, str | None]:
    if value == "-8":
        return None, "not_applicable"
    if value == "-9" or value == "":
        return None, "not_reported"
    if value_type == "number":
        return _format_number(float(value)), None
    return value, None


def _number_or_none(value: str) -> str | None:
    normalized, _ = _normalized_value(value, "number")
    return normalized


def _source_amount(value: str) -> float | None:
    if value in {"", "-8", "-9"}:
        return None
    amount = float(value)
    if amount < 0:
        raise ValueError(f"unexpected negative non-sentinel source amount: {value}")
    return amount


def _format_number(value: float) -> str:
    return str(int(value)) if value.is_integer() else format(value, ".10g")

