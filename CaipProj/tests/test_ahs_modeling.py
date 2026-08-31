from __future__ import annotations

import csv
import json
import math
from pathlib import Path
import shutil
import tempfile
import unittest

from caip_maintenance.data.common import sha256_file, write_csv
from caip_maintenance.modeling.ahs_experiment import (
    EXPERIMENT_ID,
    LOG1P_EXPERIMENT_ID,
    PREDICTION_FIELDS,
    SYSTEM_NAMES,
    audit_ahs_experiment,
    build_ahs_experiment,
    calculate_metrics,
)


RELEASE = "public-corpus-v0.2.0-ahs"
SPLIT = "ahs-grouped-temporal-v1"
PREPROCESSOR = "ahs-training-fold-v1"
EXPERIMENT = EXPERIMENT_ID
LOG1P_EXPERIMENT = LOG1P_EXPERIMENT_ID
TASK = "future_routine_cost_proxy_v1"


class AHSModelingTests(unittest.TestCase):
    def test_metric_fixture(self) -> None:
        metrics = calculate_metrics([0.0, 2.0], [1.0, 4.0], 2.0)
        self.assertEqual(metrics["count"], 2)
        self.assertEqual(metrics["mae_usd"], 1.5)
        self.assertAlmostEqual(metrics["rmse_usd"], math.sqrt(2.5))
        self.assertEqual(metrics["high_cost_true_positive"], 1)
        self.assertEqual(metrics["high_cost_false_positive"], 0)
        self.assertEqual(metrics["high_cost_false_negative"], 0)
        self.assertEqual(metrics["high_cost_precision"], 1.0)
        self.assertEqual(metrics["high_cost_recall"], 1.0)
        self.assertEqual(metrics["high_cost_f1"], 1.0)

    def test_training_only_build_persistence_and_audit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _write_fixture(root)
            output = build_ahs_experiment(root)

            manifest = json.loads(
                (output / "experiment_manifest.json").read_text(encoding="utf-8")
            )
            metrics = json.loads((output / "metrics.json").read_text(encoding="utf-8"))
            baselines = json.loads(
                (output / "baseline_parameters.json").read_text(encoding="utf-8")
            )
            self.assertEqual(manifest["fit_contract"]["fit_split"], "training")
            self.assertFalse(manifest["fit_contract"]["held_out_labels_used_for_fit"])
            self.assertFalse(manifest["fit_contract"]["hyperparameter_search"])
            self.assertEqual(manifest["evaluation_contract"]["high_cost_threshold_usd"], 1428.0)
            self.assertEqual(manifest["claim_boundary"]["is_wapda_data"], False)
            self.assertEqual(baselines["training_median"]["prediction_usd"], 450.0)
            self.assertEqual(baselines["type_median"]["group_median_usd"], {"01": 400.0, "02": 500.0})
            self.assertEqual(metrics["system_order"], SYSTEM_NAMES)
            self.assertEqual(
                set(metrics["results"]["random_forest"]),
                {"primary", "pre_2023_cap_sensitivity"},
            )
            self.assertEqual(
                metrics["results"]["random_forest"]["primary"]["validation"]["count"],
                4,
            )
            self.assertEqual(
                metrics["results"]["random_forest"]["pre_2023_cap_sensitivity"]["test"]["count"],
                2,
            )
            report = audit_ahs_experiment(root, output)
            self.assertEqual(report["status"], "passed", report)
            self.assertEqual(report["summary"], {"passed": 11, "failed": 0})
            with self.assertRaises(FileExistsError):
                build_ahs_experiment(root)

    def test_held_out_label_changes_do_not_change_any_prediction(self) -> None:
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            first_root = Path(first)
            second_root = Path(second)
            _write_fixture(first_root)
            _write_fixture(second_root, held_out_offset=7777.0)
            first_output = build_ahs_experiment(first_root)
            second_output = build_ahs_experiment(second_root)

            first_predictions = _read_prediction_columns(first_output / "predictions.csv")
            second_predictions = _read_prediction_columns(second_output / "predictions.csv")
            self.assertEqual(first_predictions, second_predictions)

            first_baselines = (first_output / "baseline_parameters.json").read_text(
                encoding="utf-8"
            )
            second_baselines = (second_output / "baseline_parameters.json").read_text(
                encoding="utf-8"
            )
            self.assertEqual(first_baselines, second_baselines)
            self.assertNotEqual(
                (first_output / "metrics.json").read_text(encoding="utf-8"),
                (second_output / "metrics.json").read_text(encoding="utf-8"),
            )

    def test_log1p_trains_on_transform_and_scores_in_usd(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _write_fixture(root, experiment_id=LOG1P_EXPERIMENT)
            output = build_ahs_experiment(root, experiment_id=LOG1P_EXPERIMENT)

            manifest = json.loads(
                (output / "experiment_manifest.json").read_text(encoding="utf-8")
            )
            metrics = json.loads((output / "metrics.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["experiment_id"], LOG1P_EXPERIMENT)
            self.assertEqual(manifest["fit_contract"]["target_transform"], "log1p")
            self.assertEqual(
                manifest["fit_contract"]["prediction_inverse_transform"], "expm1"
            )
            self.assertEqual(
                manifest["evaluation_contract"]["metrics_evaluated_in"], "original_usd"
            )
            self.assertEqual(metrics["target_transform"], "log1p")
            self.assertEqual(metrics["metrics_evaluated_in"], "original_usd")
            self.assertIn("mae_usd", metrics["results"]["linear_regression"]["primary"]["test"])
            report = audit_ahs_experiment(root, output)
            self.assertEqual(report["status"], "passed", report)

            import joblib
            import numpy as np

            model = joblib.load(output / "models" / "linear_regression.joblib")
            features = np.loadtxt(
                root
                / "data"
                / "processed"
                / "preprocessing"
                / RELEASE
                / SPLIT
                / PREPROCESSOR
                / "feature_matrix.csv",
                delimiter=",",
                skiprows=1,
                usecols=range(1, 9),
            )
            raw_predict = model.predict(features)
            stored = _read_prediction_columns(output / "predictions.csv")
            for index, row in enumerate(stored):
                self.assertAlmostEqual(
                    float(row["prediction_linear_regression_usd"]),
                    float(np.expm1(raw_predict[index])),
                    places=12,
                )


def _write_fixture(
    root: Path,
    held_out_offset: float = 0.0,
    experiment_id: str = EXPERIMENT,
) -> None:
    config_dir = root / "configs" / "experiments"
    config_dir.mkdir(parents=True)
    config_names = {
        EXPERIMENT: "ahs_baselines_models_v1.toml",
        LOG1P_EXPERIMENT: "ahs_baselines_models_log1p_v1.toml",
    }
    source_config = (
        Path(__file__).resolve().parents[1]
        / "configs"
        / "experiments"
        / config_names[experiment_id]
    )
    shutil.copyfile(source_config, config_dir / source_config.name)

    directory = (
        root
        / "data"
        / "processed"
        / "preprocessing"
        / RELEASE
        / SPLIT
        / PREPROCESSOR
    )
    directory.mkdir(parents=True)
    feature_columns = [
        "snapshot_id",
        "building_type_code__category_000",
        "building_type_code__category_001",
        "building_type_code__category_missing",
        "building_type_code__category_unknown",
        "building_type_code__is_missing",
        "prior_routine_maintenance_usd__standardized",
        "prior_routine_maintenance_usd__is_missing",
        "age__standardized",
    ]
    targets = [
        0.0,
        100.0,
        200.0,
        300.0,
        400.0,
        500.0,
        600.0,
        1428.0,
        1428.0,
        2000.0,
        200.0,
        1500.0,
        3000.0,
        100.0,
        500.0,
        1428.0,
        4000.0,
        0.0,
    ]
    splits = ["training"] * 10 + ["validation"] * 4 + ["test"] * 4
    waves = [2017] * 10 + [2019] * 4 + [2021, 2021, 2023, 2023]
    rows = []
    target_rows = []
    for index, (target, split, wave) in enumerate(zip(targets, splits, waves)):
        snapshot_id = f"snapshot_{index:03d}"
        type_code = "01" if index % 2 == 0 else "02"
        if index == 17:
            type_values = [0, 0, 0, 1, 0]
        elif index == 16:
            type_values = [0, 0, 1, 0, 1]
        else:
            type_values = [int(type_code == "01"), int(type_code == "02"), 0, 0, 0]
        prior_missing = index in {3, 11}
        prior = 0.0 if prior_missing else float(index * 75)
        rows.append(
            {
                "snapshot_id": snapshot_id,
                **dict(zip(feature_columns[1:6], type_values)),
                "prior_routine_maintenance_usd__standardized": prior,
                "prior_routine_maintenance_usd__is_missing": int(prior_missing),
                "age__standardized": float(index - 5),
            }
        )
        current_target = target + (held_out_offset if split != "training" else 0.0)
        target_rows.append(
            {
                "snapshot_id": snapshot_id,
                "split_name": split,
                "task_id": TASK,
                "target_amount_local_nominal": current_target,
                "target_currency": "USD",
                "label_wave_year": wave,
                "include_in_primary_metrics": True,
                "include_in_pre_2023_cap_sensitivity": wave < 2023,
                "is_high_cost": current_target >= 1428.0,
                "target_was_imputed": False,
                "target_was_clipped": False,
            }
        )

    preprocessor = {
        "dataset_release": RELEASE,
        "split_id": SPLIT,
        "preprocessor_id": PREPROCESSOR,
        "task_id": TASK,
        "fit_split": "training",
        "distribution": "local-analysis-only",
        "model_fitted": False,
        "target_policy": {
            "cap_sensitivity_metadata_preserved": True,
            "clipping": "prohibited",
            "imputation": "prohibited",
        },
        "high_cost_policy": {
            "threshold_version": "ahs-high-cost-training-top20-v1",
            "threshold_amount_local_nominal": "1428",
            "fit_split": "training",
        },
        "feature_matrix_columns": feature_columns,
        "feature_parameters": [
            {
                "feature_name": "building_type_code",
                "value_feature_included": True,
                "encoder": {
                    "category_output_columns": feature_columns[1:3],
                    "reserved_missing_output_column": feature_columns[3],
                    "reserved_unknown_output_column": feature_columns[4],
                    "training_categories": ["01", "02"],
                    "reserved_missing_token": "__MISSING__",
                    "reserved_unknown_token": "__UNKNOWN__",
                },
            },
            {
                "feature_name": "prior_routine_maintenance_usd",
                "value_feature_included": True,
                "value_output_column": feature_columns[6],
                "missing_indicator_column": feature_columns[7],
                "scaler": {"mean_after_imputation": 0.0, "scale": 1.0},
            },
        ],
    }
    preprocessor_path = directory / "preprocessor.json"
    preprocessor_path.write_text(
        json.dumps(preprocessor, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    feature_path = directory / "feature_matrix.csv"
    write_csv(feature_path, feature_columns, rows)
    target_path = directory / "target_metadata.csv"
    write_csv(target_path, list(target_rows[0]), target_rows)
    manifest = {
        "dataset_release": RELEASE,
        "split_id": SPLIT,
        "preprocessor_id": PREPROCESSOR,
        "task_id": TASK,
        "fit_split": "training",
        "distribution": "local-analysis-only",
        "counts": {"feature_rows": len(rows)},
        "output_sha256": {
            "preprocessor.json": sha256_file(preprocessor_path),
            "feature_matrix.csv": sha256_file(feature_path),
            "target_metadata.csv": sha256_file(target_path),
        },
    }
    (directory / "preprocessing_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _read_prediction_columns(path: Path) -> list[dict[str, str]]:
    fields = [field for field in PREDICTION_FIELDS if field.startswith("prediction_")]
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [{field: row[field] for field in fields} for row in csv.DictReader(handle)]


if __name__ == "__main__":
    unittest.main()
