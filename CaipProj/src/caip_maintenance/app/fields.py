"""Form field metadata for the Streamlit decision-support demo."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class FormField:
    name: str
    label: str
    kind: str  # number | code | wave_year
    section: str
    help_text: str
    categories: tuple[str, ...] = ()
    default: str | float | int | None = None
    min_value: float | None = None
    max_value: float | None = None


FIELD_LABELS: dict[str, tuple[str, str]] = {
    "source_wave_year": ("Survey year (facts)", "Year when property facts were recorded"),
    "tenure_code": ("Tenure", "Owner or renter category from the survey codebook"),
    "building_type_code": ("Building type", "Housing type code (maps to WAPDA category groups)"),
    "year_built": ("Year built", "Construction year"),
    "unit_size_code": ("Unit size code", "Survey size category"),
    "total_rooms": ("Total rooms", "Room count"),
    "bathrooms_code": ("Bathrooms code", "Bathroom category"),
    "bedrooms": ("Bedrooms", "Bedroom count"),
    "unit_floors": ("Floors in unit", "Number of floors"),
    "foundation_type_code": ("Foundation type", "Foundation category"),
    "garage_code": ("Garage", "Garage category"),
    "heating_type_code": ("Heating type", "Primary heating system"),
    "heating_fuel_code": ("Heating fuel", "Fuel used for heating"),
    "primary_air_conditioning_code": ("Air conditioning", "Primary AC type"),
    "sewage_type_code": ("Sewage type", "Sewage/disposal type"),
    "lot_size_code": ("Lot size code", "Lot size category"),
    "owns_lot_code": ("Owns lot", "Lot ownership code"),
    "roof_leak_code": ("Roof leak", "0 = none, higher = worse"),
    "roof_hole_code": ("Roof hole", "0 = none, higher = worse"),
    "roof_sag_code": ("Roof sag", "0 = none, higher = worse"),
    "roof_shingle_condition_code": ("Roof shingles", "0 = good, higher = worse"),
    "sewage_breakdown_code": ("Sewage breakdown", "0 = none, higher = worse"),
    "household_income_usd": ("Household income (USD)", "Annual household income"),
    "prior_routine_maintenance_usd": (
        "Prior routine maintenance (USD)",
        "Maintenance spent in the previous survey period",
    ),
    "division_code": ("Region division", "Census division code"),
    "cbsa_code": ("Metro area code", "CBSA code"),
}


SECTION_ORDER = (
    "Basics",
    "Size",
    "Systems",
    "Condition",
    "Cost history",
    "Location",
)


def form_fields_from_preprocessor(preprocessor: dict[str, Any]) -> list[FormField]:
    """Build Streamlit inputs from the frozen preprocessor contract."""
    fields: list[FormField] = []
    fields.append(
        FormField(
            name="source_wave_year",
            label=FIELD_LABELS["source_wave_year"][0],
            kind="wave_year",
            section="Basics",
            help_text=FIELD_LABELS["source_wave_year"][1],
            categories=("2015", "2017", "2019", "2021"),
            default="2019",
        )
    )
    for parameter in preprocessor["feature_parameters"]:
        name = parameter["feature_name"]
        if name == "survey_weight":
            continue
        label, help_text = FIELD_LABELS.get(name, (name.replace("_", " ").title(), ""))
        section = _section_for(name)
        if parameter["source_type"] == "number":
            default = _numeric_default(name)
            fields.append(
                FormField(
                    name=name,
                    label=label,
                    kind="number",
                    section=section,
                    help_text=help_text,
                    default=default,
                    min_value=0 if "usd" in name else None,
                )
            )
        elif not parameter.get("value_feature_included", True):
            # e.g. roof_leak_code: only a missingness flag enters the model matrix.
            continue
        else:
            encoder = parameter.get("encoder")
            if encoder is None:
                continue
            categories = tuple(encoder["training_categories"])
            fields.append(
                FormField(
                    name=name,
                    label=label,
                    kind="code",
                    section=section,
                    help_text=help_text,
                    categories=categories,
                    default=categories[0] if categories else "",
                )
            )
    return fields


def default_snapshot(preprocessor: dict[str, Any]) -> dict[str, str]:
    snapshot: dict[str, str] = {}
    for field in form_fields_from_preprocessor(preprocessor):
        if field.default is None:
            snapshot[field.name] = ""
        else:
            snapshot[field.name] = str(field.default)
    return snapshot


def _section_for(name: str) -> str:
    if name in {"tenure_code", "building_type_code", "year_built"}:
        return "Basics"
    if name in {
        "unit_size_code",
        "total_rooms",
        "bathrooms_code",
        "bedrooms",
        "unit_floors",
        "foundation_type_code",
        "garage_code",
        "lot_size_code",
        "owns_lot_code",
    }:
        return "Size"
    if name in {
        "heating_type_code",
        "heating_fuel_code",
        "primary_air_conditioning_code",
        "sewage_type_code",
    }:
        return "Systems"
    if name.startswith("roof_") or name == "sewage_breakdown_code":
        return "Condition"
    if name in {"household_income_usd", "prior_routine_maintenance_usd"}:
        return "Cost history"
    if name in {"division_code", "cbsa_code"}:
        return "Location"
    return "Basics"


def _numeric_default(name: str) -> float | int:
    defaults = {
        "year_built": 1985,
        "total_rooms": 6,
        "bedrooms": 3,
        "unit_floors": 1,
        "household_income_usd": 60000,
        "prior_routine_maintenance_usd": 500,
    }
    return defaults.get(name, 0)
