"""Offline tests for the Phase 1 content analytics pipeline."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

from src.backend.metrics import add_metrics, calculate_metrics, summarise_metrics
from src.backend.normalise import normalise_post, normalise_posts
from src.backend.pipeline import run_pipeline
from src.backend.schema import CANONICAL_CSV_FIELDS


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
    def test_sample_pipeline_generates_llm_ready_markdown_and_json(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_dir = Path(temporary_directory)
            metrics_path, plan_path = run_pipeline(
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
            self.assertEqual(plan["provider"], "manual")
            self.assertFalse(plan["llm_called"])

    def test_content_plan_stub_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            base = Path(temporary_directory)
            _, first_path = run_pipeline(
                Path("examples/sample_recent_posts.csv"),
                10,
                "manual",
                base / "first",
            )
            _, second_path = run_pipeline(
                Path("examples/sample_recent_posts.csv"),
                10,
                "manual",
                base / "second",
            )

            self.assertEqual(first_path.read_bytes(), second_path.read_bytes())


if __name__ == "__main__":
    unittest.main()
