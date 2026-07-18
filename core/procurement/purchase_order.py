"""
Purchase-order draft generation grouped by supplier.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from core.procurement.lead_time import get_alerts, urgency_label

ROOT = Path(__file__).resolve().parent.parent.parent


def _po_id(supplier_id: str, supplier_name: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    key = (supplier_id or supplier_name or "unassigned").replace(" ", "_")[:24]
    return f"PO-{key}-{stamp}"


def generate_po_drafts(conn) -> list[dict[str, Any]]:
    """Build PO draft payloads from current reorder alerts."""
    alerts = get_alerts(conn)
    if alerts.empty:
        return []

    drafts: list[dict[str, Any]] = []
    grouped = alerts.groupby(["supplier_id", "supplier_name"], dropna=False)

    for (supplier_id, supplier_name), grp in grouped:
        sid = str(supplier_id or "")
        sname = str(supplier_name or "Não atribuído")
        po_id = _po_id(sid, sname)
        lines = []
        for row in grp.itertuples(index=False):
            qty = int(getattr(row, "suggested_qty", 0) or 0)
            if qty <= 0:
                continue
            unit_cost = float(getattr(row, "unit_cost", 0) or 0)
            days = float(getattr(row, "days_remaining", 9999) or 9999)
            lead = float(getattr(row, "lead_time", 12) or 12)
            lines.append({
                "sku": str(getattr(row, "sku", "")),
                "product": str(getattr(row, "product", "")),
                "qty": qty,
                "unit_cost": unit_cost,
                "line_total": round(qty * unit_cost, 2),
                "urgency": urgency_label(days, lead),
                "days_remaining": int(days),
                "rationale": f"Cobertura {days:.0f}d restantes; lead {lead:.0f}d",
            })

        if not lines:
            continue

        drafts.append({
            "po_id": po_id,
            "supplier_id": sid,
            "supplier_name": sname,
            "status": "draft",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "po_total_brl": round(sum(l["line_total"] for l in lines), 2),
            "line_count": len(lines),
            "lines": lines,
        })

    return drafts


def export_po_artifacts(conn, out_dir: Path | None = None) -> dict[str, Any]:
    """Write po_drafts.json and per-supplier Excel files."""
    out = out_dir or (ROOT / "data" / "outputs" / "purchase_orders")
    out.mkdir(parents=True, exist_ok=True)

    drafts = generate_po_drafts(conn)
    json_path = out / "po_drafts.json"
    payload = {"generated_at": datetime.now(timezone.utc).isoformat(), "purchase_orders": drafts}
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    xlsx_paths: list[str] = []
    for po in drafts:
        lines_df = pd.DataFrame(po["lines"])
        if lines_df.empty:
            continue
        safe_name = po["supplier_name"].replace("/", "-")[:40]
        xlsx_path = out / f"{po['po_id']}_{safe_name}.xlsx"
        with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
            lines_df.to_excel(writer, sheet_name="Linhas", index=False)
            summary = pd.DataFrame([{
                "po_id": po["po_id"],
                "supplier": po["supplier_name"],
                "total_brl": po["po_total_brl"],
                "status": po["status"],
            }])
            summary.to_excel(writer, sheet_name="Resumo", index=False)
        xlsx_paths.append(str(xlsx_path))

    return {
        "json_path": str(json_path),
        "xlsx_paths": xlsx_paths,
        "po_count": len(drafts),
        "drafts": drafts,
    }
