"""Contract tests for the gated, separate AHS longitudinal release."""

from __future__ import annotations

import csv
from decimal import Decimal
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import tomllib
import unittest
import zipfile


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from caip_maintenance.data.ahs import (  # noqa: E402
    DATASET_RELEASE,
    DOCUMENT_FILES,
    FEATURE_MAP,
    TASK_ID,
    harmonize,
)
from caip_maintenance.data.ahs_gate import (  # noqa: E402
    WAVE_ARCHIVES,
    assess_ahs_gate,
)
from caip_maintenance.data.ahs_split import (  # noqa: E402
    SPLIT_ASSIGNMENT_FIELDS,
    SPLIT_ID,
    assign_ahs_splits,
    audit_ahs_split,
)
from caip_maintenance.data.audit import audit_release  # noqa: E402
from caip_maintenance.features.ahs_preprocessing import (  # noqa: E402
    HIGH_COST_THRESHOLD_VERSION,
    PREPROCESSOR_ID,
    TARGET_FIELDS,
    audit_ahs_preprocessing,
    build_ahs_preprocessing,
)


class AhsPipelineTests(unittest.TestCase):
    @staticmethod
    def _row(control: int, wave: int, **overrides: str) -> dict[str, str]:
        row = {source: "1" for _, source, _ in FEATURE_MAP}
        row.update(
            {
                "CONTROL": f"'{control:08d}'",
                "INTSTATUS": "1",
                "TENURE": "1",
                "YRBUILT": "1980",
                "UNITSIZE": "5",
                "TOTROOMS": "6",
                "BATHROOMS": "2",
                "BLD": "2",
                "MAINTAMT": "0" if control == 0 else str(100 + wave - 2015),
                "JMAINTAMT": "0",
                "WEIGHT": "1.5",
            }
        )
        row.update(overrides)
        return row

    def _write_fixture(
        self,
        root: Path,
        linked_units: int = 501,
        terminal_cohorts: bool = False,
        preprocessing_profile: int | None = None,
    ) -> Path:
        raw_dir = (
            root
            / "data"
            / "raw"
            / "public"
            / "ahs_2015_2023"
            / "official_2015_2023"
        )
        raw_dir.mkdir(parents=True)
        fields = ["CONTROL", "INTSTATUS", "TENURE", "MAINTAMT", "JMAINTAMT"]
        fields.extend(source for _, source, _ in FEATURE_MAP if source not in fields)
        for year, archive_name in WAVE_ARCHIVES.items():
            buffer = io.StringIO(newline="")
            writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            rows = []
            for index in range(linked_units):
                overrides = {}
                if terminal_cohorts and index >= 334 and year >= 2021:
                    overrides["TENURE"] = "3"
                elif terminal_cohorts and index >= 167 and year >= 2023:
                    overrides["TENURE"] = "3"
                if preprocessing_profile is not None:
                    if index >= 334:
                        overrides.update(
                            {
                                "HINCP": "-6" if index == 334 else str(10 + index % 2 * 10),
                                "HEATTYPE": str(1 + index % 2),
                                "LEAKOROOF": "-6",
                                "MAINTAMT": str(100 + index % 10),
                            }
                        )
                    else:
                        held_out_scale = 1_000_000 * preprocessing_profile
                        overrides.update(
                            {
                                "HINCP": str(held_out_scale + index),
                                "HEATTYPE": str(90 + preprocessing_profile),
                                "LEAKOROOF": "1",
                                "MAINTAMT": "90000"
                                if index < 167 and year == 2023
                                else str(8000 + preprocessing_profile),
                            }
                        )
                rows.append(self._row(index, year, **overrides))
            writer.writerows(rows)
            writer.writerow(self._row(linked_units, year, INTSTATUS="3"))
            with zipfile.ZipFile(raw_dir / archive_name, "w", zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("household.csv", buffer.getvalue())
        for name in DOCUMENT_FILES:
            path = raw_dir / name
            if not path.exists():
                path.write_bytes(b"test-only official-document fixture\n")
        return raw_dir

    @staticmethod
    def _copy_split_contract(root: Path) -> None:
        config_dir = root / "configs"
        (config_dir / "splits").mkdir(parents=True)
        shutil.copy2(
            PROJECT_ROOT / "configs" / "splits" / "ahs_grouped_temporal_v1.toml",
            config_dir / "splits" / "ahs_grouped_temporal_v1.toml",
        )
        (config_dir / "preprocessing").mkdir()
        shutil.copy2(
            PROJECT_ROOT / "configs" / "preprocessing" / "ahs_training_fold_v1.toml",
            config_dir / "preprocessing" / "ahs_training_fold_v1.toml",
        )
        documentation = root / "Documentation"
        documentation.mkdir()
        shutil.copy2(
            PROJECT_ROOT / "Documentation" / "AHSSemanticLicenseDecision.md",
            documentation / "AHSSemanticLicenseDecision.md",
        )

    def test_declarative_mapping_matches_feature_contract(self) -> None:
        path = PROJECT_ROOT / "configs" / "mappings" / "ahs_2015_2023.toml"
        with path.open("rb") as handle:
            mapping = tomllib.load(handle)
        declared = {
            (target, definition["source"])
            for target, definition in mapping["fields"].items()
        }
        self.assertEqual(declared, {(target, source) for target, source, _ in FEATURE_MAP})
        self.assertEqual(mapping["label_task"], TASK_ID)
        self.assertEqual(mapping["native_key"], "CONTROL")

    def test_declarative_split_contract_matches_implementation(self) -> None:
        schema_path = (
            PROJECT_ROOT / "configs" / "schemas" / "ahs_split_assignment_v1.json"
        )
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        with (
            PROJECT_ROOT / "configs" / "splits" / "ahs_grouped_temporal_v1.toml"
        ).open("rb") as handle:
            split = tomllib.load(handle)

        self.assertEqual(list(schema["fields"]), SPLIT_ASSIGNMENT_FIELDS)
        self.assertEqual(schema["split_id"], split["split_id"])
        self.assertEqual(schema["dataset_release"], split["dataset_release"])
        self.assertEqual(schema["task_id"], split["task_id"])
        self.assertEqual(schema["terminal_wave_assignment"], split["terminal_wave_assignment"])
        self.assertEqual(schema["distribution"], "local-analysis-only")

    def test_declarative_preprocessing_contract_matches_implementation(self) -> None:
        schema = json.loads(
            (
                PROJECT_ROOT / "configs" / "schemas" / "ahs_preprocessing_v1.json"
            ).read_text(encoding="utf-8")
        )
        with (
            PROJECT_ROOT / "configs" / "preprocessing" / "ahs_training_fold_v1.toml"
        ).open("rb") as handle:
            spec = tomllib.load(handle)

        self.assertEqual(schema["preprocessor_id"], PREPROCESSOR_ID)
        self.assertEqual(schema["preprocessor_id"], spec["preprocessor_id"])
        self.assertEqual(schema["dataset_release"], spec["dataset_release"])
        self.assertEqual(schema["split_id"], spec["split_id"])
        self.assertEqual(schema["task_id"], spec["task_id"])
        self.assertEqual(list(schema["target_metadata_fields"]), TARGET_FIELDS)
        self.assertEqual(spec["fit_split"], "training")
        self.assertEqual(spec["high_cost_quantile"], 0.8)
        self.assertEqual(spec["target_imputation"], "prohibited")
        self.assertEqual(spec["target_clipping"], "prohibited")

    def test_gate_and_release_are_longitudinal_separate_and_auditable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_fixture(root)

            gate = assess_ahs_gate(root)
            self.assertEqual(gate["decision"], "go")
            self.assertEqual(gate["distinct_linked_units"], 501)
            self.assertEqual(gate["eligible_pair_rows"], 2004)
            self.assertFalse(gate["native_identifiers_exported"])

            release = harmonize(root)
            report = audit_release(release)
            manifest = json.loads((release / "manifest.json").read_text(encoding="utf-8"))
            labels = self._read(release / "property_period_label.csv")
            snapshots = self._read(release / "property_period_snapshot.csv")

            self.assertEqual(report["status"], "passed")
            self.assertIn("ahs_task_isolated", {check["check_id"] for check in report["checks"]})
            self.assertEqual(len(labels), 2004)
            self.assertEqual(len(snapshots), 2004)
            self.assertTrue(all(row["task_id"] == TASK_ID for row in labels))
            self.assertTrue(all(row["is_exact_wapda_target"] == "false" for row in labels))
            self.assertEqual(manifest["modeling_view"], "ahs_only_separate_from_rhfs")
            self.assertEqual(
                manifest["dataset_status"],
                "local_analysis_only_license_review_pending",
            )
            self.assertEqual(
                {row["source_response_maximum_usd"] for row in labels},
                {"10000", "100000"},
            )

            with self.assertRaises(FileExistsError):
                harmonize(root)

    def test_harmonization_rejects_missing_or_stale_gate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw_dir = self._write_fixture(root)
            with self.assertRaisesRegex(FileNotFoundError, "assess-ahs"):
                harmonize(root)

            assess_ahs_gate(root)
            archive = raw_dir / WAVE_ARCHIVES[2015]
            archive.write_bytes(archive.read_bytes() + b"checksum drift")
            with self.assertRaisesRegex(ValueError, "gate is stale"):
                harmonize(root)

    def test_gate_records_no_go_below_threshold(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_fixture(root, linked_units=3)
            gate = assess_ahs_gate(root, write_result=False)

            self.assertEqual(gate["decision"], "no_go")
            self.assertEqual(gate["distinct_linked_units"], 3)

    def test_grouped_temporal_split_is_leakage_free_and_cap_aware(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._copy_split_contract(root)
            self._write_fixture(root, terminal_cohorts=True)
            assess_ahs_gate(root)
            harmonize(root)

            split_dir = assign_ahs_splits(root)
            report = audit_ahs_split(root, split_dir)
            assignments = self._read(split_dir / "split_assignment.csv")
            manifest = json.loads(
                (split_dir / "split_manifest.json").read_text(encoding="utf-8")
            )

            self.assertEqual(report["status"], "passed")
            splits_by_asset: dict[str, set[str]] = {}
            for row in assignments:
                splits_by_asset.setdefault(row["analytical_asset_id"], set()).add(
                    row["split_name"]
                )
            self.assertTrue(all(len(names) == 1 for names in splits_by_asset.values()))
            self.assertEqual(
                manifest["counts"]["assets_by_split"],
                {"test": 167, "training": 167, "validation": 167},
            )
            self.assertEqual(
                manifest["counts"]["rows_by_split"],
                {"test": 668, "training": 334, "validation": 501},
            )
            self.assertEqual(manifest["cap_sensitivity"]["excluded_rows"], 167)
            self.assertEqual(
                sum(
                    row["include_in_pre_2023_cap_sensitivity"] == "false"
                    for row in assignments
                ),
                167,
            )
            self.assertNotIn("CONTROL", assignments[0])
            self.assertNotIn("target_amount_local_nominal", assignments[0])

            with self.assertRaises(FileExistsError):
                assign_ahs_splits(root)

    def test_split_rejects_semantic_decision_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._copy_split_contract(root)
            self._write_fixture(root, terminal_cohorts=True)
            assess_ahs_gate(root)
            harmonize(root)
            decision = root / "Documentation" / "AHSSemanticLicenseDecision.md"
            decision.write_text(
                decision.read_text(encoding="utf-8") + "\nchanged\n", encoding="utf-8"
            )

            with self.assertRaisesRegex(ValueError, "decision checksum changed"):
                assign_ahs_splits(root)

    def test_preprocessing_fits_training_only_and_preserves_targets_and_caps(self) -> None:
        learned_artifacts = []
        for profile in (1, 2):
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self._copy_split_contract(root)
                self._write_fixture(
                    root,
                    terminal_cohorts=True,
                    preprocessing_profile=profile,
                )
                assess_ahs_gate(root)
                harmonize(root)
                assign_ahs_splits(root)

                output_dir = build_ahs_preprocessing(root)
                report = audit_ahs_preprocessing(root, output_dir)
                artifact = json.loads(
                    (output_dir / "preprocessor.json").read_text(encoding="utf-8")
                )
                matrix = self._read(output_dir / "feature_matrix.csv")
                targets = self._read(output_dir / "target_metadata.csv")
                self.assertNotIn("target_amount_local_nominal", matrix[0])
                parameters = {
                    item["feature_name"]: item
                    for item in artifact["feature_parameters"]
                }

                self.assertEqual(report["status"], "passed")
                self.assertEqual(artifact["fit_split"], "training")
                self.assertEqual(artifact["fit_row_count"], 334)
                self.assertFalse(artifact["model_fitted"])
                self.assertFalse(
                    artifact["feature_policy"]["validation_or_test_statistics_used"]
                )
                self.assertNotIn(
                    str(90 + profile),
                    parameters["heating_type_code"]["encoder"]["training_categories"],
                )
                unknown_column = parameters["heating_type_code"]["encoder"][
                    "reserved_unknown_output_column"
                ]
                self.assertTrue(any(row[unknown_column] == "1" for row in matrix))
                self.assertTrue(
                    any(row["household_income_usd__is_missing"] == "1" for row in matrix)
                )
                self.assertFalse(parameters["roof_leak_code"]["value_feature_included"])
                self.assertIn("roof_leak_code__is_missing", matrix[0])

                self.assertEqual(len(matrix), 1503)
                self.assertEqual(len(targets), 1503)
                self.assertEqual(
                    artifact["high_cost_policy"]["threshold_version"],
                    HIGH_COST_THRESHOLD_VERSION,
                )
                self.assertLess(
                    Decimal(
                        artifact["high_cost_policy"][
                            "threshold_amount_local_nominal"
                        ]
                    ),
                    Decimal("8000"),
                )
                retained_2023 = [
                    row
                    for row in targets
                    if row["target_amount_local_nominal"] == "90000"
                ]
                self.assertTrue(retained_2023)
                self.assertTrue(
                    all(row["source_response_maximum_usd"] == "100000" for row in retained_2023)
                )
                self.assertTrue(
                    all(row["response_cap_regime"] == "wave_2023_usd_100000" for row in retained_2023)
                )
                self.assertTrue(
                    all(
                        row["include_in_pre_2023_cap_sensitivity"] == "false"
                        for row in retained_2023
                    )
                )
                self.assertTrue(all(row["target_was_imputed"] == "false" for row in targets))
                self.assertTrue(all(row["target_was_clipped"] == "false" for row in targets))

                learned_artifacts.append(
                    {
                        "feature_parameters": artifact["feature_parameters"],
                        "feature_matrix_columns": artifact["feature_matrix_columns"],
                        "fit_snapshot_ids_sha256": artifact["fit_snapshot_ids_sha256"],
                        "high_cost_policy": artifact["high_cost_policy"],
                    }
                )
                with self.assertRaises(FileExistsError):
                    build_ahs_preprocessing(root)

        self.assertEqual(learned_artifacts[0], learned_artifacts[1])

    @staticmethod
    def _read(path: Path) -> list[dict[str, str]]:
        with path.open("r", encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))


if __name__ == "__main__":
    unittest.main()
