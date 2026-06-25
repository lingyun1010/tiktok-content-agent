"""Tests for the offline analyst evaluation harness."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import patch

from src.backend import evaluate_analyst


FIXTURES_DIR = Path("tests/fixtures")
CASES_PATH = FIXTURES_DIR / "analyst_eval_cases.json"
DASHBOARD_PATH = FIXTURES_DIR / "analyst_dashboard_data.json"


class AnalystEvaluationHarnessTest(unittest.TestCase):
    def setUp(self) -> None:
        self.dashboard = evaluate_analyst.load_json_object(DASHBOARD_PATH)
        self.cases = evaluate_analyst.load_eval_cases(CASES_PATH)

    def test_eval_cases_file_is_valid_json(self) -> None:
        payload = json.loads(CASES_PATH.read_text(encoding="utf-8"))

        self.assertIsInstance(payload, list)
        self.assertGreaterEqual(len(payload), 8)
        for case in payload:
            self.assertIn("id", case)
            self.assertIn("question", case)
            self.assertEqual(case["expected_provider"], "manual")
            self.assertFalse(case["expected_llm_called"])

    def test_evaluation_runner_passes_on_fixture_data(self) -> None:
        results = evaluate_analyst.evaluate_cases(self.cases, self.dashboard)

        self.assertTrue(all(result.passed for result in results))
        report = evaluate_analyst.format_report(results)
        self.assertIn(f"Cases: {len(self.cases)}/{len(self.cases)} passed", report)

    def test_failure_is_detected_when_expected_tool_is_missing(self) -> None:
        case = dict(self.cases[0])
        case["expected_tools"] = ["missing_tool"]

        result = evaluate_analyst.evaluate_case(case, self.dashboard)

        self.assertFalse(result.passed)
        self.assertIn("missing expected tool: missing_tool", result.failures)

    def test_no_real_llm_provider_is_called(self) -> None:
        with patch(
            "src.backend.analyst.OpenAIAnalystProvider.from_environment"
        ) as openai_provider, patch(
            "src.backend.analyst.ClaudeAnalystProvider.from_environment"
        ) as claude_provider:
            results = evaluate_analyst.evaluate_cases(self.cases, self.dashboard)

        self.assertTrue(all(result.passed for result in results))
        openai_provider.assert_not_called()
        claude_provider.assert_not_called()

    def test_response_schema_validation_detects_missing_field(self) -> None:
        case = self.cases[0]
        response = {
            "summary": "Synthetic answer.",
            "evidence": [],
            "recommendation": "Do the next test.",
            "suggested_next_action": "Run a controlled test.",
            "limitations": ["Grounded only in dashboard data."],
            "provider": "manual",
            "llm_called": False,
            "trace": {
                "interpreted_intent": "best_performing_posts",
                "tools_used": ["get_top_posts"],
                "observations": ["eval-004 was the strongest post."],
            },
        }
        del response["recommendation"]

        failures = evaluate_analyst.validate_response(case, response)

        self.assertIn("missing required field: recommendation", failures)


if __name__ == "__main__":
    unittest.main()
