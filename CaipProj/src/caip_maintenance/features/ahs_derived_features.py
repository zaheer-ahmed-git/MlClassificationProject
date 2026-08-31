"""Cutoff-safe derived predictors for the AHS feature-engineering preprocessor."""

from __future__ import annotations

import math
from typing import Any

from caip_maintenance.data.ahs import FEATURE_MAP


DERIVED_FEATURE_MAP: tuple[tuple[str, str, str], ...] = (
    ("property_age_years", "derived_property_age", "number"),
    ("log_prior_routine_maintenance_usd", "derived_log_prior_cost", "number"),
    ("prior_cost_per_room", "derived_prior_per_room", "number"),
    ("rooms_per_bedroom", "derived_rooms_per_bedroom", "number"),
    ("condition_defect_count", "derived_condition_defects", "number"),
)

CONDITION_CODE_FIELDS = (
    "roof_leak_code",
    "roof_hole_code",
    "roof_sag_code",
    "roof_shingle_condition_code",
    "sewage_breakdown_code",
)

FEATURE_GROUPS: dict[str, tuple[str, ...]] = {
    "structural": (
        "building_type_code",
        "year_built",
        "unit_size_code",
        "total_rooms",
        "bathrooms_code",
        "bedrooms",
        "unit_floors",
        "foundation_type_code",
        "garage_code",
        "lot_size_code",
        "owns_lot_code",
        "property_age_years",
        "rooms_per_bedroom",
    ),
    "systems": (
        "heating_type_code",
        "heating_fuel_code",
        "primary_air_conditioning_code",
        "sewage_type_code",
    ),
    "condition": (
        *CONDITION_CODE_FIELDS,
        "condition_defect_count",
    ),
    "socioeconomic": (
        "tenure_code",
        "household_income_usd",
    ),
    "prior_maintenance": (
        "prior_routine_maintenance_usd",
        "log_prior_routine_maintenance_usd",
        "prior_cost_per_room",
    ),
    "geography": (
        "division_code",
        "cbsa_code",
    ),
}

ABLATION_CONFIGS: dict[str, tuple[str, ...]] = {
    "structural_only": ("structural",),
    "structural_socioeconomic": ("structural", "socioeconomic"),
    "structural_prior": ("structural", "prior_maintenance"),
    "all_except_prior": (
        "structural",
        "systems",
        "condition",
        "socioeconomic",
        "geography",
    ),
    "all": (
        "structural",
        "systems",
        "condition",
        "socioeconomic",
        "prior_maintenance",
        "geography",
    ),
}


def combined_feature_map(include_derived: bool) -> tuple[tuple[str, str, str], ...]:
    if not include_derived:
        return FEATURE_MAP
    return FEATURE_MAP + DERIVED_FEATURE_MAP


def enrich_snapshot(snapshot: dict[str, str]) -> dict[str, str]:
    """Add derived numeric fields using only earlier-wave snapshot information."""
    enriched = dict(snapshot)
    wave_year = _optional_int(snapshot.get("source_wave_year"))
    year_built = _optional_int(snapshot.get("year_built"))
    total_rooms = _optional_float(snapshot.get("total_rooms"))
    bedrooms = _optional_float(snapshot.get("bedrooms"))
    prior_cost = _optional_float(snapshot.get("prior_routine_maintenance_usd"))

    if wave_year is not None and year_built is not None:
        enriched["property_age_years"] = str(max(wave_year - year_built, 0))
    else:
        enriched["property_age_years"] = ""

    if prior_cost is not None:
        enriched["log_prior_routine_maintenance_usd"] = format(
            math.log1p(prior_cost), ".17g"
        )
        room_denominator = max(total_rooms, 1.0) if total_rooms is not None else 1.0
        enriched["prior_cost_per_room"] = format(prior_cost / room_denominator, ".17g")
    else:
        enriched["log_prior_routine_maintenance_usd"] = ""
        enriched["prior_cost_per_room"] = ""

    if total_rooms is not None and bedrooms is not None:
        enriched["rooms_per_bedroom"] = format(
            total_rooms / max(bedrooms, 1.0), ".17g"
        )
    else:
        enriched["rooms_per_bedroom"] = ""

    enriched["condition_defect_count"] = str(_condition_defect_count(snapshot))
    return enriched


def _condition_defect_count(snapshot: dict[str, str]) -> int:
    count = 0
    for name in CONDITION_CODE_FIELDS:
        raw = snapshot.get(name, "")
        if raw == "":
            continue
        try:
            if int(raw) >= 2:
                count += 1
        except ValueError:
            continue
    return count


def _optional_int(raw: str | None) -> int | None:
    if raw is None or raw == "":
        return None
    return int(raw)


def _optional_float(raw: str | None) -> float | None:
    if raw is None or raw == "":
        return None
    return float(raw)


def feature_group_members(group_names: tuple[str, ...]) -> set[str]:
    members: set[str] = set()
    for group_name in group_names:
        members.update(FEATURE_GROUPS[group_name])
    return members


def matrix_columns_for_groups(
    preprocessor: dict[str, Any], group_names: tuple[str, ...]
) -> list[str]:
    allowed = feature_group_members(group_names)
    selected: list[str] = []
    for parameter in preprocessor["feature_parameters"]:
        if parameter["feature_name"] not in allowed:
            continue
        if parameter["value_feature_included"]:
            if parameter["source_type"] == "number":
                selected.append(parameter["value_output_column"])
            else:
                encoder = parameter["encoder"]
                selected.extend(encoder["category_output_columns"])
                selected.append(encoder["reserved_missing_output_column"])
                selected.append(encoder["reserved_unknown_output_column"])
        selected.append(parameter["missing_indicator_column"])
    return selected
