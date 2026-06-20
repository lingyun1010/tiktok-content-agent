"""Normalisation helpers for TikTok post records."""

from __future__ import annotations

from typing import Any

REQUIRED_FIELDS = (
    "post_id",
    "posted_at",
    "caption",
    "views",
    "likes",
    "comments",
    "shares",
)


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


def normalise_post(record: dict[str, Any]) -> dict[str, Any]:
    """Convert one CSV row into the backend's consistent post structure."""
    row_number = int(record.get("_row_number", 0))
    for field in REQUIRED_FIELDS:
        if field not in record:
            raise ValueError(f"Input CSV is missing required column '{field}'")

    return {
        "post_id": _required_text(record, "post_id", row_number),
        "posted_at": _required_text(record, "posted_at", row_number),
        "caption": _required_text(record, "caption", row_number),
        "views": int(_number(record, "views", row_number) or 0),
        "likes": int(_number(record, "likes", row_number) or 0),
        "comments": int(_number(record, "comments", row_number) or 0),
        "shares": int(_number(record, "shares", row_number) or 0),
        "saves": _optional_int(record, "saves", row_number),
        "duration_seconds": _number(
            record, "duration_seconds", row_number, optional=True
        ),
        "average_watch_time_seconds": _number(
            record, "average_watch_time_seconds", row_number, optional=True
        ),
        "content_pillar": str(record.get("content_pillar", "")).strip() or None,
        "hook": str(record.get("hook", "")).strip() or None,
    }


def _optional_int(
    record: dict[str, Any], field: str, row_number: int
) -> int | None:
    value = _number(record, field, row_number, optional=True)
    return int(value) if value is not None else None


def normalise_posts(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalise a collection of raw CSV records."""
    return [normalise_post(record) for record in records]

