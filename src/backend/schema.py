"""Canonical field definitions for TikTok post analytics records."""

from __future__ import annotations

from typing import TypedDict

REQUIRED_CSV_FIELDS = (
    "post_id",
    "platform",
    "published_at",
    "format",
    "caption",
    "duration_seconds",
    "views",
    "likes",
    "comments",
    "shares",
)

OPTIONAL_CSV_FIELDS = (
    "post_url",
    "topic",
    "hook",
    "saves",
    "average_watch_time_seconds",
    "completion_rate",
    "top_region",
    "target_region",
    "top_region_view_percentage",
    "notes",
)

CANONICAL_CSV_FIELDS = REQUIRED_CSV_FIELDS + OPTIONAL_CSV_FIELDS


class TikTokPost(TypedDict):
    """Canonical normalised record used by analytics and future adapters."""

    post_id: str
    platform: str
    post_url: str | None
    published_at: str
    format: str
    topic: str | None
    hook: str | None
    caption: str
    duration_seconds: float
    views: int
    likes: int
    comments: int
    shares: int
    saves: int | None
    average_watch_time_seconds: float | None
    completion_rate: float | None
    top_region: str | None
    target_region: str | None
    top_region_view_percentage: float | None
    notes: str | None
