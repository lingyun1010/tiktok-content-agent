"""Compatibility wrapper for the Phase 6 analyst module."""

from __future__ import annotations

from typing import Any

from .analyst import AnalystError as AnalystChatError
from .analyst import answer_question as _answer_question


def answer_question(question: str, dashboard_data: dict[str, Any]) -> dict[str, Any]:
    """Answer with the default manual analyst provider."""
    return _answer_question(question, dashboard_data, provider="manual")
