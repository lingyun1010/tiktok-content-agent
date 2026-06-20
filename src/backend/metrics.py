"""Deterministic metric calculations and rule-based performance signals."""

from __future__ import annotations

from collections import Counter, defaultdict
from statistics import mean
from typing import Any, Iterable

WEAK_RETENTION_THRESHOLD = 0.50
WRONG_REGION_THRESHOLD = 0.50


def _rate(numerator: float, views: int) -> float:
    return round(numerator / views, 4) if views > 0 else 0.0


def _mean_available(values: Iterable[float | None]) -> float | None:
    available = [value for value in values if value is not None]
    return round(mean(available), 4) if available else None


def _region_match_score(post: dict[str, Any]) -> float | None:
    top_region = post["top_region"]
    target_region = post["target_region"]
    top_share = post["top_region_view_percentage"]
    if top_region is None or target_region is None or top_share is None:
        return None
    if top_region.casefold() == target_region.casefold():
        return round(top_share, 4)
    return round(1 - top_share, 4)


def add_metrics(post: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of a post with calculated rate and watch metrics."""
    views = post["views"]
    saves = post["saves"]
    engagement_total = (
        post["likes"] + post["comments"] + post["shares"] + (saves or 0)
    )
    duration = post["duration_seconds"]
    average_watch_time = post["average_watch_time_seconds"]
    watch_ratio = None
    if duration > 0 and average_watch_time is not None:
        watch_ratio = round(average_watch_time / duration, 4)

    return {
        **post,
        "like_rate": _rate(post["likes"], views),
        "comment_rate": _rate(post["comments"], views),
        "share_rate": _rate(post["shares"], views),
        "save_rate": _rate(saves, views) if saves is not None else None,
        "engagement_rate": _rate(engagement_total, views),
        "average_watch_ratio": watch_ratio,
        "region_match_score": _region_match_score(post),
    }


def _dataset_benchmarks(posts: list[dict[str, Any]]) -> dict[str, float | None]:
    return {
        "average_views": round(mean(post["views"] for post in posts), 2),
        "average_like_rate": _mean_available(post["like_rate"] for post in posts),
        "average_save_rate": _mean_available(post["save_rate"] for post in posts),
        "average_engagement_rate": _mean_available(
            post["engagement_rate"] for post in posts
        ),
        "average_watch_ratio": _mean_available(
            post["average_watch_ratio"] for post in posts
        ),
    }


def _signals(
    post: dict[str, Any], benchmarks: dict[str, float | None]
) -> list[str]:
    average_views = float(benchmarks["average_views"] or 0)
    average_like_rate = float(benchmarks["average_like_rate"] or 0)
    average_save_rate = benchmarks["average_save_rate"]
    average_engagement = float(benchmarks["average_engagement_rate"] or 0)
    average_watch_ratio = benchmarks["average_watch_ratio"]

    high_view = post["views"] >= average_views
    high_engagement = post["engagement_rate"] >= average_engagement
    low_engagement = post["engagement_rate"] < average_engagement
    weak_retention = (
        post["average_watch_ratio"] is not None
        and post["average_watch_ratio"] < WEAK_RETENTION_THRESHOLD
    )
    wrong_region = (
        post["region_match_score"] is not None
        and post["region_match_score"] < WRONG_REGION_THRESHOLD
    )

    signals: list[str] = []
    if high_view and low_engagement:
        signals.append("high_view_low_engagement")
    if (
        post["views"] < average_views
        and post["save_rate"] is not None
        and average_save_rate is not None
        and post["save_rate"] >= average_save_rate
    ):
        signals.append("low_view_high_save")
    if post["like_rate"] >= average_like_rate and weak_retention:
        signals.append("good_hook_weak_retention")
    if wrong_region:
        signals.append("wrong_region_distribution")

    retention_supports_repeat = (
        post["average_watch_ratio"] is None
        or average_watch_ratio is None
        or post["average_watch_ratio"] >= average_watch_ratio
    )
    if high_engagement and retention_supports_repeat and not wrong_region:
        signals.append("repeat_candidate")
    if low_engagement and (weak_retention or wrong_region):
        signals.append("pause_candidate")
    return signals


def calculate_metrics(posts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Calculate metrics and dataset-relative signals for all posts."""
    enriched_posts = [add_metrics(post) for post in posts]
    if not enriched_posts:
        return []
    benchmarks = _dataset_benchmarks(enriched_posts)
    return [
        {**post, "signals": _signals(post, benchmarks)}
        for post in enriched_posts
    ]


def _group_performance(
    posts: list[dict[str, Any]], field: str
) -> list[dict[str, Any]]:
    groups: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for post in posts:
        groups[post[field]].append(post)

    results = []
    for name, grouped_posts in groups.items():
        results.append(
            {
                "name": name,
                "post_count": len(grouped_posts),
                "total_views": sum(post["views"] for post in grouped_posts),
                "average_views": round(
                    mean(post["views"] for post in grouped_posts), 2
                ),
                "average_engagement_rate": _mean_available(
                    post["engagement_rate"] for post in grouped_posts
                ),
                "average_watch_ratio": _mean_available(
                    post["average_watch_ratio"] for post in grouped_posts
                ),
                "repeat_candidates": sum(
                    "repeat_candidate" in post["signals"] for post in grouped_posts
                ),
            }
        )
    return sorted(
        results,
        key=lambda group: (
            -(group["average_engagement_rate"] or 0),
            -group["average_views"],
            group["name"],
        ),
    )


def _post_snapshot(post: dict[str, Any]) -> dict[str, Any]:
    return {
        "post_id": post["post_id"],
        "caption": post["caption"],
        "format": post["format"],
        "topic": post["topic"],
        "hook": post["hook"],
        "views": post["views"],
        "engagement_rate": post["engagement_rate"],
        "save_rate": post["save_rate"],
        "average_watch_ratio": post["average_watch_ratio"],
        "region_match_score": post["region_match_score"],
        "signals": post["signals"],
    }


def summarise_metrics(posts: list[dict[str, Any]]) -> dict[str, Any]:
    """Build aggregate, ranking, grouping, region, and signal summaries."""
    if not posts:
        return {
            "post_count": 0,
            "total_views": 0,
            "average_views": 0.0,
            "average_engagement_rate": 0.0,
            "average_watch_ratio": None,
            "average_region_match_score": None,
            "top_post": None,
            "top_posts": [],
            "weak_posts": [],
            "format_performance": [],
            "topic_performance": [],
            "signal_counts": {},
            "signal_posts": {},
            "region_coverage_count": 0,
        }

    ranked = sorted(
        posts,
        key=lambda post: (
            -post["engagement_rate"],
            -(post["average_watch_ratio"] or 0),
            -post["views"],
            post["post_id"],
        ),
    )
    weak_ranked = sorted(
        posts,
        key=lambda post: (
            post["engagement_rate"],
            post["average_watch_ratio"]
            if post["average_watch_ratio"] is not None
            else 1,
            post["views"],
            post["post_id"],
        ),
    )
    signal_counts = Counter(
        signal for post in posts for signal in post["signals"]
    )
    signal_posts = {
        signal: [
            post["post_id"] for post in posts if signal in post["signals"]
        ]
        for signal in sorted(signal_counts)
    }
    top_post = _post_snapshot(ranked[0])

    return {
        "post_count": len(posts),
        "total_views": sum(post["views"] for post in posts),
        "average_views": round(mean(post["views"] for post in posts), 2),
        "average_engagement_rate": _mean_available(
            post["engagement_rate"] for post in posts
        ),
        "average_watch_ratio": _mean_available(
            post["average_watch_ratio"] for post in posts
        ),
        "average_region_match_score": _mean_available(
            post["region_match_score"] for post in posts
        ),
        "top_post": top_post,
        "top_posts": [_post_snapshot(post) for post in ranked[:3]],
        "weak_posts": [_post_snapshot(post) for post in weak_ranked[:3]],
        "format_performance": _group_performance(posts, "format"),
        "topic_performance": _group_performance(posts, "topic"),
        "signal_counts": dict(sorted(signal_counts.items())),
        "signal_posts": signal_posts,
        "region_coverage_count": sum(
            post["region_match_score"] is not None for post in posts
        ),
    }
