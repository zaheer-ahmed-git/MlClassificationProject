"""Small standard-library helpers shared by dataset builders."""

from __future__ import annotations

import csv
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Iterable
from uuid import NAMESPACE_URL, uuid5


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest for a file without loading it all into memory."""
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def stable_id(kind: str, *parts: object) -> str:
    """Create a deterministic opaque identifier for a derived record."""
    value = "|".join(str(part) for part in (kind, *parts))
    return str(uuid5(NAMESPACE_URL, f"caip-maintenance/{value}"))


def asset_token(source_id: str, native_id: str) -> str:
    """Tokenize a source-native public identifier before analytical export."""
    material = f"caip-public-asset-v1|{source_id}|{native_id}".encode()
    return f"asset_{sha256(material).hexdigest()[:24]}"


def row_digest(row: dict[str, str]) -> str:
    """Hash the complete raw row for lineage without copying its contents."""
    canonical = json.dumps(row, sort_keys=True, separators=(",", ":"))
    return sha256(canonical.encode("utf-8")).hexdigest()


def write_csv(path: Path, fieldnames: list[str], rows: Iterable[dict[str, Any]]) -> int:
    """Write deterministic UTF-8 CSV and return its row count."""
    count = 0
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: _serialize(row.get(field)) for field in fieldnames})
            count += 1
    return count


def _serialize(value: Any) -> Any:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return ""
    return value

