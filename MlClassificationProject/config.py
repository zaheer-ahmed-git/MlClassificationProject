"""Shared configuration for vehicle image classification."""

from __future__ import annotations

import os
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_DIR.parent

# Class order must match the trained model output indices
CLASS_NAMES = ["bike", "buses", "car", "truck"]

IMAGE_SIZE = (224, 224)
MODEL_FILENAME = os.getenv("VEHICLE_MODEL_PATH", "vehicle_classifier_ZAM_main.h5")
MODEL_PATH = Path(MODEL_FILENAME)
if not MODEL_PATH.is_absolute():
    # Prefer package dir, then project root
    candidates = [PACKAGE_DIR / MODEL_FILENAME, PROJECT_ROOT / MODEL_FILENAME]
    MODEL_PATH = next((p for p in candidates if p.exists()), PACKAGE_DIR / MODEL_FILENAME)

DATASET_DIR = PACKAGE_DIR / "dataset"
DEFAULT_BATCH_SIZE = 16
CONFIDENCE_WARN_THRESHOLD = float(os.getenv("CONFIDENCE_WARN_THRESHOLD", "0.55"))
