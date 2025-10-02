"""Image loading and preprocessing helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Tuple, Union

import cv2
import numpy as np

from .config import CLASS_NAMES, DATASET_DIR, IMAGE_SIZE

PathLike = Union[str, Path]


def decode_image_bytes(contents: bytes) -> np.ndarray:
    """Decode raw image bytes to a BGR uint8 array."""
    if not contents:
        raise ValueError("Empty image payload.")
    nparr = np.frombuffer(contents, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Could not decode image. Use JPG/PNG/BMP.")
    return image


def load_image(path: PathLike) -> np.ndarray:
    image = cv2.imread(str(path))
    if image is None:
        raise FileNotFoundError(f"Could not read image: {path}")
    return image


def preprocess_image(
    image: np.ndarray,
    size: Tuple[int, int] = IMAGE_SIZE,
) -> np.ndarray:
    """Resize, normalize to [0, 1], and add batch dimension."""
    if image is None or image.size == 0:
        raise ValueError("Invalid image array.")
    resized = cv2.resize(image, size)
    normalized = resized.astype("float32") / 255.0
    return np.expand_dims(normalized, axis=0)


def preprocess_batch(
    images: Iterable[np.ndarray],
    size: Tuple[int, int] = IMAGE_SIZE,
) -> np.ndarray:
    """Stack multiple images into a single batch tensor."""
    batch = [preprocess_image(img, size=size)[0] for img in images]
    if not batch:
        raise ValueError("No images provided for batch preprocessing.")
    return np.stack(batch, axis=0)


def inventory_dataset(dataset_dir: PathLike = DATASET_DIR) -> dict:
    """Count images per class folder under the local dataset directory."""
    root = Path(dataset_dir)
    counts: dict = {}
    total = 0
    for name in CLASS_NAMES:
        folder = root / name
        if not folder.is_dir():
            counts[name] = 0
            continue
        n = sum(1 for p in folder.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp"})
        counts[name] = n
        total += n
    return {"classes": counts, "total": total, "path": str(root)}


def list_sample_paths(dataset_dir: PathLike = DATASET_DIR, limit_per_class: int = 3) -> List[Path]:
    root = Path(dataset_dir)
    paths: List[Path] = []
    for name in CLASS_NAMES:
        folder = root / name
        if not folder.is_dir():
            continue
        files = sorted(
            p for p in folder.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp"}
        )
        paths.extend(files[:limit_per_class])
    return paths
