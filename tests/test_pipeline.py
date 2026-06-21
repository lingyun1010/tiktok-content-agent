"""Offline tests for analytics and deterministic manual strategy generation."""

from __future__ import annotations

import json
import importlib.util
import os
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from typing import Any
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from src.backend.ingest.airtable import (
    AirtableConfig,
    AirtableError,
    load_posts as load_airtable_posts,
)
from src.backend.llm_strategy import (
    ClaudeStrategyProvider,
    LLMStrategyError,
    OpenAIStrategyProvider,
    build_compact_strategy_input,
    configured_provider_name,
    validate_llm_plan,
)
from src.backend.metrics import add_metrics, calculate_metrics, summarise_metrics
from src.backend.normalise import normalise_post, normalise_posts
from src.backend.pipeline import run_pipeline
from src.backend.schema import CANONICAL_CSV_FIELDS
from src.backend.strategy_agent import ManualStrategyProvider, get_strategy_provider


def canonical_post(**overrides: Any) -> dict[str, Any]:
    post = {
        "post_id": "test-001",
        "platform": "tiktok",
        "post_url": None,
        "published_at": "2026-05-01T10:00:00Z",
        "format": "Talking head",
        "topic": "Education",
        "hook": "A clear opening",
        "caption": "Synthetic test post",
        "duration_seconds": 20.0,
        "views": 100,
        "likes": 10,
        "comments": 2,
        "shares": 3,
        "saves": 5,
        "average_watch_time_seconds": 10.0,
        "completion_rate": 0.4,
        "top_region": "Australia",
        "target_region": "Australia",
        "top_region_view_percentage": 0.7,
        "notes": None,
    }
    post.update(overrides)
    return post


def valid_llm_payload(post_id: str = "test-001") -> dict[str, Any]:
    return {
        "strategy": {
            "primary_goal": "Test a clearer educational routine concept.",
            "repeat": {
                "source_post_id": post_id,
                "format": "Talking head",
                "topic": "Education",
                "reason": "The supplied signals support a controlled follow-up.",
            },
            "pause": [],
            "retention_adjustment": {
                "required": False,
                "affected_post_ids": [],
                "guidance": "Keep the explanation concise.",
            },
        },
        "content_item": {
            "id": "llm-001",
            "working_title": "One clearer wash-day step",
            "format": "Talking head",
            "topic": "Education",
            "source_post_id": post_id,
            "creative_direction": "Demonstrate one practical adjustment.",
            "script": {
                "hook": "Your wash-day routine may need one simpler step.",
                "body": ["Show the step.", "Explain why it is worth testing."],
                "cta": "Save this for your next wash day.",
            },
            "caption": "One practical adjustment to test next.",
            "hashtags": ["#HairCareTips", "#WashDay"],
            "review_checks": [
                "Verify all product and performance claims.",
                "Approve the final copy before publishing.",
            ],
        },
        "limitations": [
            "The recommendation is based only on the supplied compact summary."
        ],
    }


class NormalisationTest(unittest.TestCase):
    def test_normalises_the_canonical_schema(self) -> None:
        raw_post = {
            "_row_number": 2,
            **{field: "" for field in CANONICAL_CSV_FIELDS},
            "post_id": "demo",
            "platform": "TikTok",
            "published_at": "2026-05-01T10:00:00Z",
            "format": "Product demo",
            "topic": "Routine",
            "hook": "Watch this",
            "caption": "Synthetic caption",
            "duration_seconds": "20",
            "views": "100",
            "likes": "10",
            "comments": "2",
            "shares": "3",
            "saves": "5",
            "average_watch_time_seconds": "10.5",
            "completion_rate": "0.4",
            "top_region": "Australia",
            "target_region": "Australia",
            "top_region_view_percentage": "0.7",
        }

        post = normalise_post(raw_post)

        self.assertEqual(post["platform"], "tiktok")
        self.assertEqual(post["views"], 100)
        self.assertEqual(post["duration_seconds"], 20.0)
        self.assertEqual(post["completion_rate"], 0.4)

    def test_rejects_duplicate_post_ids(self) -> None:
        raw = {
            "_row_number": 2,
            "post_id": "duplicate",
            "platform": "tiktok",
            "published_at": "2026-05-01T10:00:00Z",
            "format": "Product demo",
            "topic": "Routine",
            "hook": "Watch this",
            "caption": "Synthetic caption",
            "duration_seconds": "20",
            "views": "100",
            "likes": "10",
            "comments": "2",
            "shares": "3",
        }

        with self.assertRaisesRegex(ValueError, "duplicate 'post_id'"):
            normalise_posts([raw, {**raw, "_row_number": 3}])

    def test_keeps_missing_topic_and_hook_as_none(self) -> None:
        raw = {
            "_row_number": 2,
            "post_id": "metadata-light",
            "platform": "tiktok",
            "published_at": "2026-05-01T10:00:00Z",
            "format": "Product demo",
            "caption": "Synthetic caption",
            "duration_seconds": "20",
            "views": "100",
            "likes": "10",
            "comments": "2",
            "shares": "3",
        }

        post = normalise_post(raw)

        self.assertIsNone(post["topic"])
        self.assertIsNone(post["hook"])


class AirtableIngestionTest(unittest.TestCase):
    ENVIRONMENT = {
        "AIRTABLE_API_KEY": "test-secret-key",
        "AIRTABLE_BASE_ID": "appSynthetic",
        "AIRTABLE_TABLE_ID": "tblSynthetic",
        "AIRTABLE_VIEW_ID": "viwSynthetic",
    }

    def test_requires_all_airtable_environment_variables_without_values(self) -> None:
        with self.assertRaises(AirtableError) as context:
            load_airtable_posts(10, environ={"AIRTABLE_API_KEY": "do-not-print"})

        message = str(context.exception)
        self.assertIn("AIRTABLE_BASE_ID", message)
        self.assertIn("AIRTABLE_TABLE_ID", message)
        self.assertIn("AIRTABLE_VIEW_ID", message)
        self.assertNotIn("do-not-print", message)

    @unittest.skipUnless(
        importlib.util.find_spec("dotenv"),
        "python-dotenv is not installed",
    )
    def test_loads_airtable_configuration_from_local_dotenv(self) -> None:
        dotenv_content = "\n".join(
            f"{name}={value}" for name, value in self.ENVIRONMENT.items()
        )
        with tempfile.TemporaryDirectory() as temporary_directory:
            dotenv_path = Path(temporary_directory) / ".env"
            dotenv_path.write_text(dotenv_content, encoding="utf-8")
            with patch.dict(os.environ, {}, clear=True):
                with patch("pathlib.Path.cwd", return_value=Path(temporary_directory)):
                    config = AirtableConfig.from_environment()

        self.assertEqual(config.api_key, "test-secret-key")
        self.assertEqual(config.base_id, "appSynthetic")
        self.assertEqual(config.table_id, "tblSynthetic")
        self.assertEqual(config.view_id, "viwSynthetic")

    def test_maps_fields_and_paginates_until_limit(self) -> None:
        responses = [
            {
                "records": [
                    {"id": "recOne", "fields": canonical_post(post_id="one")},
                    {"id": "recTwo", "fields": canonical_post(post_id="two")},
                ],
                "offset": "next-page",
            },
            {
                "records": [
                    {"id": "recThree", "fields": canonical_post(post_id="three")}
                ]
            },
        ]
        requests = []

        class FakeResponse:
            def __init__(self, payload: dict[str, Any]) -> None:
                self.body = BytesIO(json.dumps(payload).encode("utf-8"))

            def __enter__(self) -> "FakeResponse":
                return self

            def __exit__(self, *args: object) -> None:
                return None

            def read(self) -> bytes:
                return self.body.read()

        def opener(request: Any, timeout: int) -> FakeResponse:
            requests.append((request, timeout))
            return FakeResponse(responses[len(requests) - 1])

        rows = load_airtable_posts(
            3,
            environ=self.ENVIRONMENT,
            opener=opener,
        )

        self.assertEqual([row["post_id"] for row in rows], ["one", "two", "three"])
        self.assertEqual(rows[0]["_row_number"], 1)
        self.assertEqual(rows[0]["views"], 100)
        self.assertEqual(rows[0]["post_url"], "")
        self.assertEqual(rows[0]["notes"], "")
        self.assertEqual(
            requests[0][0].get_header("Authorization"),
            "Bearer test-secret-key",
        )
        self.assertEqual(requests[0][1], 30)
        first_query = parse_qs(urlparse(requests[0][0].full_url).query)
        second_query = parse_qs(urlparse(requests[1][0].full_url).query)
        self.assertEqual(first_query["view"], ["viwSynthetic"])
        self.assertEqual(first_query["pageSize"], ["3"])
        self.assertEqual(second_query["offset"], ["next-page"])
        self.assertEqual(second_query["pageSize"], ["1"])


class MetricsTest(unittest.TestCase):
    def test_calculates_rates_and_zero_view_metrics(self) -> None:
        post = add_metrics(
            canonical_post(
                views=0,
                likes=10,
                comments=2,
                shares=3,
                saves=5,
            )
        )

        self.assertEqual(post["like_rate"], 0.0)
        self.assertEqual(post["comment_rate"], 0.0)
        self.assertEqual(post["share_rate"], 0.0)
        self.assertEqual(post["save_rate"], 0.0)
        self.assertEqual(post["engagement_rate"], 0.0)
        self.assertEqual(post["average_watch_ratio"], 0.5)

    def test_calculates_region_match_for_matching_and_mismatching_regions(self) -> None:
        matching = add_metrics(canonical_post())
        mismatching = add_metrics(
            canonical_post(top_region="United States", top_region_view_percentage=0.7)
        )

        self.assertEqual(matching["region_match_score"], 0.7)
        self.assertEqual(mismatching["region_match_score"], 0.3)

    def test_assigns_all_supported_rule_based_signals(self) -> None:
        posts = calculate_metrics(
            [
                canonical_post(
                    post_id="high-views",
                    views=1000,
                    likes=30,
                    comments=2,
                    shares=2,
                    saves=2,
                    average_watch_time_seconds=6,
                ),
                canonical_post(
                    post_id="save-worthy",
                    views=100,
                    likes=15,
                    comments=3,
                    shares=4,
                    saves=20,
                    average_watch_time_seconds=14,
                ),
                canonical_post(
                    post_id="wrong-region",
                    views=200,
                    likes=10,
                    comments=1,
                    shares=1,
                    saves=1,
                    average_watch_time_seconds=5,
                    top_region="United States",
                    top_region_view_percentage=0.7,
                ),
                canonical_post(
                    post_id="hook-retention",
                    views=150,
                    likes=45,
                    comments=2,
                    shares=2,
                    saves=1,
                    average_watch_time_seconds=4,
                ),
                canonical_post(
                    post_id="repeat",
                    views=300,
                    likes=60,
                    comments=8,
                    shares=8,
                    saves=15,
                    average_watch_time_seconds=16,
                ),
            ]
        )
        triggered = {signal for post in posts for signal in post["signals"]}

        self.assertEqual(
            triggered,
            {
                "high_view_low_engagement",
                "low_view_high_save",
                "good_hook_weak_retention",
                "wrong_region_distribution",
                "repeat_candidate",
                "pause_candidate",
            },
        )

    def test_summarises_format_topic_and_signal_performance(self) -> None:
        posts = calculate_metrics(
            [
                canonical_post(post_id="one", format="Demo", topic="Routine"),
                canonical_post(
                    post_id="two",
                    format="Story",
                    topic="Founder",
                    views=200,
                    likes=30,
                ),
            ]
        )

        summary = summarise_metrics(posts)

        self.assertEqual(summary["post_count"], 2)
        self.assertEqual(len(summary["format_performance"]), 2)
        self.assertEqual(len(summary["topic_performance"]), 2)
        self.assertEqual(summary["topic_coverage_count"], 2)
        self.assertEqual(summary["region_coverage_count"], 2)

    def test_skips_missing_topics_without_affecting_metrics(self) -> None:
        posts = calculate_metrics(
            [
                canonical_post(post_id="known", topic="Routine"),
                canonical_post(post_id="unknown", topic=None, hook=None),
            ]
        )

        summary = summarise_metrics(posts)

        self.assertEqual(summary["post_count"], 2)
        self.assertEqual(summary["topic_coverage_count"], 1)
        self.assertEqual(
            [group["name"] for group in summary["topic_performance"]],
            ["Routine"],
        )
        self.assertEqual(posts[1]["engagement_rate"], 0.2)


class PipelineTest(unittest.TestCase):
    def test_airtable_source_uses_canonical_pipeline_without_csv_input(self) -> None:
        source_post = canonical_post()
        raw_post = {
            "_row_number": 1,
            **{
                field: "" if value is None else value
                for field, value in source_post.items()
            },
        }
        with tempfile.TemporaryDirectory() as temporary_directory:
            with patch(
                "src.backend.pipeline.load_airtable_posts",
                return_value=[raw_post],
            ) as loader:
                paths = run_pipeline(
                    input_path=None,
                    limit=1,
                    provider_name="manual",
                    output_dir=Path(temporary_directory),
                    source="airtable",
                )

            loader.assert_called_once_with(1)
            self.assertIn(
                "- Source: `airtable`",
                paths[0].read_text(encoding="utf-8"),
            )

    def test_manual_strategy_uses_repeat_pause_and_retention_signals(self) -> None:
        posts = calculate_metrics(
            [
                canonical_post(
                    post_id="repeat",
                    format="Product demo",
                    topic="Routine",
                    hook="Try this instead",
                    views=500,
                    likes=100,
                    comments=10,
                    shares=10,
                    saves=20,
                    average_watch_time_seconds=16,
                ),
                canonical_post(
                    post_id="pause",
                    format="Montage",
                    topic="Lifestyle",
                    views=100,
                    likes=2,
                    comments=0,
                    shares=0,
                    saves=0,
                    average_watch_time_seconds=4,
                ),
            ]
        )
        summary = summarise_metrics(posts)

        plan = ManualStrategyProvider().generate_plan(posts, summary)

        self.assertEqual(plan["schema_version"], "1.0")
        self.assertEqual(plan["status"], "draft_for_human_review")
        self.assertTrue(plan["human_review_required"])
        self.assertEqual(
            plan["analysis_basis"]["repeat_candidate_post_ids"], ["repeat"]
        )
        self.assertEqual(
            plan["analysis_basis"]["pause_candidate_post_ids"], ["pause"]
        )
        self.assertEqual(plan["strategy"]["repeat"]["source_post_id"], "repeat")
        self.assertTrue(plan["strategy"]["retention_adjustment"]["required"])
        self.assertEqual(plan["content_item"]["source_post_id"], "repeat")
        self.assertIn("before publishing", plan["content_item"]["review_checks"][-1])

    def test_manual_strategy_uses_neutral_missing_metadata_fallbacks(self) -> None:
        posts = calculate_metrics([canonical_post(topic=None, hook=None)])
        summary = summarise_metrics(posts)

        plan = ManualStrategyProvider().generate_plan(posts, summary)

        self.assertIsNone(plan["content_item"]["topic"])
        self.assertEqual(
            plan["content_item"]["script"]["hook"],
            "Start with the clearest practical benefit",
        )
        self.assertNotIn("None", json.dumps(plan))

    def test_report_explains_limited_topic_coverage(self) -> None:
        source_post = canonical_post(topic=None, hook=None)
        raw_post = {
            "_row_number": 1,
            **{
                field: "" if value is None else value
                for field, value in source_post.items()
            },
        }
        with tempfile.TemporaryDirectory() as temporary_directory:
            with patch(
                "src.backend.pipeline.load_airtable_posts",
                return_value=[raw_post],
            ):
                metrics_path, *_ = run_pipeline(
                    input_path=None,
                    limit=1,
                    provider_name="manual",
                    output_dir=Path(temporary_directory),
                    source="airtable",
                )

            report = metrics_path.read_text(encoding="utf-8")
        self.assertIn("Topic-level analysis is unavailable", report)
        self.assertIn("0 of 1 posts include topic metadata", report)

    def test_sample_pipeline_generates_all_phase_2_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_dir = Path(temporary_directory)
            (
                metrics_path,
                plan_path,
                script_path,
                caption_path,
                hashtags_path,
            ) = run_pipeline(
                input_path=Path("examples/sample_recent_posts.csv"),
                limit=10,
                provider_name="manual",
                output_dir=output_dir,
            )

            markdown = metrics_path.read_text(encoding="utf-8")
            for heading in (
                "## Dataset overview",
                "## Top performing posts",
                "## Weak performing posts",
                "## Format performance",
                "## Topic performance",
                "## Audience region notes",
                "## Recommended signals for next content",
            ):
                self.assertIn(heading, markdown)
            self.assertIn("Posts analysed: 10", markdown)

            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            self.assertEqual(plan_path.name, "content_plan.json")
            self.assertEqual(plan["schema_version"], "1.0")
            self.assertEqual(plan["provider"], "manual")
            self.assertFalse(plan["llm_called"])
            self.assertTrue(plan["human_review_required"])
            self.assertTrue(plan["analysis_basis"]["repeat_candidate_post_ids"])
            self.assertIn("## Review checks", script_path.read_text(encoding="utf-8"))
            self.assertTrue(caption_path.read_text(encoding="utf-8").strip())
            hashtags = hashtags_path.read_text(encoding="utf-8").strip()
            self.assertTrue(hashtags.startswith("#"))
            self.assertIn(" ", hashtags)

    def test_phase_2_outputs_are_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            base = Path(temporary_directory)
            first_paths = run_pipeline(
                Path("examples/sample_recent_posts.csv"),
                10,
                "manual",
                base / "first",
            )
            second_paths = run_pipeline(
                Path("examples/sample_recent_posts.csv"),
                10,
                "manual",
                base / "second",
            )

            for first_path, second_path in zip(first_paths, second_paths):
                self.assertEqual(first_path.read_bytes(), second_path.read_bytes())


class LLMStrategyProviderTest(unittest.TestCase):
    def setUp(self) -> None:
        self.posts = calculate_metrics([canonical_post()])
        self.summary = summarise_metrics(self.posts)

    def test_requires_provider_keys_without_printing_other_values(self) -> None:
        with patch("src.backend.llm_strategy._load_local_dotenv"):
            with patch.dict(os.environ, {"UNRELATED_SECRET": "do-not-print"}, clear=True):
                with self.assertRaisesRegex(
                    LLMStrategyError, "OPENAI_API_KEY"
                ) as openai_context:
                    get_strategy_provider("openai")
                with self.assertRaisesRegex(
                    LLMStrategyError, "CLAUDE_API_KEY"
                ) as claude_context:
                    get_strategy_provider("claude")

        self.assertNotIn("do-not-print", str(openai_context.exception))
        self.assertNotIn("do-not-print", str(claude_context.exception))

    def test_model_provider_environment_selects_default(self) -> None:
        with patch("src.backend.llm_strategy._load_local_dotenv"):
            with patch.dict(os.environ, {"MODEL_PROVIDER": "Claude"}, clear=True):
                self.assertEqual(configured_provider_name(), "claude")

    def test_compact_input_excludes_raw_private_record_fields(self) -> None:
        payload = build_compact_strategy_input(self.posts, self.summary)
        encoded = json.dumps(payload)

        self.assertNotIn("Synthetic test post", encoded)
        self.assertNotIn("post_url", encoded)
        self.assertNotIn("published_at", encoded)
        self.assertNotIn("notes", encoded)
        self.assertNotIn('"likes"', encoded)
        self.assertEqual(payload["post_signals"][0]["post_id"], "test-001")

    def test_validation_adds_python_owned_evidence_metadata(self) -> None:
        payload = valid_llm_payload()

        plan = validate_llm_plan(
            payload,
            provider="openai",
            posts=self.posts,
            summary=self.summary,
        )

        self.assertEqual(plan["provider"], "openai")
        self.assertTrue(plan["llm_called"])
        self.assertEqual(plan["analysis_basis"]["post_count"], 1)
        self.assertEqual(plan["analysis_basis"]["top_post_id"], "test-001")

    def test_validation_rejects_missing_fields_and_unknown_source_ids(self) -> None:
        missing_caption = valid_llm_payload()
        del missing_caption["content_item"]["caption"]
        with self.assertRaisesRegex(LLMStrategyError, "content_item.caption"):
            validate_llm_plan(
                missing_caption,
                provider="openai",
                posts=self.posts,
                summary=self.summary,
            )

        unknown_source = valid_llm_payload(post_id="invented-post")
        with self.assertRaisesRegex(LLMStrategyError, "unknown post ID"):
            validate_llm_plan(
                unknown_source,
                provider="claude",
                posts=self.posts,
                summary=self.summary,
            )

    def test_openai_provider_parses_mocked_response_and_sends_compact_input(
        self,
    ) -> None:
        api_response = {
            "output": [
                {
                    "content": [
                        {
                            "type": "output_text",
                            "text": json.dumps(valid_llm_payload()),
                        }
                    ]
                }
            ]
        }
        captured_request: dict[str, Any] = {}

        class FakeResponse:
            def __enter__(self) -> "FakeResponse":
                return self

            def __exit__(self, *args: object) -> None:
                return None

            def read(self) -> bytes:
                return json.dumps(api_response).encode("utf-8")

        def fake_urlopen(request: Any, timeout: int) -> FakeResponse:
            captured_request["request"] = request
            captured_request["timeout"] = timeout
            return FakeResponse()

        provider = OpenAIStrategyProvider("test-openai-key", "test-openai-model")
        with patch("src.backend.llm_strategy.urlopen", side_effect=fake_urlopen):
            plan = provider.generate_plan(self.posts, self.summary)

        request_body = json.loads(captured_request["request"].data)
        compact_input = json.loads(request_body["input"])
        self.assertEqual(plan["provider"], "openai")
        self.assertEqual(request_body["model"], "test-openai-model")
        self.assertNotIn("caption", compact_input["post_signals"][0])
        self.assertEqual(
            captured_request["request"].get_header("Authorization"),
            "Bearer test-openai-key",
        )

    def test_claude_provider_rejects_invalid_json_gracefully(self) -> None:
        api_response = {"content": [{"type": "text", "text": "not-json"}]}

        class FakeResponse:
            def __enter__(self) -> "FakeResponse":
                return self

            def __exit__(self, *args: object) -> None:
                return None

            def read(self) -> bytes:
                return json.dumps(api_response).encode("utf-8")

        provider = ClaudeStrategyProvider("test-claude-key", "test-claude-model")
        with patch("src.backend.llm_strategy.urlopen", return_value=FakeResponse()):
            with self.assertRaisesRegex(LLMStrategyError, "invalid JSON"):
                provider.generate_plan(self.posts, self.summary)

    def test_pipeline_renders_all_outputs_from_validated_llm_plan(self) -> None:
        class FakeLLMProvider:
            def generate_plan(
                self,
                posts: list[dict[str, Any]],
                summary: dict[str, Any],
            ) -> dict[str, Any]:
                return validate_llm_plan(
                    valid_llm_payload(post_id=posts[0]["post_id"]),
                    provider="claude",
                    posts=posts,
                    summary=summary,
                )

        with tempfile.TemporaryDirectory() as temporary_directory:
            with patch(
                "src.backend.pipeline.get_strategy_provider",
                return_value=FakeLLMProvider(),
            ):
                paths = run_pipeline(
                    input_path=Path("examples/sample_recent_posts.csv"),
                    limit=1,
                    provider_name="claude",
                    output_dir=Path(temporary_directory),
                )

            plan = json.loads(paths[1].read_text(encoding="utf-8"))
            script = paths[2].read_text(encoding="utf-8")

        self.assertEqual(plan["provider"], "claude")
        self.assertTrue(plan["llm_called"])
        self.assertIn("opt-in claude strategy provider", script)


if __name__ == "__main__":
    unittest.main()
