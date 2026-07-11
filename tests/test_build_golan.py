"""Regression tests for the standalone Golan analysis builder."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "analysis" / "build_golan.py"


class BuildGolanCliTest(unittest.TestCase):
    """Verify that the analysis runs from a clean checkout."""

    def test_builds_expected_summary_with_repository_data(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "golan_data.json"
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--output", str(output)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(payload["n_jewish"], 33)
            self.assertEqual(payload["n_druze"], 5)


if __name__ == "__main__":
    unittest.main()
