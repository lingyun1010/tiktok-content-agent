"""Airtable ingestion mapped to the canonical TikTok post fields."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from ..schema import CANONICAL_CSV_FIELDS

AIRTABLE_ENV_VARS = (
    "AIRTABLE_API_KEY",
    "AIRTABLE_BASE_ID",
    "AIRTABLE_TABLE_ID",
    "AIRTABLE_VIEW_ID",
)


class AirtableError(RuntimeError):
    """Raised when Airtable configuration or retrieval fails safely."""


@dataclass(frozen=True)
class AirtableConfig:
    """Environment-backed Airtable connection settings."""

    api_key: str
    base_id: str
    table_id: str
    view_id: str

    @classmethod
    def from_environment(
        cls, environ: Mapping[str, str] | None = None
    ) -> "AirtableConfig":
        """Load required settings without exposing their values."""
        if environ is None:
            dotenv_path = Path.cwd() / ".env"
            if dotenv_path.is_file():
                try:
                    from dotenv import load_dotenv
                except ModuleNotFoundError as exc:
                    raise AirtableError(
                        "Local .env loading requires python-dotenv; install "
                        "dependencies with: python3 -m pip install -r requirements.txt"
                    ) from exc
                load_dotenv(dotenv_path=dotenv_path, override=False)
            values = os.environ
        else:
            values = environ
        missing = [name for name in AIRTABLE_ENV_VARS if not values.get(name, "").strip()]
        if missing:
            raise AirtableError(
                "Airtable source requires these environment variables: "
                + ", ".join(missing)
            )
        config = cls(*(values[name].strip() for name in AIRTABLE_ENV_VARS))
        expected_prefixes = {
            "AIRTABLE_BASE_ID": (config.base_id, "app"),
            "AIRTABLE_TABLE_ID": (config.table_id, "tbl"),
            "AIRTABLE_VIEW_ID": (config.view_id, "viw"),
        }
        invalid = [
            f"{name} must start with '{prefix}'"
            for name, (value, prefix) in expected_prefixes.items()
            if not value.startswith(prefix)
        ]
        if invalid:
            raise AirtableError("Invalid Airtable configuration: " + "; ".join(invalid))
        return config


def _request_page(
    config: AirtableConfig,
    *,
    limit: int,
    offset: str | None,
    opener: Callable[..., Any],
) -> dict[str, Any]:
    query = {"pageSize": min(limit, 100), "view": config.view_id}
    if offset:
        query["offset"] = offset
    url = (
        "https://api.airtable.com/v0/"
        f"{quote(config.base_id, safe='')}/{quote(config.table_id, safe='')}"
        f"?{urlencode(query)}"
    )
    request = Request(
        url,
        headers={
            "Authorization": f"Bearer {config.api_key}",
            "Accept": "application/json",
        },
    )
    try:
        with opener(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise AirtableError(
            f"Airtable request failed with HTTP status {exc.code}"
        ) from exc
    except (URLError, TimeoutError) as exc:
        raise AirtableError("Airtable request failed; check network access") from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AirtableError("Airtable returned an invalid JSON response") from exc

    if not isinstance(payload, dict) or not isinstance(payload.get("records"), list):
        raise AirtableError("Airtable response did not contain a records list")
    return payload


def load_posts(
    limit: int,
    *,
    environ: Mapping[str, str] | None = None,
    opener: Callable[..., Any] | None = None,
) -> list[dict[str, Any]]:
    """Retrieve at most ``limit`` Airtable records as canonical raw mappings."""
    if limit < 1:
        raise ValueError("--limit must be at least 1")

    config = AirtableConfig.from_environment(environ)
    open_request = urlopen if opener is None else opener
    rows: list[dict[str, Any]] = []
    offset: str | None = None

    while len(rows) < limit:
        payload = _request_page(
            config,
            limit=limit - len(rows),
            offset=offset,
            opener=open_request,
        )
        for record in payload["records"]:
            if not isinstance(record, dict) or not isinstance(record.get("fields"), dict):
                raise AirtableError("Airtable returned a record without a fields object")
            fields = record["fields"]
            canonical_fields = {}
            for field in CANONICAL_CSV_FIELDS:
                value = fields.get(field)
                canonical_fields[field] = "" if value is None else value
            rows.append(
                {
                    "_row_number": len(rows) + 1,
                    **canonical_fields,
                }
            )
            if len(rows) >= limit:
                break

        raw_offset = payload.get("offset")
        offset = raw_offset if isinstance(raw_offset, str) and raw_offset else None
        if not offset or not payload["records"]:
            break

    return rows
