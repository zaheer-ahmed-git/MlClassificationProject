"""Tests for single-row AHS inference and the Streamlit scoring path."""

from __future__ import annotations

import csv
import unittest
from pathlib import Path

from caip_maintenance.app.fields import form_fields_from_preprocessor
from caip_maintenance.app.inference import load_inference_bundle, predict_snapshot
from caip_maintenance.features.ahs_inference import (
    feature_column_names,
    load_preprocessor_artifact,
    transform_snapshot,
    vector_from_transform,
)


ROOT = Path(__file__).resolve().parents[1]
PREPROCESSOR_ID = "ahs-feature-engineering-v1"
EXPERIMENT_ID = "ahs-xgboost-tuning-v1"


def _artifacts_available() -> bool:
    return (
        ROOT
        / "data/processed/preprocessing/public-corpus-v0.2.0-ahs/ahs-grouped-temporal-v1"
        / PREPROCESSOR_ID
        / "preprocessor.json"
    ).is_file() and (
        ROOT
        / "artifacts/experiments/public-corpus-v0.2.0-ahs/ahs-grouped-temporal-v1"
        / PREPROCESSOR_ID
        / EXPERIMENT_ID
        / "models/xgboost.joblib"
    ).is_file()


@unittest.skipUnless(_artifacts_available(), "local preprocessor and experiment artifacts required")
class AppInferenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.preprocessor = load_preprocessor_artifact(ROOT, PREPROCESSOR_ID)
        self.bundle = load_inference_bundle(ROOT)
        self.snapshot_id, self.snapshot, self.expected_vector = self._load_reference_row()

    def _load_reference_row(self) -> tuple[str, dict[str, str], list[float]]:
        assignment_path = (
            ROOT
            / "data/processed/splits/public-corpus-v0.2.0-ahs/ahs-grouped-temporal-v1"
            / "split_assignment.csv"
        )
        matrix_path = (
            ROOT
            / "data/processed/preprocessing/public-corpus-v0.2.0-ahs/ahs-grouped-temporal-v1"
            / PREPROCESSOR_ID
            / "feature_matrix.csv"
        )
        snapshot_path = (
            ROOT / "data/processed/releases/public-corpus-v0.2.0-ahs/property_period_snapshot.csv"
        )
        columns = feature_column_names(self.preprocessor)
        with assignment_path.open(encoding="utf-8", newline="") as handle:
            snapshot_id = next(
                row["snapshot_id"]
                for row in csv.DictReader(handle)
                if row["split_name"] == "training"
            )
        with snapshot_path.open(encoding="utf-8", newline="") as handle:
            snapshot = next(
                row for row in csv.DictReader(handle) if row["snapshot_id"] == snapshot_id
            )
        with matrix_path.open(encoding="utf-8", newline="") as handle:
            matrix_row = next(
                row for row in csv.DictReader(handle) if row["snapshot_id"] == snapshot_id
            )
        expected = [float(matrix_row[name]) for name in columns]
        return snapshot_id, snapshot, expected

    def test_form_fields_build_without_encoder_crash(self) -> None:
        fields = form_fields_from_preprocessor(self.preprocessor)
        names = {field.name for field in fields}
        self.assertIn("building_type_code", names)
        self.assertNotIn("roof_leak_code", names)

    def test_single_row_transform_matches_frozen_matrix(self) -> None:
        transform = transform_snapshot(self.snapshot, self.preprocessor)
        vector = vector_from_transform(transform, self.preprocessor)
        for index, (expected, actual) in enumerate(zip(self.expected_vector, vector)):
            self.assertAlmostEqual(expected, actual, places=6, msg=f"column index {index}")

    def test_predict_returns_baselines_and_fitted_model(self) -> None:
        result = predict_snapshot(self.bundle, self.snapshot)
        self.assertIn("type_median", result.predictions_usd)
        self.assertIn("prior_cost", result.predictions_usd)
        self.assertIn("xgboost", result.predictions_usd)
        self.assertEqual(result.high_cost_threshold_usd, 1428.0)
        self.assertTrue(all(value >= 0 for value in result.predictions_usd.values()))
        self.assertIn("WAPDA", result.disclaimer)


if __name__ == "__main__":
    unittest.main()
