"""Tests for the Phase 6B analyst providers."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

from src.backend.analyst import (
    AnalystError,
    ClaudeAnalystProvider,
    OpenAIAnalystProvider,
    answer_question,
    build_safe_context,
    load_dashboard_data,
    validate_answer_payload,
)
from src.backend.pipeline import run_pipeline


def sample_dashboard_payload() -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as temporary_directory:
        *_, dashboard_path = run_pipeline(
            input_path=Path("examples/sample_recent_posts.csv"),
            limit=10,
            provider_name="manual",
            output_dir=Path(temporary_directory),
        )
        return json.loads(dashboard_path.read_text(encoding="utf-8"))


def valid_analyst_payload() -> dict[str, Any]:
    return {
        "summary": "The strongest post is supported by engagement evidence.",
        "evidence": [
            {
                "post_id": "demo-004",
                "metric": "engagement_rate",
                "value": "12.62%",
            }
        ],
        "recommendation": "Repeat the strongest supported format.",
        "suggested_next_action": "Run one controlled follow-up test.",
        "limitations": ["Grounded only in the supplied dashboard data."],
    }


class AnalystProviderTest(unittest.TestCase):
    def setUp(self) -> None:
        self.dashboard = sample_dashboard_payload()

    def test_manual_provider_returns_structured_response(self) -> None:
        answer = answer_question(
            "Which posts performed best recently?",
            self.dashboard,
            provider="manual",
        )

        self.assertEqual(answer["provider"], "manual")
        self.assertFalse(answer["llm_called"])
        for field in (
            "summary",
            "evidence",
            "recommendation",
            "suggested_next_action",
            "limitations",
            "provider",
            "llm_called",
        ):
            self.assertIn(field, answer)
        self.assertTrue(answer["evidence"])
        self.assertEqual(answer["trace"]["interpreted_intent"], "best_performing_posts")
        self.assertIn("get_top_posts", answer["trace"]["tools_used"])

    def test_manual_best_question_returns_top_post_trace(self) -> None:
        answer = answer_question(
            "Which posts performed best recently?",
            self.dashboard,
            provider="manual",
        )

        self.assertEqual(answer["provider"], "manual")
        self.assertFalse(answer["llm_called"])
        self.assertEqual(answer["trace"]["interpreted_intent"], "best_performing_posts")
        self.assertEqual(answer["trace"]["tools_used"], ["get_top_posts"])

    def test_manual_hook_reuse_question_returns_repeat_trace(self) -> None:
        answer = answer_question(
            "Which hook should I reuse?",
            self.dashboard,
            provider="manual",
        )

        self.assertEqual(answer["provider"], "manual")
        self.assertFalse(answer["llm_called"])
        self.assertEqual(answer["trace"]["interpreted_intent"], "hook_reuse")
        self.assertIn("get_repeat_candidates", answer["trace"]["tools_used"])

    def test_manual_pause_question_returns_pause_trace(self) -> None:
        answer = answer_question(
            "What should I avoid or pause?",
            self.dashboard,
            provider="manual",
        )

        self.assertEqual(answer["provider"], "manual")
        self.assertFalse(answer["llm_called"])
        self.assertEqual(answer["trace"]["interpreted_intent"], "pause_or_avoid")
        self.assertTrue(
            {
                "get_pause_candidates",
                "get_underperforming_posts",
            }.intersection(answer["trace"]["tools_used"])
        )

    def test_manual_retention_question_returns_retention_trace(self) -> None:
        answer = answer_question(
            "How should I improve retention?",
            self.dashboard,
            provider="manual",
        )

        self.assertEqual(answer["provider"], "manual")
        self.assertFalse(answer["llm_called"])
        self.assertEqual(answer["trace"]["interpreted_intent"], "retention_issues")
        self.assertEqual(answer["trace"]["tools_used"], ["get_retention_issues"])

    def test_manual_underperforming_question_includes_limitations(self) -> None:
        answer = answer_question(
            "Why are some posts stuck around 90 views?",
            self.dashboard,
            provider="manual",
        )

        self.assertEqual(answer["provider"], "manual")
        self.assertFalse(answer["llm_called"])
        self.assertEqual(
            answer["trace"]["interpreted_intent"], "underperforming_or_low_views"
        )
        self.assertIn("get_underperforming_posts", answer["trace"]["tools_used"])
        self.assertTrue(
            any("impressions" in limitation for limitation in answer["limitations"])
        )

    def test_manual_response_schema_keeps_existing_fields_with_optional_trace(self) -> None:
        answer = answer_question(
            "Give me the general summary.",
            self.dashboard,
            provider="manual",
        )

        self.assertTrue(
            {
                "summary",
                "evidence",
                "recommendation",
                "suggested_next_action",
                "limitations",
                "provider",
                "llm_called",
            }.issubset(answer)
        )
        self.assertIn("trace", answer)

    def test_missing_dashboard_data_is_rejected(self) -> None:
        with self.assertRaisesRegex(AnalystError, "missing required fields"):
            answer_question("What should I post?", {"posts": []}, provider="manual")

    def test_invalid_provider_is_rejected(self) -> None:
        with self.assertRaisesRegex(AnalystError, "Unknown analyst provider"):
            answer_question("What should I post?", self.dashboard, provider="deepseek")

    def test_structured_response_validation_rejects_missing_fields(self) -> None:
        payload = valid_analyst_payload()
        del payload["recommendation"]

        with self.assertRaisesRegex(AnalystError, "recommendation"):
            validate_answer_payload(payload)

    def test_structured_response_validation_allows_optional_trace(self) -> None:
        payload = valid_analyst_payload()
        payload["trace"] = {
            "interpreted_intent": "best_performing_posts",
            "tools_used": ["get_top_posts"],
            "observations": ["demo-004 had the highest engagement rate."],
            "limitations": ["Grounded only in dashboard data."],
        }

        answer = validate_answer_payload(payload)

        self.assertEqual(answer["trace"]["tools_used"], ["get_top_posts"])

    def test_safe_context_excludes_private_fields(self) -> None:
        context = build_safe_context(self.dashboard)
        encoded = json.dumps(context)

        self.assertNotIn("post_url", encoded)
        self.assertNotIn('"caption"', encoded)
        self.assertNotIn("notes", encoded)
        self.assertNotIn("api_key", encoded.lower())
        self.assertIn("demo-004", encoded)

    def test_load_dashboard_data_reports_missing_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            missing_path = Path(temporary_directory) / "missing.json"
            with self.assertRaisesRegex(AnalystError, "Run the backend pipeline"):
                load_dashboard_data(missing_path)

    def test_openai_provider_parses_mocked_structured_json(self) -> None:
        api_response = {
            "output": [
                {
                    "content": [
                        {
                            "type": "output_text",
                            "text": json.dumps(valid_analyst_payload()),
                        }
                    ]
                }
            ]
        }
        captured_request: dict[str, Any] = {}

        def fake_post_json(
            url: str,
            headers: dict[str, str],
            body: dict[str, Any],
            provider: str,
        ) -> dict[str, Any]:
            captured_request.update(
                {"url": url, "headers": headers, "body": body, "provider": provider}
            )
            return api_response

        provider = OpenAIAnalystProvider(
            "test-openai-key", "test-openai-model", post_json=fake_post_json
        )
        answer = provider.answer("Which hooks should I reuse?", self.dashboard)

        request_input = json.loads(captured_request["body"]["input"])
        encoded_context = json.dumps(request_input["dashboard_context"])
        self.assertEqual(answer["provider"], "openai")
        self.assertTrue(answer["llm_called"])
        self.assertNotIn("post_url", encoded_context)
        self.assertNotIn('"caption"', encoded_context)
        self.assertNotIn("test-openai-key", encoded_context)

    def test_claude_provider_rejects_invalid_json(self) -> None:
        def fake_post_json(*args: Any, **kwargs: Any) -> dict[str, Any]:
            return {"content": [{"type": "text", "text": "not-json"}]}

        provider = ClaudeAnalystProvider(
            "test-claude-key", "test-claude-model", post_json=fake_post_json
        )
        with self.assertRaisesRegex(AnalystError, "invalid JSON"):
            provider.answer("What should I post tomorrow?", self.dashboard)


if __name__ == "__main__":
    unittest.main()
