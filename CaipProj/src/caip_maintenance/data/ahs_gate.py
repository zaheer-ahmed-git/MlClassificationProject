"""Run the AHS longitudinal feasibility gate before harmonization."""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path
import zipfile

from .common import sha256_file


SOURCE_ID = "ahs_2015_2023"
SOURCE_RELEASE = "official_2015_2023"
MINIMUM_LINKED_UNITS = 500
WAVE_ARCHIVES = {
    2015: "2015_AHS_National_PUF_v3.1_CSV.zip",
    2017: "2017_AHS_National_PUF_v3.1_CSV.zip",
    2019: "2019_AHS_National_PUF_v1.1_CSV.zip",
    2021: "2021_AHS_National_PUF_v1.0_CSV.zip",
    2023: "2023_AHS_National_PUF_v1.1_CSV.zip",
}
CORE_FEATURE_FIELDS = ("YRBUILT", "UNITSIZE", "TOTROOMS", "BATHROOMS", "BLD")
MISSING_CODES = {"", "-6", "-7", "-8", "-9", "N"}


def assess_ahs_gate(
    project_root: Path,
    minimum_linked_units: int = MINIMUM_LINKED_UNITS,
    write_result: bool = True,
) -> dict[str, object]:
    """Count authentic adjacent-wave links without building an analytical release."""
    raw_dir = project_root / "data" / "raw" / "public" / SOURCE_ID / SOURCE_RELEASE
    scans = {year: _scan_wave(raw_dir / archive) for year, archive in WAVE_ARCHIVES.items()}

    pairs: list[dict[str, object]] = []
    linked_controls: set[str] = set()
    years = sorted(WAVE_ARCHIVES)
    for earlier, later in zip(years, years[1:]):
        linked = scans[earlier]["feature_controls"] & scans[later]["label_controls"]
        linked_controls.update(linked)
        pairs.append(
            {
                "earlier_wave": earlier,
                "later_wave": later,
                "eligible_pair_rows": len(linked),
            }
        )

    result: dict[str, object] = {
        "gate_id": "ahs_longitudinal_future_routine_cost_proxy_v1",
        "source_id": SOURCE_ID,
        "source_release": SOURCE_RELEASE,
        "task_id": "future_routine_cost_proxy_v1",
        "threshold_distinct_linked_units": minimum_linked_units,
        "decision": "go" if len(linked_controls) >= minimum_linked_units else "no_go",
        "distinct_linked_units": len(linked_controls),
        "eligible_pair_rows": sum(int(pair["eligible_pair_rows"]) for pair in pairs),
        "pair_counts": pairs,
        "wave_counts": {
            str(year): {
                "raw_household_rows": scan["raw_rows"],
                "complete_earlier_feature_rows": len(scan["feature_controls"]),
                "eligible_later_label_rows": len(scan["label_controls"]),
                "maximum_eligible_maintamt": scan["maximum_eligible_maintamt"],
                "archive_sha256": scan["archive_sha256"],
            }
            for year, scan in scans.items()
        },
        "eligibility": {
            "earlier_wave": (
                "INTSTATUS=1 and non-sentinel YRBUILT, UNITSIZE, TOTROOMS, "
                "BATHROOMS, and BLD"
            ),
            "later_wave": "INTSTATUS=1, TENURE in {1,2}, and nonnegative MAINTAMT",
            "link_key": "exact CONTROL match between adjacent national PUF waves",
            "missing_codes": sorted(MISSING_CODES),
        },
        "semantic_evidence": {
            "stable_unit_id": (
                "Sample Case History File: one record per sample case, uniquely identified "
                "by CONTROL; CONTROL can merge the case-history file with AHS PUFs."
            ),
            "label_field": (
                "Wave mini codebooks define MAINTAMT as amount of annual routine "
                "maintenance costs."
            ),
            "response_cap_change": (
                "2023 Historical Changes states the maximum reportable amount increased "
                "from $10,000 in 2021 to $100,000 in 2023."
            ),
        },
        "release_policy": "local_analysis_only_license_review_pending",
        "native_identifiers_exported": False,
    }
    if write_result:
        output = project_root / "data" / "interim" / "gates" / "ahs_gate_result.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        result["result_path"] = str(output)
    return result


def load_passed_gate(project_root: Path) -> dict[str, object]:
    """Load the recorded gate and reject harmonization if it is absent or stale."""
    path = project_root / "data" / "interim" / "gates" / "ahs_gate_result.json"
    if not path.is_file():
        raise FileNotFoundError(f"run assess-ahs before harmonization: {path}")
    result = json.loads(path.read_text(encoding="utf-8"))
    if result.get("decision") != "go":
        raise ValueError("AHS gate did not pass; the AHS release must not be built")
    raw_dir = project_root / "data" / "raw" / "public" / SOURCE_ID / SOURCE_RELEASE
    wave_counts = result.get("wave_counts", {})
    for year, archive in WAVE_ARCHIVES.items():
        expected = wave_counts.get(str(year), {}).get("archive_sha256")
        actual = sha256_file(raw_dir / archive)
        if expected != actual:
            raise ValueError(f"AHS gate is stale for {archive}; rerun assess-ahs")
    return result


def _scan_wave(archive_path: Path) -> dict[str, object]:
    if not archive_path.is_file():
        raise FileNotFoundError(f"missing AHS PUF archive: {archive_path}")
    feature_controls: set[str] = set()
    label_controls: set[str] = set()
    raw_rows = 0
    maximum: float | None = None
    with zipfile.ZipFile(archive_path) as archive:
        if "household.csv" not in archive.namelist():
            raise ValueError(f"AHS archive lacks household.csv: {archive_path.name}")
        with archive.open("household.csv") as binary:
            text = io.TextIOWrapper(binary, encoding="utf-8-sig", newline="")
            reader = csv.DictReader(text)
            required = {"CONTROL", "INTSTATUS", "TENURE", "MAINTAMT", *CORE_FEATURE_FIELDS}
            missing = required.difference(reader.fieldnames or [])
            if missing:
                raise ValueError(f"AHS schema drift in {archive_path.name}: {sorted(missing)}")
            for row_number, row in enumerate(reader, start=2):
                raw_rows += 1
                control = clean_ahs_value(row["CONTROL"])
                if not control:
                    raise ValueError(f"empty CONTROL at {archive_path.name} row {row_number}")
                complete = clean_ahs_value(row["INTSTATUS"]) == "1" and all(
                    clean_ahs_value(row[field]) not in MISSING_CODES
                    for field in CORE_FEATURE_FIELDS
                )
                if complete:
                    feature_controls.add(control)
                label = eligible_label(row)
                if label is not None:
                    label_controls.add(control)
                    maximum = label if maximum is None else max(maximum, label)
    return {
        "raw_rows": raw_rows,
        "feature_controls": feature_controls,
        "label_controls": label_controls,
        "maximum_eligible_maintamt": _format_number(maximum) if maximum is not None else None,
        "archive_sha256": sha256_file(archive_path),
    }


def clean_ahs_value(value: str | None) -> str:
    """Normalize AHS CSV's character-code apostrophe wrapper without recoding values."""
    cleaned = (value or "").strip()
    if len(cleaned) >= 2 and cleaned[0] == cleaned[-1] == "'":
        return cleaned[1:-1].strip()
    return cleaned


def eligible_label(row: dict[str, str]) -> float | None:
    if clean_ahs_value(row.get("INTSTATUS")) != "1":
        return None
    if clean_ahs_value(row.get("TENURE")) not in {"1", "2"}:
        return None
    value = clean_ahs_value(row.get("MAINTAMT"))
    if value in MISSING_CODES:
        return None
    try:
        amount = float(value)
    except ValueError as exc:
        raise ValueError(f"non-numeric eligible MAINTAMT: {value!r}") from exc
    return amount if amount >= 0 else None


def _format_number(value: float) -> str:
    return str(int(value)) if value.is_integer() else format(value, ".10g")
