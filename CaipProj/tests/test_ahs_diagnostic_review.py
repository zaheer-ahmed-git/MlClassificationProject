"""Unit tests for AHS residual/subgroup/weight/utility review helpers."""

from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from caip_maintenance.evaluation.ahs_diagnostic_review import (  # noqa: E402
    calculate_unweighted_metrics,
    calculate_weighted_metrics,
)


class AhsDiagnosticMetricTests(unittest.TestCase):
    def test_unweighted_metrics_hand_calculation(self) -> None:
        actual = [0.0, 100.0, 2000.0]
        predicted = [10.0, 50.0, 1500.0]
        metrics = calculate_unweighted_metrics(actual, predicted, threshold=1428.0)
        self.assertEqual(metrics["count"], 3)
        self.assertAlmostEqual(metrics["mae_usd"], (10 + 50 + 500) / 3)
        self.assertAlmostEqual(
            metrics["rmse_usd"], math.sqrt((100 + 2500 + 250000) / 3)
        )
        self.assertEqual(metrics["high_cost_true_positive"], 1)
        self.assertEqual(metrics["high_cost_false_negative"], 0)
        self.assertEqual(metrics["high_cost_false_positive"], 0)
        self.assertAlmostEqual(metrics["high_cost_precision"], 1.0)
        self.assertAlmostEqual(metrics["high_cost_recall"], 1.0)

    def test_weighted_metrics_change_mae_order(self) -> None:
        actual = [100.0, 100.0, 1000.0]
        pred_a = [100.0, 100.0, 2000.0]
        pred_b = [200.0, 200.0, 1000.0]
        equal_weights = [1.0, 1.0, 1.0]
        front_loaded_weights = [10.0, 10.0, 1.0]
        equal_a = calculate_weighted_metrics(actual, pred_a, equal_weights, 1428.0)
        equal_b = calculate_weighted_metrics(actual, pred_b, equal_weights, 1428.0)
        skewed_a = calculate_weighted_metrics(actual, pred_a, front_loaded_weights, 1428.0)
        skewed_b = calculate_weighted_metrics(actual, pred_b, front_loaded_weights, 1428.0)
        self.assertLess(equal_b["mae_usd"], equal_a["mae_usd"])
        self.assertLess(skewed_a["mae_usd"], skewed_b["mae_usd"])

    def test_weighted_metrics_reject_nonpositive_weights(self) -> None:
        with self.assertRaises(ValueError):
            calculate_weighted_metrics([1.0], [1.0], [0.0], 1428.0)


if __name__ == "__main__":
    unittest.main()
