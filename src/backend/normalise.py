"""Normalisation helpers for TikTok post records."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from urllib.parse import urlparse

from .schema import REQUIRED_CSV_FIELDS, TikTokPost


def _required_text(record: dict[str, Any], field: str, row_number: int) -> str:
    value = str(record.get(field, "")).strip()
    if not value:
        raise ValueError(f"Row {row_number}: missing required field '{field}'")
    return value


def _number(
    record: dict[str, Any],
    field: str,
    row_number: int,
    *,
    optional: bool = False,
) -> float | None:
    raw_value = str(record.get(field, "")).strip()
    if optional and raw_value == "":
        return None
    if raw_value == "":
        raise ValueError(f"Row {row_number}: missing required field '{field}'")
    try:
        value = float(raw_value)
    except ValueError as exc:
        raise ValueError(
            f"Row {row_number}: '{field}' must be numeric, got {raw_value!r}"
        ) from exc
    if value < 0:
        raise ValueError(f"Row {row_number}: '{field}' cannot be negative")
    return value


def _integer(
    record: dict[str, Any],
    field: str,
    row_number: int,
    *,
    optional: bool = False,
) -> int | None:
    value = _number(record, field, row_number, optional=optional)
    if value is None:
        return None
    if not value.is_integer():
        raise ValueError(f"Row {row_number}: '{field}' must be a whole number")
    return int(value)


def _optional_text(record: dict[str, Any], field: str) -> str | None:
    return str(record.get(field, "")).strip() or None


def _fraction(
    record: dict[str, Any], field: str, row_number: int
) -> float | None:
    value = _number(record, field, row_number, optional=True)
    if value is not None and value > 1:
        raise ValueError(
            f"Row {row_number}: '{field}' must be between 0 and 1"
        )
    return value


def _published_at(record: dict[str, Any], row_number: int) -> str:
    value = _required_text(record, "published_at", row_number)
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(
            f"Row {row_number}: 'published_at' must be an ISO 8601 datetime"
        ) from exc
    return value


def _post_url(record: dict[str, Any], row_number: int) -> str | None:
    value = _optional_text(record, "post_url")
    if value is None:
        return None
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(
            f"Row {row_number}: 'post_url' must be an absolute HTTP(S) URL"
        )
    return value


def normalise_post(record: dict[str, Any]) -> TikTokPost:
    """Convert one source record into the canonical TikTok post structure."""
    row_number = int(record.get("_row_number", 0))
    for field in REQUIRED_CSV_FIELDS:
        if field not in record:
            raise ValueError(f"Input record is missing required field '{field}'")
    platform = _required_text(record, "platform", row_number).lower()
    if platform != "tiktok":
        raise ValueError(f"Row {row_number}: 'platform' must be 'tiktok'")
    duration = _number(record, "duration_seconds", row_number) or 0.0
    if duration <= 0:
        raise ValueError(
            f"Row {row_number}: 'duration_seconds' must be greater than zero"
        )

    return {
        "post_id": _required_text(record, "post_id", row_number),
        "platform": platform,
        "post_url": _post_url(record, row_number),
        "published_at": _published_at(record, row_number),
        "format": _required_text(record, "format", row_number),
        "topic": _required_text(record, "topic", row_number),
        "hook": _required_text(record, "hook", row_number),
        "caption": _required_text(record, "caption", row_number),
        "duration_seconds": duration,
        "views": _integer(record, "views", row_number) or 0,
        "likes": _integer(record, "likes", row_number) or 0,
        "comments": _integer(record, "comments", row_number) or 0,
        "shares": _integer(record, "shares", row_number) or 0,
        "saves": _integer(record, "saves", row_number, optional=True),
        "average_watch_time_seconds": _number(
            record, "average_watch_time_seconds", row_number, optional=True
        ),
        "completion_rate": _fraction(record, "completion_rate", row_number),
        "top_region": _optional_text(record, "top_region"),
        "target_region": _optional_text(record, "target_region"),
        "top_region_view_percentage": _fraction(
            record, "top_region_view_percentage", row_number
        ),
        "notes": _optional_text(record, "notes"),
    }


def normalise_posts(records: list[dict[str, Any]]) -> list[TikTokPost]:
    """Normalise a collection of raw source records."""
    posts = [normalise_post(record) for record in records]
    post_ids = [post["post_id"] for post in posts]
    if len(post_ids) != len(set(post_ids)):
        raise ValueError("Input contains duplicate 'post_id' values")
    return posts
