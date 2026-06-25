"""Deterministic internal tools for dashboard-grounded analyst answers."""

from __future__ import annotations

from typing import Any, Mapping

SAFE_POST_FIELDS = (
    "post_id",
    "format",
    "topic",
    "hook",
    "views",
    "engagement_rate",
    "average_watch_ratio",
    "region_match_score",
    "signals",
)

SUPPORTED_COMPARE_METRICS = {
    "views",
    "engagement_rate",
    "average_watch_ratio",
}


def _safe_post(post: Mapping[str, Any]) -> dict[str, Any]:
    cleaned = {field: post.get(field) for field in SAFE_POST_FIELDS}
    signals = cleaned.get("signals")
    cleaned["signals"] = list(signals) if isinstance(signals, list) else []
    return cleaned


def _posts(data: Mapping[str, Any]) -> list[dict[str, Any]]:
    posts = data.get("posts", [])
    if not isinstance(posts, list):
        return []
    return [_safe_post(post) for post in posts if isinstance(post, Mapping)]


def _signal_ids(data: Mapping[str, Any], key: str) -> set[str]:
    signals = data.get("signals", {})
    if not isinstance(signals, Mapping):
        return set()
    values = signals.get(key, [])
    if not isinstance(values, list):
        return set()
    return {value for value in values if isinstance(value, str)}


def _metric_value(post: Mapping[str, Any], metric: str) -> float:
    value = post.get(metric)
    if value is None:
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def get_dashboard_summary(data: Mapping[str, Any]) -> dict[str, Any]:
    """Return a safe run-level summary from dashboard data."""
    overview = data.get("dataset_overview", {})
    signals = data.get("signals", {})
    if not isinstance(overview, Mapping):
        overview = {}
    if not isinstance(signals, Mapping):
        signals = {}
    return {
        "post_count": overview.get("post_count"),
        "total_views": overview.get("total_views"),
        "average_views": overview.get("average_views"),
        "average_engagement_rate": overview.get("average_engagement_rate"),
        "average_watch_ratio": overview.get("average_watch_ratio"),
        "top_post": _safe_post(overview.get("top_post", {}))
        if isinstance(overview.get("top_post", {}), Mapping)
        else {},
        "repeat_post_ids": list(signals.get("repeat_post_ids", []))
        if isinstance(signals.get("repeat_post_ids", []), list)
        else [],
        "pause_post_ids": list(signals.get("pause_post_ids", []))
        if isinstance(signals.get("pause_post_ids", []), list)
        else [],
        "weak_retention_post_ids": list(signals.get("weak_retention_post_ids", []))
        if isinstance(signals.get("weak_retention_post_ids", []), list)
        else [],
    }


def get_top_posts(data: Mapping[str, Any], limit: int = 3) -> list[dict[str, Any]]:
    """Return top posts by engagement, watch ratio, then views."""
    return sorted(
        _posts(data),
        key=lambda post: (
            _metric_value(post, "engagement_rate"),
            _metric_value(post, "average_watch_ratio"),
            _metric_value(post, "views"),
            str(post.get("post_id") or ""),
        ),
        reverse=True,
    )[: max(limit, 0)]


def get_underperforming_posts(
    data: Mapping[str, Any], limit: int = 3
) -> list[dict[str, Any]]:
    """Return low-performing posts, prioritising pause signals and low views."""
    pause_ids = _signal_ids(data, "pause_post_ids")
    weak_retention_ids = _signal_ids(data, "weak_retention_post_ids")
    return sorted(
        _posts(data),
        key=lambda post: (
            0 if post.get("post_id") in pause_ids else 1,
            0 if post.get("post_id") in weak_retention_ids else 1,
            _metric_value(post, "views"),
            _metric_value(post, "engagement_rate"),
            _metric_value(post, "average_watch_ratio"),
            str(post.get("post_id") or ""),
        ),
    )[: max(limit, 0)]


def get_repeat_candidates(data: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Return posts marked as repeat candidates in the dashboard signals."""
    repeat_ids = _signal_ids(data, "repeat_post_ids")
    return [
        post
        for post in get_top_posts(data, limit=len(_posts(data)))
        if post.get("post_id") in repeat_ids or "repeat_candidate" in post["signals"]
    ]


def get_pause_candidates(data: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Return posts marked as pause candidates in the dashboard signals."""
    pause_ids = _signal_ids(data, "pause_post_ids")
    return [
        post
        for post in get_underperforming_posts(data, limit=len(_posts(data)))
        if post.get("post_id") in pause_ids or "pause_candidate" in post["signals"]
    ]


def get_retention_issues(data: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Return posts with weak retention signals or low watch ratios."""
    weak_ids = _signal_ids(data, "weak_retention_post_ids")
    candidates = [
        post
        for post in _posts(data)
        if post.get("post_id") in weak_ids
        or "weak_retention" in post["signals"]
        or (
            post.get("average_watch_ratio") is not None
            and _metric_value(post, "average_watch_ratio") < 0.5
        )
    ]
    return sorted(
        candidates,
        key=lambda post: (
            1 if post.get("average_watch_ratio") is None else 0,
            _metric_value(post, "average_watch_ratio"),
            _metric_value(post, "engagement_rate"),
            str(post.get("post_id") or ""),
        ),
    )


def compare_posts_by_metric(
    data: Mapping[str, Any], metric: str, limit: int = 3
) -> list[dict[str, Any]]:
    """Return posts sorted by a supported dashboard metric."""
    if metric not in SUPPORTED_COMPARE_METRICS:
        raise ValueError(
            "Unsupported metric. Choose one of: "
            + ", ".join(sorted(SUPPORTED_COMPARE_METRICS))
        )
    return sorted(
        _posts(data),
        key=lambda post: (_metric_value(post, metric), str(post.get("post_id") or "")),
        reverse=True,
    )[: max(limit, 0)]
