"""Release-level integrity, target, lineage, and privacy checks."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .common import sha256_file


MIN_LABEL_ASSETS = 500


def audit_release(release_dir: Path) -> dict[str, Any]:
    """Audit a built release and return a machine-readable QA report."""
    bridges = _read_csv(release_dir / "source_asset_bridge.csv")
    snapshots = _read_csv(release_dir / "property_period_snapshot.csv")
    observations = _read_csv(release_dir / "annual_cost_observation.csv")
    labels = _read_csv(release_dir / "property_period_label.csv")
    lineage = _read_csv(release_dir / "record_lineage.csv")
    documents = _read_csv(release_dir / "source_document.csv")
    checks: list[dict[str, Any]] = []

    asset_ids = [row["analytical_asset_id"] for row in bridges]
    snapshot_ids = [row["snapshot_id"] for row in snapshots]
    asset_id_set = set(asset_ids)
    snapshot_id_set = set(snapshot_ids)
    label_keys = [f"{row['snapshot_id']}|{row['task_id']}" for row in labels]
    lineage_keys = {(row["target_table"], row["target_key"]) for row in lineage}
    document_ids = {row["document_id"] for row in documents}

    _check(checks, "minimum_label_assets", len(set(label_keys)) >= MIN_LABEL_ASSETS, len(labels))
    _check(checks, "minimum_distinct_assets", len(asset_id_set) >= MIN_LABEL_ASSETS, len(asset_id_set))
    _check(checks, "unique_asset_ids", len(asset_ids) == len(asset_id_set), len(asset_ids))
    _check(
        checks,
        "unique_snapshot_ids",
        len(snapshot_ids) == len(snapshot_id_set),
        len(snapshot_ids),
    )
    _check(checks, "unique_label_keys", len(label_keys) == len(set(label_keys)), len(label_keys))
    _check(
        checks,
        "snapshot_asset_foreign_keys",
        all(row["analytical_asset_id"] in asset_id_set for row in snapshots),
        None,
    )
    _check(
        checks,
        "label_snapshot_foreign_keys",
        all(row["snapshot_id"] in snapshot_id_set for row in labels),
        None,
    )
    _check(
        checks,
        "lineage_document_foreign_keys",
        all(row["document_id"] in document_ids for row in lineage),
        None,
    )
    _check(
        checks,
        "label_lineage_complete",
        all(("property_period_label", key) in lineage_keys for key in label_keys),
        len(labels),
    )
    _check(
        checks,
        "cost_observation_lineage_complete",
        all(
            ("annual_cost_observation", row["cost_observation_id"]) in lineage_keys
            for row in observations
        ),
        len(observations),
    )
    _check(
        checks,
        "costs_nonnegative",
        all(float(row["target_amount_local_nominal"]) >= 0 for row in labels),
        None,
    )
    _check(
        checks,
        "zero_coverage_evidence",
        all(
            float(row["target_amount_local_nominal"]) != 0
            or (row["zero_valid"] == "true" and row["coverage_complete"] == "true")
            for row in labels
        ),
        None,
    )
    _check(
        checks,
        "capital_excluded",
        all(row["capital_included"] == "false" for row in observations),
        None,
    )
    _check(
        checks,
        "operating_expense_reconciliation",
        all(
            row["operating_expense_reconciliation"] in {"passed", "not_testable"}
            for row in observations
        ),
        None,
    )
    _check(
        checks,
        "public_origin_not_wapda",
        all(row["is_exact_wapda_target"] == "false" for row in labels),
        None,
    )
    prohibited_headers = {
        "name",
        "resident_name",
        "address",
        "phone",
        "cnic",
        "contractor",
        "invoice_reference",
        "controlpuf",
    }
    analytical_paths = [
        release_dir / "source_asset_bridge.csv",
        release_dir / "annual_cost_observation.csv",
        release_dir / "property_period_snapshot.csv",
        release_dir / "property_period_label.csv",
    ]
    found_headers = set()
    for path in analytical_paths:
        with path.open("r", encoding="utf-8", newline="") as handle:
            headers = {header.lower() for header in (csv.DictReader(handle).fieldnames or [])}
            found_headers.update(headers.intersection(prohibited_headers))
    _check(checks, "prohibited_identifier_headers_absent", not found_headers, sorted(found_headers))

    manifest = json.loads((release_dir / "manifest.json").read_text(encoding="utf-8"))
    label_task_ids = {row["task_id"] for row in labels}
    _check(
        checks,
        "manifest_task_ids_match_labels",
        label_task_ids == set(manifest["task_ids"]),
        sorted(label_task_ids),
    )
    if manifest.get("modeling_view") == "ahs_only_separate_from_rhfs":
        snapshots_by_id = {row["snapshot_id"]: row for row in snapshots}
        _check(
            checks,
            "ahs_task_isolated",
            label_task_ids == {"future_routine_cost_proxy_v1"},
            sorted(label_task_ids),
        )
        _check(
            checks,
            "ahs_label_after_feature_wave",
            all(
                snapshots_by_id[row["snapshot_id"]]["as_of_date"] < row["label_start"]
                and int(row["label_wave_year"]) > int(row["feature_wave_year"])
                for row in labels
            ),
            None,
        )
        _check(
            checks,
            "ahs_response_maximum_marked",
            all(
                row["source_response_maximum_usd"]
                == ("100000" if row["label_wave_year"] == "2023" else "10000")
                for row in labels
            ),
            None,
        )
    drift = {}
    for name, expected in manifest["output_sha256"].items():
        path = release_dir / name
        actual = sha256_file(path) if path.is_file() else None
        if actual != expected:
            drift[name] = {"expected": expected, "actual": actual}
    _check(checks, "processed_file_checksums", not drift, drift)

    failed = [check["check_id"] for check in checks if check["status"] == "failed"]
    return {
        "release": manifest["dataset_release"],
        "status": "passed" if not failed else "failed",
        "summary": {"passed": len(checks) - len(failed), "failed": len(failed)},
        "failed_checks": failed,
        "checks": checks,
    }


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _check(checks: list[dict[str, Any]], check_id: str, passed: bool, evidence: Any) -> None:
    checks.append(
        {
            "check_id": check_id,
            "status": "passed" if passed else "failed",
            "evidence": evidence,
        }
    )
