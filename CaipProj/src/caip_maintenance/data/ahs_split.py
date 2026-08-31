"""Create and audit the frozen, unit-grouped AHS temporal split."""

from __future__ import annotations

from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import tomllib
from typing import Any

from .ahs import DATASET_RELEASE, TASK_ID
from .common import sha256_file, stable_id, write_csv


SPLIT_ID = "ahs-grouped-temporal-v1"
SPLIT_ASSIGNMENT_FIELDS = [
    "split_assignment_id",
    "dataset_release",
    "split_id",
    "task_id",
    "snapshot_id",
    "analytical_asset_id",
    "asset_group_id",
    "split_name",
    "asset_terminal_label_wave",
    "feature_wave_year",
    "label_wave_year",
    "division_code",
    "building_type_code",
    "response_cap_regime",
    "include_in_primary_metrics",
    "include_in_pre_2023_cap_sensitivity",
    "threshold_version",
]


def assign_ahs_splits(
    project_root: Path,
    release: str = DATASET_RELEASE,
    split_id: str = SPLIT_ID,
) -> Path:
    """Build an immutable split artifact without mutating the source release."""
    spec = _load_spec(project_root, split_id)
    _validate_spec(spec, release, split_id)
    _validate_semantic_decision(project_root, spec)

    release_dir = project_root / "data" / "processed" / "releases" / release
    release_manifest_path = release_dir / "manifest.json"
    release_manifest = json.loads(release_manifest_path.read_text(encoding="utf-8"))
    _validate_release(release_dir, release_manifest)

    snapshots = _read_csv(release_dir / "property_period_snapshot.csv")
    labels = _read_csv(release_dir / "property_period_label.csv")
    snapshots_by_id = {row["snapshot_id"]: row for row in snapshots}
    if len(snapshots_by_id) != len(snapshots):
        raise ValueError("AHS release has duplicate snapshot_id values")
    if len({row["snapshot_id"] for row in labels}) != len(labels):
        raise ValueError("AHS release has duplicate split-eligible label snapshots")

    transition_rows: list[tuple[dict[str, str], dict[str, str]]] = []
    terminal_wave_by_asset: dict[str, int] = {}
    for label in labels:
        if label["task_id"] != TASK_ID:
            raise ValueError(f"unexpected AHS task in label table: {label['task_id']!r}")
        snapshot = snapshots_by_id.get(label["snapshot_id"])
        if snapshot is None:
            raise ValueError(f"label lacks snapshot: {label['snapshot_id']}")
        if snapshot["analytical_asset_id"] == "":
            raise ValueError("empty analytical_asset_id in AHS snapshot")
        if int(snapshot["source_wave_year"]) != int(label["feature_wave_year"]):
            raise ValueError("feature wave differs between AHS snapshot and label")
        asset_id = snapshot["analytical_asset_id"]
        label_wave = int(label["label_wave_year"])
        terminal_wave_by_asset[asset_id] = max(
            terminal_wave_by_asset.get(asset_id, label_wave), label_wave
        )
        transition_rows.append((snapshot, label))

    terminal_assignment = {
        int(year): split_name
        for year, split_name in spec["terminal_wave_assignment"].items()
    }
    cap_regime = {
        int(year): regime for year, regime in spec["response_cap_regime"].items()
    }
    sensitivity_wave = int(spec["cap_sensitivity_excluded_label_wave"])
    rows: list[dict[str, Any]] = []
    for snapshot, label in transition_rows:
        asset_id = snapshot["analytical_asset_id"]
        terminal_wave = terminal_wave_by_asset[asset_id]
        if terminal_wave not in terminal_assignment:
            raise ValueError(f"no split assignment for terminal label wave {terminal_wave}")
        label_wave = int(label["label_wave_year"])
        if label_wave not in cap_regime:
            raise ValueError(f"no response-cap regime for label wave {label_wave}")
        split_name = terminal_assignment[terminal_wave]
        rows.append(
            {
                "split_assignment_id": stable_id(
                    "split-assignment", release, split_id, label["snapshot_id"], TASK_ID
                ),
                "dataset_release": release,
                "split_id": split_id,
                "task_id": TASK_ID,
                "snapshot_id": label["snapshot_id"],
                "analytical_asset_id": asset_id,
                "asset_group_id": asset_id,
                "split_name": split_name,
                "asset_terminal_label_wave": terminal_wave,
                "feature_wave_year": label["feature_wave_year"],
                "label_wave_year": label_wave,
                "division_code": snapshot["division_code"],
                "building_type_code": snapshot["building_type_code"],
                "response_cap_regime": cap_regime[label_wave],
                "include_in_primary_metrics": True,
                "include_in_pre_2023_cap_sensitivity": label_wave != sensitivity_wave,
                "threshold_version": spec["threshold_version"],
            }
        )
    rows.sort(key=lambda row: row["split_assignment_id"])

    output_dir = (
        project_root / "data" / "processed" / "splits" / release / split_id
    )
    if output_dir.exists():
        raise FileExistsError(
            f"split already exists: {output_dir}; split artifacts are immutable"
        )
    output_dir.mkdir(parents=True)
    assignment_path = output_dir / "split_assignment.csv"
    write_csv(assignment_path, SPLIT_ASSIGNMENT_FIELDS, rows)

    row_counts = Counter(row["split_name"] for row in rows)
    assets_by_split: dict[str, set[str]] = defaultdict(set)
    label_wave_counts: Counter[tuple[str, int]] = Counter()
    strata_counts: Counter[tuple[str, str, str]] = Counter()
    for row in rows:
        assets_by_split[row["split_name"]].add(row["analytical_asset_id"])
        label_wave_counts[(row["split_name"], int(row["label_wave_year"]))] += 1
        strata_counts[
            (row["split_name"], row["division_code"], row["building_type_code"])
        ] += 1

    manifest = {
        "split_id": split_id,
        "split_contract_version": spec["split_contract_version"],
        "dataset_release": release,
        "task_id": TASK_ID,
        "status": "frozen_local_analysis_only",
        "built_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "source_release_manifest_sha256": sha256_file(release_manifest_path),
        "source_table_sha256": {
            name: sha256_file(release_dir / name)
            for name in ("property_period_snapshot.csv", "property_period_label.csv")
        },
        "semantic_decision": {
            "decision_id": spec["semantic_decision_id"],
            "path": spec["semantic_decision_path"],
            "sha256": spec["semantic_decision_sha256"],
        },
        "assignment_rule": {
            "group_field": spec["group_field"],
            "basis": spec["assignment_basis"],
            "all_group_transitions_inherit_assignment": True,
            "terminal_wave_assignment": {
                str(year): terminal_assignment[year] for year in sorted(terminal_assignment)
            },
            "interpretation": (
                "latest, preceding, and older refer to each asset's terminal eligible "
                "label-wave cohort; assigning individual transitions would violate the "
                "housing-unit grouping invariant"
            ),
        },
        "counts": {
            "transition_rows": len(rows),
            "distinct_assets": len(terminal_wave_by_asset),
            "rows_by_split": {name: row_counts[name] for name in sorted(row_counts)},
            "assets_by_split": {
                name: len(assets_by_split[name]) for name in sorted(assets_by_split)
            },
            "rows_by_split_and_label_wave": [
                {"split_name": split_name, "label_wave_year": wave, "rows": count}
                for (split_name, wave), count in sorted(label_wave_counts.items())
            ],
        },
        "stratification_report": {
            "assignment_is_deterministic_not_rebalanced": True,
            "fields": spec["strata_report_fields"],
            "counts": [
                {
                    "split_name": split_name,
                    "division_code": division,
                    "building_type_code": building_type,
                    "rows": count,
                }
                for (split_name, division, building_type), count in sorted(
                    strata_counts.items()
                )
            ],
        },
        "cap_sensitivity": {
            "primary_view": "include_all_eligible_transitions_without_target_clipping",
            "sensitivity_view": "exclude_label_wave_2023",
            "excluded_label_wave": sensitivity_wave,
            "primary_rows": len(rows),
            "sensitivity_rows": sum(
                row["include_in_pre_2023_cap_sensitivity"] for row in rows
            ),
            "excluded_rows": sum(
                not row["include_in_pre_2023_cap_sensitivity"] for row in rows
            ),
            "target_clipping": spec["target_clipping"],
        },
        "threshold_version": spec["threshold_version"],
        "distribution": spec["distribution"],
        "output_sha256": {"split_assignment.csv": sha256_file(assignment_path)},
        "prohibited_claims": [
            "observed WAPDA outcome",
            "exact WAPDA next-12-month target",
            "validated WASC forecast",
            "RHFS and AHS stacked target",
        ],
    }
    (output_dir / "split_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return output_dir


def audit_ahs_split(project_root: Path, split_dir: Path) -> dict[str, Any]:
    """Audit assignment completeness, group isolation, temporal rules, and cap flags."""
    manifest = json.loads((split_dir / "split_manifest.json").read_text(encoding="utf-8"))
    split_id = manifest["split_id"]
    release = manifest["dataset_release"]
    spec = _load_spec(project_root, split_id)
    release_dir = project_root / "data" / "processed" / "releases" / release
    assignments = _read_csv(split_dir / "split_assignment.csv")
    labels = _read_csv(release_dir / "property_period_label.csv")
    snapshots = _read_csv(release_dir / "property_period_snapshot.csv")
    snapshots_by_id = {row["snapshot_id"]: row for row in snapshots}
    labels_by_snapshot = {row["snapshot_id"]: row for row in labels}
    checks: list[dict[str, Any]] = []

    ids = [row["split_assignment_id"] for row in assignments]
    assignment_snapshots = [row["snapshot_id"] for row in assignments]
    _check(checks, "unique_split_assignment_ids", len(ids) == len(set(ids)), len(ids))
    _check(
        checks,
        "unique_assigned_snapshots",
        len(assignment_snapshots) == len(set(assignment_snapshots)),
        len(assignment_snapshots),
    )
    _check(
        checks,
        "all_and_only_release_labels_assigned",
        set(assignment_snapshots) == set(labels_by_snapshot),
        {
            "assignments": len(set(assignment_snapshots)),
            "labels": len(labels_by_snapshot),
        },
    )
    _check(
        checks,
        "task_release_split_constants",
        all(
            row["task_id"] == TASK_ID
            and row["dataset_release"] == release
            and row["split_id"] == split_id
            for row in assignments
        ),
        None,
    )

    splits_by_asset: dict[str, set[str]] = defaultdict(set)
    label_waves_by_asset: dict[str, list[int]] = defaultdict(list)
    for row in assignments:
        splits_by_asset[row["analytical_asset_id"]].add(row["split_name"])
        label_waves_by_asset[row["analytical_asset_id"]].append(
            int(row["label_wave_year"])
        )
    leaking_assets = sorted(
        asset for asset, split_names in splits_by_asset.items() if len(split_names) != 1
    )
    _check(checks, "zero_asset_leakage", not leaking_assets, len(leaking_assets))

    terminal_assignment = {
        int(year): split_name
        for year, split_name in spec["terminal_wave_assignment"].items()
    }
    rule_failures = 0
    relationship_failures = 0
    cap_failures = 0
    sensitivity_failures = 0
    for row in assignments:
        snapshot = snapshots_by_id.get(row["snapshot_id"])
        label = labels_by_snapshot.get(row["snapshot_id"])
        asset_id = row["analytical_asset_id"]
        if (
            snapshot is None
            or label is None
            or snapshot["analytical_asset_id"] != asset_id
            or row["asset_group_id"] != asset_id
            or row["division_code"] != snapshot["division_code"]
            or row["building_type_code"] != snapshot["building_type_code"]
            or row["feature_wave_year"] != label["feature_wave_year"]
            or row["label_wave_year"] != label["label_wave_year"]
        ):
            relationship_failures += 1
        if snapshot is None or label is None:
            # Continue collecting audit failures instead of crashing on a corrupt join.
            rule_failures += 1
            cap_failures += 1
            sensitivity_failures += 1
            continue
        terminal_wave = max(label_waves_by_asset[asset_id])
        if (
            int(row["asset_terminal_label_wave"]) != terminal_wave
            or row["split_name"] != terminal_assignment.get(terminal_wave)
        ):
            rule_failures += 1
        label_wave = int(row["label_wave_year"])
        expected_cap = "100000" if label_wave == 2023 else "10000"
        expected_regime = spec["response_cap_regime"].get(str(label_wave))
        if (
            label["source_response_maximum_usd"] != expected_cap
            or row["response_cap_regime"] != expected_regime
        ):
            cap_failures += 1
        expected_sensitivity = label_wave != int(
            spec["cap_sensitivity_excluded_label_wave"]
        )
        if (
            row["include_in_primary_metrics"] != "true"
            or (row["include_in_pre_2023_cap_sensitivity"] == "true")
            != expected_sensitivity
        ):
            sensitivity_failures += 1
    _check(
        checks,
        "release_relationships_match",
        relationship_failures == 0,
        relationship_failures,
    )
    _check(checks, "terminal_wave_assignment_rule", rule_failures == 0, rule_failures)
    _check(checks, "response_cap_regimes_match", cap_failures == 0, cap_failures)
    _check(
        checks,
        "cap_sensitivity_flags_match",
        sensitivity_failures == 0,
        sensitivity_failures,
    )
    _check(
        checks,
        "all_configured_splits_present",
        {row["split_name"] for row in assignments} == {"training", "validation", "test"},
        sorted({row["split_name"] for row in assignments}),
    )
    _check(
        checks,
        "no_model_threshold_assigned",
        all(row["threshold_version"] == "not_assigned_pre_modeling" for row in assignments),
        None,
    )
    prohibited_headers = {
        "control",
        "target_amount_local_nominal",
        "resident_name",
        "address",
    }
    found_headers = set(assignments[0]).intersection(prohibited_headers) if assignments else set()
    _check(checks, "target_and_native_identifier_absent", not found_headers, sorted(found_headers))

    semantic_path = project_root / manifest["semantic_decision"]["path"]
    semantic_hash = sha256_file(semantic_path) if semantic_path.is_file() else None
    _check(
        checks,
        "semantic_decision_frozen",
        semantic_hash
        == manifest["semantic_decision"]["sha256"]
        == spec["semantic_decision_sha256"],
        semantic_hash,
    )
    release_manifest_path = release_dir / "manifest.json"
    _check(
        checks,
        "source_release_manifest_unchanged",
        sha256_file(release_manifest_path) == manifest["source_release_manifest_sha256"],
        None,
    )
    source_drift = {
        name: {
            "expected": expected,
            "actual": sha256_file(release_dir / name)
            if (release_dir / name).is_file()
            else None,
        }
        for name, expected in manifest["source_table_sha256"].items()
        if not (release_dir / name).is_file()
        or sha256_file(release_dir / name) != expected
    }
    _check(checks, "source_tables_unchanged", not source_drift, source_drift)
    assignment_path = split_dir / "split_assignment.csv"
    assignment_hash = sha256_file(assignment_path) if assignment_path.is_file() else None
    _check(
        checks,
        "split_assignment_checksum",
        assignment_hash == manifest["output_sha256"]["split_assignment.csv"],
        assignment_hash,
    )

    failed = [check["check_id"] for check in checks if check["status"] == "failed"]
    return {
        "dataset_release": release,
        "split_id": split_id,
        "status": "passed" if not failed else "failed",
        "summary": {"passed": len(checks) - len(failed), "failed": len(failed)},
        "failed_checks": failed,
        "checks": checks,
    }


def _load_spec(project_root: Path, split_id: str) -> dict[str, Any]:
    if split_id != SPLIT_ID:
        raise ValueError(f"supported AHS split is {SPLIT_ID!r}")
    path = project_root / "configs" / "splits" / "ahs_grouped_temporal_v1.toml"
    with path.open("rb") as handle:
        return tomllib.load(handle)


def _validate_spec(spec: dict[str, Any], release: str, split_id: str) -> None:
    if spec["split_id"] != split_id or spec["dataset_release"] != release:
        raise ValueError("AHS split specification does not match requested release/split")
    if spec["task_id"] != TASK_ID:
        raise ValueError("AHS split specification has an unexpected task")
    if spec["group_field"] != "analytical_asset_id" or not spec["same_asset_all_transitions"]:
        raise ValueError("AHS split specification does not enforce housing-unit grouping")
    assignments = set(spec["terminal_wave_assignment"].values())
    if assignments != {"training", "validation", "test"}:
        raise ValueError("AHS split specification must define training, validation, and test")
    if spec["target_clipping"] != "prohibited":
        raise ValueError("AHS split specification must prohibit target clipping")
    if spec["distribution"] != "local-analysis-only":
        raise ValueError("AHS split redistribution remains local-analysis-only")


def _validate_semantic_decision(project_root: Path, spec: dict[str, Any]) -> None:
    decision_path = project_root / spec["semantic_decision_path"]
    if not decision_path.is_file():
        raise FileNotFoundError(f"missing frozen AHS semantic decision: {decision_path}")
    actual = sha256_file(decision_path)
    if actual != spec["semantic_decision_sha256"]:
        raise ValueError(
            "frozen AHS semantic decision checksum changed; version the decision and split spec"
        )


def _validate_release(release_dir: Path, manifest: dict[str, Any]) -> None:
    if manifest.get("dataset_release") != DATASET_RELEASE:
        raise ValueError("split source is not the approved AHS release")
    if manifest.get("task_ids") != [TASK_ID]:
        raise ValueError("split source does not contain the isolated AHS task")
    if manifest.get("modeling_view") != "ahs_only_separate_from_rhfs":
        raise ValueError("split source is not the separate AHS modeling view")
    drift = []
    for name in ("property_period_snapshot.csv", "property_period_label.csv"):
        path = release_dir / name
        if not path.is_file() or sha256_file(path) != manifest["output_sha256"].get(name):
            drift.append(name)
    if drift:
        raise ValueError(f"AHS release checksum drift: {drift}")


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
