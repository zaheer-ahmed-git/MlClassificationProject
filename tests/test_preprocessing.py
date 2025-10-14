import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from MlClassificationProject.config import CLASS_NAMES, IMAGE_SIZE
from MlClassificationProject.preprocessing import (
    decode_image_bytes,
    inventory_dataset,
    preprocess_batch,
    preprocess_image,
)


def test_preprocess_image_shape():
    image = np.zeros((100, 80, 3), dtype=np.uint8)
    batch = preprocess_image(image)
    assert batch.shape == (1, IMAGE_SIZE[0], IMAGE_SIZE[1], 3)
    assert batch.dtype == np.float32
    assert 0.0 <= float(batch.max()) <= 1.0


def test_preprocess_batch_stacks():
    images = [np.zeros((50, 50, 3), dtype=np.uint8) for _ in range(3)]
    batch = preprocess_batch(images)
    assert batch.shape[0] == 3


def test_decode_image_bytes_rejects_empty():
    try:
        decode_image_bytes(b"")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_inventory_has_expected_classes():
    info = inventory_dataset()
    assert set(info["classes"].keys()) == set(CLASS_NAMES)
    assert info["total"] >= 0
