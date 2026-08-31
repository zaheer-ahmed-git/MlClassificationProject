"""Contract tests for the first public-corpus harmonization slice."""

from __future__ import annotations

import csv
from pathlib import Path
import sys
import tempfile
import tomllib
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from caip_maintenance.data.audit import audit_release  # noqa: E402
from caip_maintenance.data.common import sha256_file  # noqa: E402
from caip_maintenance.data.rhfs import (  # noqa: E402
    DATASET_RELEASE,
    DOCUMENT_FILES,
    FEATURE_MAP,
    harmonize,
)


class RhfsPipelineTests(unittest.TestCase):
    def test_declarative_mapping_matches_implemented_feature_contract(self) -> None:
        with (PROJECT_ROOT / "configs" / "mappings" / "rhfs_2024.toml").open("rb") as handle:
            mapping = tomllib.load(handle)
        declared = {
            (field["target"], field["source"])
            for field in mapping["fields"]
            if field["role"] in {"feature", "descriptive_weight"}
        }

        self.assertEqual(declared, {(target, source) for target, source, _ in FEATURE_MAP})

    def _write_fixture(self, root: Path, valid_rows: int = 501) -> None:
        raw_dir = root / "data" / "raw" / "public" / "rhfs_2024" / "v1.0"
        raw_dir.mkdir(parents=True)
        fields = ["CONTROLPUF", "OPREP", "PROPANS", "JPREP", "OPEX_R"]
        fields.extend(source for _, source, _ in FEATURE_MAP if source not in fields)
        rows = [self._row(index) for index in range(valid_rows)]
        rows.extend(
            [
                self._row(valid_rows, OPREP="-9"),
                self._row(valid_rows + 1, OPREP="-8"),
                self._row(valid_rows + 2, OPREP="0", PROPANS="-9"),
            ]
        )
        with (raw_dir / DOCUMENT_FILES[0]).open(
            "w", encoding="utf-8", newline=""
        ) as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        for name in DOCUMENT_FILES[1:]:
            (raw_dir / name).write_bytes(b"test-only documentation fixture\n")

    @staticmethod
    def _row(index: int, **overrides: str) -> dict[str, str]:
        row = {source: "1" for _, source, _ in FEATURE_MAP}
        row.update(
            {
                "CONTROLPUF": f"test-{index:04d}",
                "OPREP": "0" if index == 0 else "100",
                "PROPANS": "1",
                "JPREP": "1" if index == 1 else "-9",
                "OPEX_R": "200",
            }
        )
        row.update(overrides)
        return row

    @staticmethod
    def _read(path: Path) -> list[dict[str, str]]:
        with path.open("r", encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))

    def test_harmonization_is_lineaged_auditable_and_privacy_safe(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_fixture(root)

            release = harmonize(root)
            report = audit_release(release)
            labels = self._read(release / "property_period_label.csv")
            bridges = self._read(release / "source_asset_bridge.csv")

            self.assertEqual(report["status"], "passed")
            self.assertEqual(len(labels), 501)
            self.assertEqual(sum(row["zero_valid"] == "true" for row in labels), 1)
            self.assertTrue(all(row["is_exact_wapda_target"] == "false" for row in labels))
            self.assertNotIn("CONTROLPUF", bridges[0])
            self.assertTrue(bridges[0]["analytical_asset_id"].startswith("asset_"))

            with self.assertRaises(FileExistsError):
                harmonize(root)

    def test_deterministic_tables_and_checksum_drift_detection(self) -> None:
        table_names = [
            "source_asset_bridge.csv",
            "annual_cost_observation.csv",
            "property_period_snapshot.csv",
            "property_period_label.csv",
            "record_lineage.csv",
            "source_document.csv",
        ]
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            roots = [Path(first), Path(second)]
            for root in roots:
                self._write_fixture(root)
                harmonize(root)
            releases = [
                root / "data" / "processed" / "releases" / DATASET_RELEASE
                for root in roots
            ]

            for name in table_names:
                self.assertEqual(
                    sha256_file(releases[0] / name),
                    sha256_file(releases[1] / name),
                )

            label_path = releases[0] / "property_period_label.csv"
            label_path.write_text(label_path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
            report = audit_release(releases[0])
            self.assertIn("processed_file_checksums", report["failed_checks"])

            (releases[1] / "qa_build_summary.json").unlink()
            missing_report = audit_release(releases[1])
            checksum_check = next(
                check
                for check in missing_report["checks"]
                if check["check_id"] == "processed_file_checksums"
            )
            self.assertIsNone(
                checksum_check["evidence"]["qa_build_summary.json"]["actual"]
            )


if __name__ == "__main__":
    unittest.main()
