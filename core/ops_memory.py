"""
FulôFiló — Operational Memory
=============================
Tracks alert → operator action → outcome for postmortem and false-positive analysis.
"""

from __future__ import annotations

import csv
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
OPS_DECISIONS_PATH = ROOT / "data" / "logs" / "ops_decisions.csv"

_DECISION_HEADERS = [
    "decision_id",
    "timestamp",
    "alert_type",
    "sku",
    "product",
    "alert_priority",
    "action_taken",
    "outcome",
    "notes",
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def log_decision(
    *,
    alert_type: str,
    action_taken: str,
    sku: str = "",
    product: str = "",
    alert_priority: str = "",
    outcome: str = "pending",
    notes: str = "",
    decision_id: str | None = None,
) -> dict[str, Any]:
    """Append one operator decision to ops_decisions.csv."""
    OPS_DECISIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "decision_id": decision_id or str(uuid.uuid4())[:8],
        "timestamp": _utc_now(),
        "alert_type": alert_type,
        "sku": sku,
        "product": product,
        "alert_priority": alert_priority,
        "action_taken": action_taken,
        "outcome": outcome,
        "notes": notes,
    }
    write_header = not OPS_DECISIONS_PATH.exists() or OPS_DECISIONS_PATH.stat().st_size == 0
    with OPS_DECISIONS_PATH.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=_DECISION_HEADERS)
        if write_header:
            writer.writeheader()
        writer.writerow(record)
    return record


def list_decisions(limit: int = 100) -> list[dict[str, str]]:
    """Return recent decisions (newest last)."""
    if not OPS_DECISIONS_PATH.exists():
        return []
    with OPS_DECISIONS_PATH.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return rows[-limit:]
