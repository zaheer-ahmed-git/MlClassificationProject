#!/usr/bin/env python3
"""CLI: classify one or more local vehicle images."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from MlClassificationProject.inference import VehicleClassifier  # noqa: E402
from MlClassificationProject.preprocessing import inventory_dataset  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Predict vehicle class from image files")
    parser.add_argument("images", nargs="*", help="Image paths (jpg/png)")
    parser.add_argument("--top-k", type=int, default=4)
    parser.add_argument("--inventory", action="store_true", help="Print dataset class counts")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.inventory:
        info = inventory_dataset()
        print(json.dumps(info, indent=2) if args.json else info)
        return

    if not args.images:
        parser.error("Provide image paths or --inventory")

    clf = VehicleClassifier()
    outputs = []
    for path in args.images:
        result = clf.predict_path(path, top_k=args.top_k)
        result["source"] = path
        outputs.append(result)

    if args.json:
        print(json.dumps(outputs, indent=2))
        return

    for item in outputs:
        flag = " (low confidence)" if item["low_confidence"] else ""
        print(f"{item['source']}: {item['label']} ({item['confidence']:.3f}){flag}")


if __name__ == "__main__":
    main()
