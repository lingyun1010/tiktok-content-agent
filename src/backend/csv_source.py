"""CSV ingestion for local TikTok analytics exports."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any


def load_posts(path: Path, limit: int) -> list[dict[str, Any]]:
    """Load at most ``limit`` post records from a CSV file."""
    if limit < 1:
        raise ValueError("--limit must be at least 1")
    if not path.exists():
        raise FileNotFoundError(f"Input CSV not found: {path}")

    with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        if not reader.fieldnames:
            raise ValueError("Input CSV must include a header row")
        rows = []
        for row_number, row in enumerate(reader, start=2):
            rows.append({"_row_number": row_number, **row})
            if len(rows) >= limit:
                break
    return rows

