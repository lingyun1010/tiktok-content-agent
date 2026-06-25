"""Tests for deterministic internal analyst tools."""

from __future__ import annotations

import unittest

from src.backend.analyst_tools import (
    compare_posts_by_metric,
    get_dashboard_summary,
    get_pause_candidates,
    get_repeat_candidates,
    get_retention_issues,
    get_top_posts,
    get_underperforming_posts,
)


def tool_payload() -> dict:
    return {
        "dataset_overview": {
            "post_count": 4,
            "total_views": 13100,
            "average_views": 3275,
            "average_engagement_rate": 0.08,
            "average_watch_ratio": 0.55,
            "top_post": {
                "post_id": "post_003",
                "format": "talking_head",
                "topic": "education",
                "hook": "Stop making this mistake",
                "views": 8200,
                "engagement_rate": 0.14,
                "average_watch_ratio": 0.72,
                "signals": ["repeat_candidate"],
                "post_url": "https://example.invalid/private",
            },
        },
        "signals": {
            "repeat_post_ids": ["post_003"],
            "pause_post_ids": ["post_002"],
            "weak_retention_post_ids": ["post_002", "post_004"],
        },
        "posts": [
            {
                "post_id": "post_001",
                "format": "demo",
                "topic": "routine",
                "hook": "Three steps",
                "views": 4200,
                "engagement_rate": 0.08,
                "average_watch_ratio": 0.61,
                "region_match_score": 0.8,
                "signals": [],
            },
            {
                "post_id": "post_002",
                "format": "bts",
                "topic": "manufacturing",
                "hook": "Behind the batch",
                "views": 90,
                "engagement_rate": 0.01,
                "average_watch_ratio": 0.31,
                "region_match_score": None,
                "signals": ["pause_candidate", "weak_retention"],
            },
            {
                "post_id": "post_003",
                "format": "talking_head",
                "topic": "education",
                "hook": "Stop making this mistake",
                "views": 8200,
                "engagement_rate": 0.14,
                "average_watch_ratio": 0.72,
                "region_match_score": 0.9,
                "signals": ["repeat_candidate"],
            },
            {
                "post_id": "post_004",
                "format": "story",
                "topic": "founder",
                "hook": None,
                "views": 610,
                "engagement_rate": 0.04,
                "signals": ["weak_retention"],
            },
        ],
    }


class AnalystToolsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = tool_payload()

    def test_dashboard_summary_returns_safe_fields(self) -> None:
        summary = get_dashboard_summary(self.payload)

        self.assertEqual(summary["post_count"], 4)
        self.assertEqual(summary["top_post"]["post_id"], "post_003")
        self.assertNotIn("post_url", summary["top_post"])
        self.assertEqual(summary["repeat_post_ids"], ["post_003"])

    def test_get_top_posts_sorts_by_strength(self) -> None:
        posts = get_top_posts(self.payload, limit=2)

        self.assertEqual([post["post_id"] for post in posts], ["post_003", "post_001"])

    def test_get_underperforming_posts_prioritises_low_and_weak_posts(self) -> None:
        posts = get_underperforming_posts(self.payload, limit=2)

        self.assertEqual(posts[0]["post_id"], "post_002")
        self.assertIn(posts[1]["post_id"], {"post_004", "post_001"})

    def test_get_repeat_candidates_returns_repeat_posts(self) -> None:
        posts = get_repeat_candidates(self.payload)

        self.assertEqual([post["post_id"] for post in posts], ["post_003"])

    def test_get_pause_candidates_returns_pause_posts(self) -> None:
        posts = get_pause_candidates(self.payload)

        self.assertEqual([post["post_id"] for post in posts], ["post_002"])

    def test_get_retention_issues_returns_weak_retention_items(self) -> None:
        posts = get_retention_issues(self.payload)

        self.assertEqual([post["post_id"] for post in posts], ["post_002", "post_004"])

    def test_compare_posts_by_metric_supports_dashboard_metrics(self) -> None:
        by_views = compare_posts_by_metric(self.payload, "views", limit=1)
        by_engagement = compare_posts_by_metric(self.payload, "engagement_rate", limit=1)
        by_watch = compare_posts_by_metric(
            self.payload, "average_watch_ratio", limit=1
        )

        self.assertEqual(by_views[0]["post_id"], "post_003")
        self.assertEqual(by_engagement[0]["post_id"], "post_003")
        self.assertEqual(by_watch[0]["post_id"], "post_003")

    def test_compare_posts_by_metric_rejects_unknown_metric(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unsupported metric"):
            compare_posts_by_metric(self.payload, "likes")

    def test_tools_handle_missing_optional_fields(self) -> None:
        sparse_payload = {
            "dataset_overview": {"post_count": 1, "top_post": {"post_id": "sparse"}},
            "posts": [{"post_id": "sparse", "views": 1}],
        }

        self.assertEqual(get_dashboard_summary(sparse_payload)["pause_post_ids"], [])
        self.assertEqual(get_top_posts(sparse_payload)[0]["signals"], [])
        self.assertEqual(get_retention_issues(sparse_payload), [])


if __name__ == "__main__":
    unittest.main()
