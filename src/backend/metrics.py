"""Performance metric calculations for normalised TikTok posts."""

from __future__ import annotations

from statistics import mean
from typing import Any


def _rate(numerator: float, views: int) -> float:
    return round(numerator / views, 4) if views > 0 else 0.0


def add_metrics(post: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of a post with calculated rate and watch metrics."""
    views = post["views"]
    saves = post["saves"]
    engagement_total = (
        post["likes"] + post["comments"] + post["shares"] + (saves or 0)
    )

    enriched = {
        **post,
        "like_rate": _rate(post["likes"], views),
        "comment_rate": _rate(post["comments"], views),
        "share_rate": _rate(post["shares"], views),
        "save_rate": _rate(saves, views) if saves is not None else None,
        "engagement_rate": _rate(engagement_total, views),
        "average_watch_ratio": None,
    }

    duration = post["duration_seconds"]
    average_watch_time = post["average_watch_time_seconds"]
    if duration is not None and duration > 0 and average_watch_time is not None:
        enriched["average_watch_ratio"] = round(average_watch_time / duration, 4)

    return enriched


def calculate_metrics(posts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Calculate metrics for all normalised posts."""
    return [add_metrics(post) for post in posts]


def summarise_metrics(posts: list[dict[str, Any]]) -> dict[str, Any]:
    """Build aggregate metrics and identify the strongest engagement post."""
    if not posts:
        return {
            "post_count": 0,
            "total_views": 0,
            "average_engagement_rate": 0.0,
            "average_watch_ratio": None,
            "top_post": None,
        }

    watch_ratios = [
        post["average_watch_ratio"]
        for post in posts
        if post["average_watch_ratio"] is not None
    ]
    top_post = max(posts, key=lambda post: post["engagement_rate"])

    return {
        "post_count": len(posts),
        "total_views": sum(post["views"] for post in posts),
        "average_engagement_rate": round(
            mean(post["engagement_rate"] for post in posts), 4
        ),
        "average_watch_ratio": (
            round(mean(watch_ratios), 4) if watch_ratios else None
        ),
        "top_post": {
            "post_id": top_post["post_id"],
            "caption": top_post["caption"],
            "engagement_rate": top_post["engagement_rate"],
            "content_pillar": top_post["content_pillar"],
            "hook": top_post["hook"],
        },
    }

