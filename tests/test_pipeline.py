"""Basic offline tests for the sample content pipeline."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.backend.pipeline import run_pipeline


class PipelineTest(unittest.TestCase):
    def test_sample_pipeline_generates_markdown_and_json(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_dir = Path(temporary_directory)
            metrics_path, plan_path = run_pipeline(
                input_path=Path("examples/sample_recent_posts.csv"),
                limit=10,
                provider_name="manual",
                output_dir=output_dir,
            )

            self.assertIn("Posts analysed: 10", metrics_path.read_text())
            plan = json.loads(plan_path.read_text())
            self.assertEqual(plan["provider"], "manual")
            self.assertFalse(plan["llm_called"])


if __name__ == "__main__":
    unittest.main()

