"""Model loading and vehicle class prediction."""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

from .config import (
    CLASS_NAMES,
    CONFIDENCE_WARN_THRESHOLD,
    MODEL_PATH,
)
from .preprocessing import decode_image_bytes, load_image, preprocess_batch, preprocess_image

logger = logging.getLogger(__name__)


class VehicleClassifier:
    """Thin wrapper around a Keras .h5 vehicle classifier."""

    def __init__(self, model_path: Optional[Path] = None) -> None:
        self.model_path = Path(model_path or MODEL_PATH)
        self._model = None

    @property
    def ready(self) -> bool:
        return self.model_path.exists()

    def load(self):
        if self._model is not None:
            return self._model
        if not self.ready:
            raise FileNotFoundError(
                f"Model not found at {self.model_path}. "
                "Place vehicle_classifier_ZAM_main.h5 in the package or project root."
            )
        from keras.models import load_model  # lazy import

        logger.info("Loading model from %s", self.model_path)
        self._model = load_model(str(self.model_path))
        return self._model

    def predict_array(self, batch: np.ndarray, top_k: int = 4) -> List[Dict]:
        model = self.load()
        probs = model.predict(batch, verbose=0)
        results: List[Dict] = []
        k = max(1, min(top_k, len(CLASS_NAMES)))
        for row in probs:
            order = np.argsort(row)[::-1][:k]
            top = [
                {
                    "label": CLASS_NAMES[int(i)],
                    "confidence": float(row[int(i)]),
                }
                for i in order
            ]
            best = top[0]
            results.append(
                {
                    "label": best["label"],
                    "confidence": best["confidence"],
                    "low_confidence": best["confidence"] < CONFIDENCE_WARN_THRESHOLD,
                    "top_k": top,
                    "probabilities": {
                        CLASS_NAMES[i]: float(row[i]) for i in range(len(CLASS_NAMES))
                    },
                }
            )
        return results

    def predict_image(self, image: np.ndarray, top_k: int = 4) -> Dict:
        batch = preprocess_image(image)
        return self.predict_array(batch, top_k=top_k)[0]

    def predict_path(self, path: str | Path, top_k: int = 4) -> Dict:
        return self.predict_image(load_image(path), top_k=top_k)

    def predict_bytes(self, contents: bytes, top_k: int = 4) -> Dict:
        return self.predict_image(decode_image_bytes(contents), top_k=top_k)

    def predict_bytes_batch(self, payloads: List[bytes], top_k: int = 4) -> List[Dict]:
        images = [decode_image_bytes(p) for p in payloads]
        batch = preprocess_batch(images)
        return self.predict_array(batch, top_k=top_k)


@lru_cache(maxsize=1)
def get_classifier() -> VehicleClassifier:
    return VehicleClassifier()
