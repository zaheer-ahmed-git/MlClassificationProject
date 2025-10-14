#!/usr/bin/env python3
"""Print a short inventory of the local vehicle dataset."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from MlClassificationProject.preprocessing import inventory_dataset  # noqa: E402


def main() -> None:
    info = inventory_dataset()
    print(json.dumps(info, indent=2))
    print(f"\nTotal images: {info['total']}")
    for name, count in info["classes"].items():
        print(f"  {name:8s} {count}")


if __name__ == "__main__":
    main()
