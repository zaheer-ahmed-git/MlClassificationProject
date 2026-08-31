"""Thin entry point for the public-corpus command interface."""

from pathlib import Path
import sys

# Keep the repository entry point usable before an editable install. Installed
# environments resolve the same package from their normal import path.
source_root = Path(__file__).resolve().parents[1] / "src"
if str(source_root) not in sys.path:
    sys.path.insert(0, str(source_root))

from caip_maintenance.data.__main__ import main


if __name__ == "__main__":
    raise SystemExit(main())
