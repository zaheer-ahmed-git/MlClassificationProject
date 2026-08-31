from __future__ import annotations

import json
from pathlib import Path
import shutil
import tempfile
import unittest

from caip_maintenance.modeling.ahs_xgboost_experiment import (
    EXPERIMENT_ID,
    SYSTEM_NAMES,
    audit_ahs_xgboost_experiment,
    build_ahs_xgboost_experiment,
)
from tests.test_ahs_modeling import PREPROCESSOR, RELEASE, SPLIT, _write_fixture


class AHSXGBoostTests(unittest.TestCase):
    def test_training_only_build_persistence_and_audit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _write_xgboost_fixture(root)
            output = build_ahs_xgboost_experiment(root)

            manifest = json.loads(
                (output / "experiment_manifest.json").read_text(encoding="utf-8")
            )
            metrics = json.loads((output / "metrics.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["experiment_id"], EXPERIMENT_ID)
            self.assertEqual(manifest["fit_contract"]["fit_split"], "training")
            self.assertFalse(manifest["fit_contract"]["held_out_labels_used_for_fit"])
            self.assertEqual(
                manifest["model_contracts"]["xgboost"]["estimator"],
                "xgboost.XGBRegressor",
            )
            self.assertEqual(metrics["system_order"], SYSTEM_NAMES)
            self.assertIn("xgboost", metrics["results"])
            report = audit_ahs_xgboost_experiment(root, output)
            self.assertEqual(report["status"], "passed", report)
            self.assertEqual(report["summary"], {"passed": 11, "failed": 0})


def _write_xgboost_fixture(root: Path) -> None:
    _write_fixture(root)
    config_dir = root / "configs" / "experiments"
    source_config = (
        Path(__file__).resolve().parents[1]
        / "configs"
        / "experiments"
        / "ahs_xgboost_v1.toml"
    )
    shutil.copyfile(source_config, config_dir / source_config.name)


if __name__ == "__main__":
    unittest.main()
