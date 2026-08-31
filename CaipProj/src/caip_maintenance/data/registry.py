"""Declarative public-source registry loading and validation."""

from __future__ import annotations

from pathlib import Path
import tomllib
from typing import Any


REQUIRED_SOURCE_FIELDS = {
    "source_id",
    "title",
    "publisher",
    "release",
    "status",
    "role",
    "label_fidelity",
    "geography",
    "native_grain",
    "calendar",
    "currency",
    "access_class",
    "license_status",
    "redistribution_allowed",
    "native_key",
    "sentinels",
    "landing_url",
}


def load_registry(path: Path) -> dict[str, Any]:
    """Load and validate the TOML source registry."""
    with path.open("rb") as handle:
        registry = tomllib.load(handle)
    sources = registry.get("sources", [])
    if not 5 <= len(sources) <= 10:
        raise ValueError("source registry must contain between 5 and 10 sources")
    ids: set[str] = set()
    for source in sources:
        missing = REQUIRED_SOURCE_FIELDS.difference(source)
        if missing:
            raise ValueError(
                f"source {source.get('source_id', '<unknown>')} misses {sorted(missing)}"
            )
        source_id = source["source_id"]
        if source_id in ids:
            raise ValueError(f"duplicate source_id: {source_id}")
        ids.add(source_id)
        if source["native_key"].strip() == "":
            raise ValueError(f"source {source_id} has an empty native key declaration")
    return registry


def find_source(registry: dict[str, Any], source_id: str) -> dict[str, Any]:
    """Return one registered source or fail clearly."""
    for source in registry["sources"]:
        if source["source_id"] == source_id:
            return source
    raise KeyError(f"unregistered source: {source_id}")
