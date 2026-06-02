"""
FulôFiló — Operational Event Log
================================
Append-only JSONL timeline for sync, alerts, inventory mutations, and automation runs.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
OPS_EVENTS_PATH = ROOT / "data" / "logs" / "ops_events.jsonl"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def emit_event(
    event_type: str,
    *,
    severity: str = "INFO",
    message: str = "",
    sku: str | None = None,
    product: str | None = None,
    action: str | None = None,
    signals: dict[str, Any] | None = None,
    source: str = "system",
) -> dict[str, Any]:
    """Append one operational event to ops_events.jsonl."""
    OPS_EVENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    record: dict[str, Any] = {
        "ts": _utc_now(),
        "type": event_type,
        "severity": severity,
        "message": message,
        "source": source,
    }
    if sku:
        record["sku"] = sku
    if product:
        record["product"] = product
    if action:
        record["action"] = action
    if signals:
        record["signals"] = signals

    with OPS_EVENTS_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def read_recent_events(limit: int = 50) -> list[dict[str, Any]]:
    """Return the most recent events (newest first)."""
    if not OPS_EVENTS_PATH.exists():
        return []

    lines = OPS_EVENTS_PATH.read_text(encoding="utf-8").splitlines()
    events: list[dict[str, Any]] = []
    for line in reversed(lines[-500:]):
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
        if len(events) >= limit:
            break
    return events


def events_to_feed_rows(
    events: list[dict[str, Any]],
    *,
    time_fmt: str = "%H:%M",
    severity_colors: dict[str, str] | None = None,
) -> list[dict[str, str]]:
    """Convert event records into terminal feed row dicts."""
    colors = severity_colors or {
        "HIGH": "#FF4444",
        "CRITICAL": "#FF4444",
        "MEDIUM": "#FFB020",
        "LOW": "#00D4FF",
        "INFO": "#FFD700",
    }
    rows: list[dict[str, str]] = []
    for ev in events:
        ts_raw = str(ev.get("ts", ""))
        try:
            ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
            time_label = ts.astimezone().strftime(time_fmt)
        except ValueError:
            time_label = ts_raw[11:16] if len(ts_raw) >= 16 else "----"

        severity = str(ev.get("severity", "INFO")).upper()
        rows.append(
            {
                "time": time_label,
                "type": str(ev.get("type", "EVENT"))[:8],
                "message": str(ev.get("message", "")),
                "color": colors.get(severity, colors["INFO"]),
            }
        )
    return rows
