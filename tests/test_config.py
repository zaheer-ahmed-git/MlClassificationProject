import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from MlClassificationProject import CLASS_NAMES, IMAGE_SIZE, __version__
from MlClassificationProject.config import CONFIDENCE_WARN_THRESHOLD


def test_class_order_stable():
    assert CLASS_NAMES == ["bike", "buses", "car", "truck"]


def test_image_size():
    assert IMAGE_SIZE == (224, 224)


def test_version_and_threshold():
    assert __version__
    assert 0.0 < CONFIDENCE_WARN_THRESHOLD <= 1.0
