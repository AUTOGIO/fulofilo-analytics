"""
FulôFiló — Smart Reorder Alert Engine
=======================================
Calculates when to reorder each product based on:
  - Giro (sell-through rate) from March + April 2026 sales history
  - Supplier lead time + safety buffer
  - Suggested order quantity for 45-day coverage

Formula:
  daily_rate     = qty_sold / SALES_PERIOD_DAYS
  days_remaining = current_stock / daily_rate
  ALERT when:    days_remaining ≤ LEAD_TIME + BUFFER  (24 days)
  suggested_qty  = ceil(daily_rate × COVERAGE_DAYS)   (45 days)
"""

from __future__ import annotations

import math
import os
import subprocess
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent

# ── Configuration (all changeable per supplier later) ─────────────────────────
SALES_PERIOD_DAYS = 61   # March 1 – April 30, 2026
LEAD_TIME_DAYS    = 12   # Default supplier lead time (days)
BUFFER_DAYS       = 12   # Safety buffer (days)
ALERT_THRESHOLD   = LEAD_TIME_DAYS + BUFFER_DAYS   # 24 days
COVERAGE_DAYS     = 45   # Target reorder coverage (days)


# ── Core Query ────────────────────────────────────────────────────────────────

def get_reorder_df(conn) -> pd.DataFrame:
    """
    Full reorder analysis — all products with sales data (period='2026').
    Uses products table directly; current_stock from inventory JOIN where
    available, otherwise falls back to DEFAULT_STOCK (300 units).
    Products with zero sales are excluded (no giro to calculate).
    """
    DEFAULT_STOCK = 300  # baseline set at system initialization

    try:
        df = conn.execute(f"""
            SELECT
                p.sku                                                                AS slug,
                p.full_name                                                          AS product,
                p.category,
                COALESCE(NULLIF(i.current_stock, 0), {DEFAULT_STOCK})               AS current_stock,
                p.qty_sold,
                ROUND(p.qty_sold::FLOAT / {SALES_PERIOD_DAYS}, 3)                  AS daily_rate,
                ROUND(
                    COALESCE(NULLIF(i.current_stock, 0), {DEFAULT_STOCK})::FLOAT /
                    (p.qty_sold::FLOAT / {SALES_PERIOD_DAYS})
                , 0)                                                                 AS days_remaining,
                CEIL(p.qty_sold::FLOAT / {SALES_PERIOD_DAYS} * {COVERAGE_DAYS})     AS suggested_qty,
                {LEAD_TIME_DAYS}                                                     AS lead_time,
                {BUFFER_DAYS}                                                        AS buffer,
                {ALERT_THRESHOLD}                                                    AS alert_threshold
            FROM products p
            LEFT JOIN inventory i ON lower(p.full_name) = lower(i.product)
            WHERE p.period = '2026'
              AND p.qty_sold > 0
            ORDER BY days_remaining ASC
        """).df()
        return df
    except Exception:
        return pd.DataFrame()


def get_alerts(conn) -> pd.DataFrame:
    """Return only products that need reordering (days_remaining ≤ 24)."""
    df = get_reorder_df(conn)
    if df.empty:
        return df
    return df[df["days_remaining"] <= ALERT_THRESHOLD].reset_index(drop=True)


def urgency_label(days: float) -> str:
    """Classify urgency based on days remaining."""
    if days <= LEAD_TIME_DAYS:
        return "🔴 URGENTE"
    elif days <= ALERT_THRESHOLD:
        return "🟡 ATENÇÃO"
    return "🟢 OK"


# ── Excel Export ──────────────────────────────────────────────────────────────

def export_excel(conn) -> Path | None:
    """
    Generate data/outputs/alertas_reposicao.xlsx with two sheets:
      - ⚠️ Reposição Urgente  → products needing reorder now
      - 📦 Todos os Produtos  → full analysis
    Returns Path to the file, or None if no data.
    """
    df = get_reorder_df(conn)
    if df.empty:
        return None

    out_dir = ROOT / "data" / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "alertas_reposicao.xlsx"

    # ── Prepare display DataFrame ──────────────────────────────────────────────
    display = df.copy()
    display["days_remaining"] = display["days_remaining"].astype(int)
    display["suggested_qty"]  = display["suggested_qty"].astype(int)
    display["daily_rate"]     = display["daily_rate"].round(2)
    display["urgency"]        = display["days_remaining"].apply(urgency_label)

    display = display.rename(columns={
        "product":        "Produto",
        "category":       "Categoria",
        "current_stock":  "Estoque Atual",
        "qty_sold":       "Vendido (Mar–Abr)",
        "daily_rate":     "Venda/Dia",
        "days_remaining": "Dias Restantes",
        "suggested_qty":  "Qtd Sugerida (45d)",
        "lead_time":      "Lead Time (dias)",
        "buffer":         "Buffer (dias)",
        "alert_threshold":"Limiar Alerta (dias)",
        "urgency":        "Urgência",
    }).drop(columns=["slug"], errors="ignore")

    alerts_display = display[display["Dias Restantes"] <= ALERT_THRESHOLD].copy()

    # ── Write Excel ────────────────────────────────────────────────────────────
    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        alerts_display.to_excel(writer, sheet_name="⚠️ Reposição Urgente", index=False)
        display.to_excel(writer, sheet_name="📦 Todos os Produtos", index=False)
        _style_workbook(writer.book, alerts_display, display)

    return out_path


def _style_workbook(wb, alerts_df: pd.DataFrame, full_df: pd.DataFrame) -> None:
    """Apply HUD-style dark formatting to the workbook."""
    from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    HEADER_BG  = "0D1117"
    URGENTE_BG = "3D1515"
    ATENCAO_BG = "2E2200"
    OK_BG      = "0D1F1A"
    TEXT_COLOR = "E2E8F0"
    ACCENT     = "00D4FF"

    thin = Border(
        left=Side(style="thin", color="1A1A2E"),
        right=Side(style="thin", color="1A1A2E"),
        bottom=Side(style="thin", color="1A1A2E"),
    )

    for ws in wb.worksheets:
        # Header row
        for cell in ws[1]:
            cell.font      = Font(bold=True, color=ACCENT, size=10)
            cell.fill      = PatternFill("solid", fgColor=HEADER_BG)
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border    = thin

        # Data rows
        urgency_col = None
        for idx, cell in enumerate(ws[1], 1):
            if str(cell.value) == "Urgência":
                urgency_col = idx
                break

        for row in ws.iter_rows(min_row=2):
            urgency_val = ""
            if urgency_col:
                urgency_val = str(ws.cell(row=row[0].row, column=urgency_col).value or "")

            if "URGENTE" in urgency_val:
                bg = URGENTE_BG
            elif "ATENÇÃO" in urgency_val:
                bg = ATENCAO_BG
            else:
                bg = OK_BG

            for cell in row:
                cell.fill      = PatternFill("solid", fgColor=bg)
                cell.font      = Font(color=TEXT_COLOR, size=9)
                cell.alignment = Alignment(horizontal="center")
                cell.border    = thin

        # Auto-width columns
        for col in ws.columns:
            max_len = max((len(str(c.value or "")) for c in col), default=8)
            ws.column_dimensions[get_column_letter(col[0].column)].width = min(max_len + 4, 40)

        # Freeze header
        ws.freeze_panes = "A2"


# ── macOS Notification ────────────────────────────────────────────────────────

def notify_macos(alerts_df: pd.DataFrame) -> None:
    """
    Fire a native macOS notification summarizing reorder alerts.
    Silent no-op on Streamlit Cloud or if no alerts.
    """
    if alerts_df.empty:
        return

    is_cloud = bool(
        os.environ.get("STREAMLIT_SHARING_MODE") or
        os.environ.get("IS_STREAMLIT_CLOUD")
    )
    if is_cloud:
        return

    count     = len(alerts_df)
    urgentes  = alerts_df[alerts_df["days_remaining"] <= LEAD_TIME_DAYS]
    n_urgent  = len(urgentes)

    title = (
        f"🔴 {n_urgent} produto(s) URGENTE(S) para repor!"
        if n_urgent > 0
        else f"⚠️ {count} produto(s) precisam de reposição"
    )

    top3 = alerts_df.head(3)["product"].tolist()
    body = ", ".join(top3) + (f" + {count - 3} mais" if count > 3 else "")

    script = (
        f'display notification "{body}" '
        f'with title "{title}" '
        f'subtitle "FulôFiló Analytics — Reposição"'
    )
    try:
        subprocess.run(["osascript", "-e", script], capture_output=True, timeout=5)
    except Exception:
        pass
