"""Tests for the declarative public-source registry."""

from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from caip_maintenance.data.registry import load_registry  # noqa: E402


class SourceRegistryTests(unittest.TestCase):
    def test_repository_registry_has_expected_governance_bounds(self) -> None:
        registry = load_registry(PROJECT_ROOT / "configs" / "sources.toml")

        self.assertEqual(len(registry["sources"]), 10)
        self.assertEqual(
            [
                source["source_id"]
                for source in registry["sources"]
                if source["status"] == "approved_core"
            ],
            ["rhfs_2024"],
        )
        ahs = next(source for source in registry["sources"] if source["source_id"] == "ahs_2015_2023")
        self.assertEqual(ahs["status"], "approved_proxy")
        self.assertEqual(ahs["native_key"], "CONTROL")
        self.assertFalse(ahs["redistribution_allowed"])
        self.assertEqual(len(ahs["artifacts"]), 28)

    def test_registry_rejects_fewer_than_five_sources(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sources.toml"
            path.write_text('registry_version = "test"\n', encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "between 5 and 10"):
                load_registry(path)


if __name__ == "__main__":
    unittest.main()
