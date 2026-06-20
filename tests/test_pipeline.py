"""Offline tests for analytics and deterministic manual strategy generation."""

from __future__ import annotations

import json
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from typing import Any
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from src.backend.ingest.airtable import AirtableError, load_posts as load_airtable_posts
from src.backend.metrics import add_metrics, calculate_metrics, summarise_metrics
from src.backend.normalise import normalise_post, normalise_posts
from src.backend.pipeline import run_pipeline
from src.backend.schema import CANONICAL_CSV_FIELDS
from src.backend.strategy_agent import ManualStrategyProvider


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


class AirtableIngestionTest(unittest.TestCase):
    ENVIRONMENT = {
        "AIRTABLE_API_KEY": "test-secret-key",
        "AIRTABLE_BASE_ID": "appSynthetic",
        "AIRTABLE_TABLE_NAME": "TikTok Posts",
        "AIRTABLE_VIEW_NAME": "Recent Posts",
    }

    def test_requires_all_airtable_environment_variables_without_values(self) -> None:
        with self.assertRaises(AirtableError) as context:
            load_airtable_posts(10, environ={"AIRTABLE_API_KEY": "do-not-print"})

        message = str(context.exception)
        self.assertIn("AIRTABLE_BASE_ID", message)
        self.assertIn("AIRTABLE_TABLE_NAME", message)
        self.assertIn("AIRTABLE_VIEW_NAME", message)
        self.assertNotIn("do-not-print", message)

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
        self.assertEqual(first_query["view"], ["Recent Posts"])
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
        self.assertEqual(summary["region_coverage_count"], 2)


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


if __name__ == "__main__":
    unittest.main()
