"""Opt-in LLM strategy providers with compact inputs and validated outputs."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

CONTENT_PLAN_SCHEMA_VERSION = "1.0"
OPENAI_ENDPOINT = "https://api.openai.com/v1/responses"
CLAUDE_ENDPOINT = "https://api.anthropic.com/v1/messages"
DEFAULT_OPENAI_MODEL = "gpt-4.1-mini"
DEFAULT_CLAUDE_MODEL = "claude-sonnet-4-5"
REQUEST_TIMEOUT_SECONDS = 60


class LLMStrategyError(ValueError):
    """Raised when provider configuration, transport, or output is invalid."""


def _load_local_dotenv() -> None:
    dotenv_path = Path.cwd() / ".env"
    if not dotenv_path.is_file():
        return
    try:
        from dotenv import load_dotenv
    except ImportError as exc:
        raise LLMStrategyError(
            "Local .env loading requires python-dotenv; install requirements.txt "
            "or export provider variables in the shell."
        ) from exc
    load_dotenv(dotenv_path=dotenv_path, override=False)


def _required_environment(name: str, provider: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise LLMStrategyError(
            f"{provider} provider requires {name}. Configure it in the environment "
            "or an ignored local .env file."
        )
    return value


def configured_provider_name() -> str:
    """Return MODEL_PROVIDER from the shell or local .env, defaulting to manual."""
    _load_local_dotenv()
    return os.getenv("MODEL_PROVIDER", "manual").strip().lower() or "manual"


def _prompt_text() -> str:
    path = Path(__file__).resolve().parents[2] / "prompts" / "content_strategy.md"
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise LLMStrategyError(
            f"Unable to read the strategy prompt at {path.as_posix()}."
        ) from exc


def _analysis_basis(
    posts: list[dict[str, Any]], summary: dict[str, Any]
) -> dict[str, Any]:
    return {
        "post_count": summary["post_count"],
        "top_post_id": summary["top_post"]["post_id"],
        "repeat_candidate_post_ids": [
            post["post_id"] for post in posts if "repeat_candidate" in post["signals"]
        ],
        "pause_candidate_post_ids": [
            post["post_id"] for post in posts if "pause_candidate" in post["signals"]
        ],
        "weak_retention_post_ids": [
            post["post_id"]
            for post in posts
            if post["average_watch_ratio"] is not None
            and post["average_watch_ratio"] < 0.5
        ],
    }


def build_compact_strategy_input(
    posts: list[dict[str, Any]], summary: dict[str, Any]
) -> dict[str, Any]:
    """Build a bounded payload without raw records, captions, URLs, or notes."""
    return {
        "brand_context": {
            "brand_type": "small direct-to-consumer premium herbal haircare brand",
            "audience": "people seeking practical, trustworthy haircare education",
            "guardrails": [
                "Use a clear, warm, evidence-aware tone.",
                "Avoid medical claims, guarantees, and unsupported product claims.",
                "All output is a draft requiring human review.",
            ],
        },
        "metrics_summary": {
            "post_count": summary["post_count"],
            "total_views": summary["total_views"],
            "average_views": summary["average_views"],
            "average_engagement_rate": summary["average_engagement_rate"],
            "average_watch_ratio": summary["average_watch_ratio"],
            "average_region_match_score": summary["average_region_match_score"],
            "topic_coverage_count": summary["topic_coverage_count"],
            "region_coverage_count": summary["region_coverage_count"],
            "signal_counts": summary["signal_counts"],
            "format_performance": summary["format_performance"],
            "topic_performance": summary["topic_performance"],
        },
        "post_signals": [
            {
                "post_id": post["post_id"],
                "format": post["format"],
                "topic": post["topic"],
                "hook": post["hook"],
                "engagement_rate": post["engagement_rate"],
                "average_watch_ratio": post["average_watch_ratio"],
                "region_match_score": post["region_match_score"],
                "signals": post["signals"],
            }
            for post in posts
        ],
        "required_response_schema": {
            "strategy": {
                "primary_goal": "string",
                "repeat": {
                    "source_post_id": "existing post_id",
                    "format": "string",
                    "topic": "string or null",
                    "reason": "string",
                },
                "pause": [
                    {
                        "post_id": "existing post_id",
                        "format": "string",
                        "topic": "string or null",
                        "action": "string",
                        "reason": "string",
                    }
                ],
                "retention_adjustment": {
                    "required": "boolean",
                    "affected_post_ids": ["existing post_id"],
                    "guidance": "string",
                },
            },
            "content_item": {
                "id": "string",
                "working_title": "string",
                "format": "string",
                "topic": "string or null",
                "source_post_id": "existing post_id",
                "creative_direction": "string",
                "script": {
                    "hook": "string",
                    "body": ["string"],
                    "cta": "string",
                },
                "caption": "string",
                "hashtags": ["#Hashtag"],
                "review_checks": ["string"],
            },
            "limitations": ["string"],
        },
    }


def _require_object(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise LLMStrategyError(f"LLM response field '{path}' must be an object.")
    return value


def _require_list(value: Any, path: str) -> list[Any]:
    if not isinstance(value, list):
        raise LLMStrategyError(f"LLM response field '{path}' must be a list.")
    return value


def _require_string(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LLMStrategyError(
            f"LLM response field '{path}' must be a non-empty string."
        )
    return value


def _require_nullable_string(value: Any, path: str) -> str | None:
    if value is not None and (not isinstance(value, str) or not value.strip()):
        raise LLMStrategyError(
            f"LLM response field '{path}' must be a string or null."
        )
    return value


def _required_field(mapping: dict[str, Any], name: str, path: str) -> Any:
    if name not in mapping:
        raise LLMStrategyError(
            f"LLM response is missing required field '{path}.{name}'."
        )
    return mapping[name]


def _validate_post_id(value: Any, path: str, post_ids: set[str]) -> str:
    post_id = _require_string(value, path)
    if post_id not in post_ids:
        raise LLMStrategyError(
            f"LLM response field '{path}' references unknown post ID '{post_id}'."
        )
    return post_id


def _validate_string_list(value: Any, path: str, *, non_empty: bool = True) -> list[str]:
    values = _require_list(value, path)
    if non_empty and not values:
        raise LLMStrategyError(f"LLM response field '{path}' must not be empty.")
    for index, item in enumerate(values):
        _require_string(item, f"{path}[{index}]")
    return values


def validate_llm_plan(
    payload: Any,
    *,
    provider: str,
    posts: list[dict[str, Any]],
    summary: dict[str, Any],
) -> dict[str, Any]:
    """Validate provider JSON and add Python-owned evidence metadata."""
    root = _require_object(payload, "root")
    post_ids = {post["post_id"] for post in posts}

    strategy = _require_object(
        _required_field(root, "strategy", "root"), "strategy"
    )
    _require_string(
        _required_field(strategy, "primary_goal", "strategy"),
        "strategy.primary_goal",
    )
    repeat = _require_object(
        _required_field(strategy, "repeat", "strategy"), "strategy.repeat"
    )
    _validate_post_id(
        _required_field(repeat, "source_post_id", "strategy.repeat"),
        "strategy.repeat.source_post_id",
        post_ids,
    )
    _require_string(
        _required_field(repeat, "format", "strategy.repeat"),
        "strategy.repeat.format",
    )
    _require_nullable_string(
        _required_field(repeat, "topic", "strategy.repeat"),
        "strategy.repeat.topic",
    )
    _require_string(
        _required_field(repeat, "reason", "strategy.repeat"),
        "strategy.repeat.reason",
    )

    pause = _require_list(
        _required_field(strategy, "pause", "strategy"), "strategy.pause"
    )
    for index, value in enumerate(pause):
        item_path = f"strategy.pause[{index}]"
        item = _require_object(value, item_path)
        _validate_post_id(
            _required_field(item, "post_id", item_path),
            f"{item_path}.post_id",
            post_ids,
        )
        _require_string(
            _required_field(item, "format", item_path), f"{item_path}.format"
        )
        _require_nullable_string(
            _required_field(item, "topic", item_path), f"{item_path}.topic"
        )
        _require_string(
            _required_field(item, "action", item_path), f"{item_path}.action"
        )
        _require_string(
            _required_field(item, "reason", item_path), f"{item_path}.reason"
        )

    retention = _require_object(
        _required_field(strategy, "retention_adjustment", "strategy"),
        "strategy.retention_adjustment",
    )
    required = _required_field(
        retention, "required", "strategy.retention_adjustment"
    )
    if not isinstance(required, bool):
        raise LLMStrategyError(
            "LLM response field 'strategy.retention_adjustment.required' "
            "must be a boolean."
        )
    affected_ids = _require_list(
        _required_field(
            retention, "affected_post_ids", "strategy.retention_adjustment"
        ),
        "strategy.retention_adjustment.affected_post_ids",
    )
    for index, post_id in enumerate(affected_ids):
        _validate_post_id(
            post_id,
            f"strategy.retention_adjustment.affected_post_ids[{index}]",
            post_ids,
        )
    _require_string(
        _required_field(
            retention, "guidance", "strategy.retention_adjustment"
        ),
        "strategy.retention_adjustment.guidance",
    )

    content_item = _require_object(
        _required_field(root, "content_item", "root"), "content_item"
    )
    for field in ("id", "working_title", "format", "creative_direction", "caption"):
        _require_string(
            _required_field(content_item, field, "content_item"),
            f"content_item.{field}",
        )
    _require_nullable_string(
        _required_field(content_item, "topic", "content_item"),
        "content_item.topic",
    )
    _validate_post_id(
        _required_field(content_item, "source_post_id", "content_item"),
        "content_item.source_post_id",
        post_ids,
    )
    script = _require_object(
        _required_field(content_item, "script", "content_item"),
        "content_item.script",
    )
    _require_string(
        _required_field(script, "hook", "content_item.script"),
        "content_item.script.hook",
    )
    _validate_string_list(
        _required_field(script, "body", "content_item.script"),
        "content_item.script.body",
    )
    _require_string(
        _required_field(script, "cta", "content_item.script"),
        "content_item.script.cta",
    )
    hashtags = _validate_string_list(
        _required_field(content_item, "hashtags", "content_item"),
        "content_item.hashtags",
    )
    if any(not hashtag.startswith("#") for hashtag in hashtags):
        raise LLMStrategyError(
            "LLM response field 'content_item.hashtags' must contain hashtags "
            "beginning with '#'."
        )
    _validate_string_list(
        _required_field(content_item, "review_checks", "content_item"),
        "content_item.review_checks",
    )
    _validate_string_list(
        _required_field(root, "limitations", "root"), "limitations"
    )

    return {
        "schema_version": CONTENT_PLAN_SCHEMA_VERSION,
        "status": "draft_for_human_review",
        "provider": provider,
        "llm_called": True,
        "human_review_required": True,
        "analysis_basis": _analysis_basis(posts, summary),
        "strategy": strategy,
        "content_item": content_item,
        "limitations": root["limitations"],
    }


def _decode_json_response(text: str, provider: str) -> dict[str, Any]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise LLMStrategyError(
            f"{provider} returned invalid JSON; no strategy files were exported. "
            f"JSON error at line {exc.lineno}, column {exc.colno}."
        ) from exc
    if not isinstance(payload, dict):
        raise LLMStrategyError(
            f"{provider} returned valid JSON but the root value was not an object."
        )
    return payload


def _post_json(
    url: str, headers: dict[str, str], body: dict[str, Any], provider: str
) -> dict[str, Any]:
    request = Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    try:
        with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8"))
            if not isinstance(payload, dict):
                raise LLMStrategyError(
                    f"{provider} returned an unexpected API response shape."
                )
            return payload
    except HTTPError as exc:
        raise LLMStrategyError(
            f"{provider} request failed with HTTP {exc.code}. Check the configured "
            "key, model, account access, and provider status."
        ) from exc
    except URLError as exc:
        raise LLMStrategyError(
            f"{provider} request could not reach the provider API. Check the network "
            "connection and try again."
        ) from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LLMStrategyError(
            f"{provider} returned an unreadable API response."
        ) from exc


@dataclass(repr=False)
class OpenAIStrategyProvider:
    """Generate strategy with the OpenAI Responses API."""

    api_key: str
    model: str
    name: str = "openai"

    @classmethod
    def from_environment(cls) -> "OpenAIStrategyProvider":
        _load_local_dotenv()
        return cls(
            api_key=_required_environment("OPENAI_API_KEY", "OpenAI"),
            model=os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL).strip()
            or DEFAULT_OPENAI_MODEL,
        )

    def generate_plan(
        self, posts: list[dict[str, Any]], summary: dict[str, Any]
    ) -> dict[str, Any]:
        request_payload = build_compact_strategy_input(posts, summary)
        response = _post_json(
            OPENAI_ENDPOINT,
            {"Authorization": f"Bearer {self.api_key}"},
            {
                "model": self.model,
                "instructions": _prompt_text(),
                "input": json.dumps(request_payload, ensure_ascii=False),
            },
            "OpenAI",
        )
        texts = [
            part["text"]
            for item in response.get("output", [])
            for part in item.get("content", [])
            if part.get("type") == "output_text" and isinstance(part.get("text"), str)
        ]
        if not texts:
            raise LLMStrategyError(
                "OpenAI returned no text content; no strategy files were exported."
            )
        payload = _decode_json_response("".join(texts), "OpenAI")
        return validate_llm_plan(
            payload, provider=self.name, posts=posts, summary=summary
        )


@dataclass(repr=False)
class ClaudeStrategyProvider:
    """Generate strategy with the Anthropic Claude Messages API."""

    api_key: str
    model: str
    name: str = "claude"

    @classmethod
    def from_environment(cls) -> "ClaudeStrategyProvider":
        _load_local_dotenv()
        return cls(
            api_key=_required_environment("CLAUDE_API_KEY", "Claude"),
            model=os.getenv("CLAUDE_MODEL", DEFAULT_CLAUDE_MODEL).strip()
            or DEFAULT_CLAUDE_MODEL,
        )

    def generate_plan(
        self, posts: list[dict[str, Any]], summary: dict[str, Any]
    ) -> dict[str, Any]:
        request_payload = build_compact_strategy_input(posts, summary)
        response = _post_json(
            CLAUDE_ENDPOINT,
            {
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
            },
            {
                "model": self.model,
                "max_tokens": 4096,
                "system": _prompt_text(),
                "messages": [
                    {
                        "role": "user",
                        "content": json.dumps(request_payload, ensure_ascii=False),
                    }
                ],
            },
            "Claude",
        )
        texts = [
            item["text"]
            for item in response.get("content", [])
            if item.get("type") == "text" and isinstance(item.get("text"), str)
        ]
        if not texts:
            raise LLMStrategyError(
                "Claude returned no text content; no strategy files were exported."
            )
        payload = _decode_json_response("".join(texts), "Claude")
        return validate_llm_plan(
            payload, provider=self.name, posts=posts, summary=summary
        )
