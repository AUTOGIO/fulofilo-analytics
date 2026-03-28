"""
sales_ops.py — Daily Sales ↔ Excel "Daily Ops" Sheet Sync
==========================================================
Keeps the Excel workbook's "Daily Ops" sheet in sync with
data/raw/daily_sales_TEMPLATE.csv (the manual sales log).

Public API
----------
sync_csv_to_excel_daily_ops()
    Read the full CSV, aggregate by day, and rewrite the
    "Daily Ops" sheet in the latest FuloFilo_Report_*.xlsx.
    Called automatically after every sale registration.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import openpyxl
from openpyxl.cell.cell import MergedCell
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

ROOT      = Path(__file__).resolve().parent.parent.parent
CSV_PATH  = ROOT / "data" / "raw" / "daily_sales_TEMPLATE.csv"
EXCEL_DIR = ROOT / "excel"

# ── Style constants (match build_report.py HUD palette) ───────────────────────
_C_HEADER   = "FF080C18"   # near-black
_C_CYAN     = "FF00D4FF"   # neon cyan accent
_C_DARK_ROW = "FF0B0F1E"   # dark row
_C_MID_ROW  = "FF10162A"   # slightly lighter
_THIN_SIDE  = Side(style="thin", color="FF1A2340")
_THIN_BORDER = Border(left=_THIN_SIDE, right=_THIN_SIDE,
                      top=_THIN_SIDE,  bottom=_THIN_SIDE)

HEADERS = [
    "Data", "Receita (R$)", "Transações", "Ticket Médio (R$)",
    "Produto Top", "Método Pagto", "Qtd Vendida", "Fonte",
]


def _latest_excel() -> Path | None:
    reports = sorted(EXCEL_DIR.glob("FuloFilo_Report_*.xlsx"), reverse=True)
    return reports[0] if reports else None


def _safe_set(cell, value) -> None:
    if not isinstance(cell, MergedCell):
        cell.value = value


def _style_header(ws, n_cols: int) -> None:
    for c in range(1, n_cols + 1):
        cell = ws.cell(1, c)
        if isinstance(cell, MergedCell):
            continue
        cell.font      = Font(bold=True, color=_C_CYAN, name="Calibri", size=10)
        cell.fill      = PatternFill("solid", fgColor=_C_HEADER)
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border    = _THIN_BORDER


def _style_data(cell, row_idx: int, is_currency: bool = False) -> None:
    bg = _C_DARK_ROW if row_idx % 2 == 0 else _C_MID_ROW
    cell.fill      = PatternFill("solid", fgColor=bg)
    cell.font      = Font(name="Calibri", size=9, color="FFE2E8F0")
    cell.alignment = Alignment(horizontal="right" if is_currency else "center",
                               vertical="center")
    cell.border    = _THIN_BORDER
    if is_currency:
        cell.number_format = 'R$ #,##0.00'


def sync_csv_to_excel_daily_ops() -> str | None:
    """
    Aggregate daily_sales_TEMPLATE.csv by date and write all rows
    into the Excel 'Daily Ops' sheet. Replaces existing data rows.
    Returns path to saved Excel or None on failure.
    """
    xlsx_path = _latest_excel()
    if not xlsx_path:
        return None
    if not CSV_PATH.exists() or CSV_PATH.stat().st_size == 0:
        return None

    try:
        # ── Read & aggregate CSV ───────────────────────────────────────────────
        df = pd.read_csv(CSV_PATH, parse_dates=["Date"])
        df = df.dropna(subset=["Date", "Total"])

        if df.empty:
            return None

        # Daily aggregation
        daily = (
            df.groupby(df["Date"].dt.strftime("%Y-%m-%d"))
            .agg(
                receita      = ("Total",          "sum"),
                transacoes   = ("Total",          "count"),
                ticket_medio = ("Total",          "mean"),
                produto_top  = ("Product",        lambda x: x.value_counts().idxmax()),
                metodo_pagto = ("Payment_Method", lambda x: x.value_counts().idxmax()),
                qtd_vendida  = ("Quantity",       "sum"),
                fonte        = ("Source",         lambda x: x.value_counts().idxmax()),
            )
            .reset_index()
            .rename(columns={"Date": "data"})
            .sort_values("data", ascending=False)   # most recent first
        )

        # ── Open workbook ─────────────────────────────────────────────────────
        wb = openpyxl.load_workbook(xlsx_path)
        if "Daily Ops" not in wb.sheetnames:
            return None
        ws = wb["Daily Ops"]

        # Clear all existing data (keep row 1 for header)
        for row in ws.iter_rows(min_row=1, max_row=ws.max_row):
            for cell in row:
                if not isinstance(cell, MergedCell):
                    cell.value = None

        # ── Write header ──────────────────────────────────────────────────────
        ws.freeze_panes = "A2"
        for ci, h in enumerate(HEADERS, 1):
            _safe_set(ws.cell(1, ci), h)
        _style_header(ws, len(HEADERS))

        # Column widths
        for ci, w in zip(range(1, len(HEADERS) + 1),
                         [14, 14, 12, 16, 28, 16, 12, 12]):
            ws.column_dimensions[
                openpyxl.utils.get_column_letter(ci)
            ].width = w

        # ── Write data rows ───────────────────────────────────────────────────
        CURRENCY_COLS = {2, 4}   # Receita, Ticket Médio

        for ri, row in enumerate(daily.itertuples(index=False), 2):
            vals = [
                row.data,
                round(row.receita, 2),
                int(row.transacoes),
                round(row.ticket_medio, 2),
                str(row.produto_top),
                str(row.metodo_pagto),
                int(row.qtd_vendida),
                str(row.fonte),
            ]
            for ci, val in enumerate(vals, 1):
                cell = ws.cell(ri, ci, val)
                _style_data(cell, ri, is_currency=(ci in CURRENCY_COLS))

        # ── KPI summary row at top (row 1 reserved, so append after data) ─────
        total_receita   = daily["receita"].sum()
        total_transacoes = daily["transacoes"].sum()
        ticker_geral    = total_receita / total_transacoes if total_transacoes else 0

        # Write KPI block into a named range or just a dedicated area
        # (add summary below all data rows)
        summary_row = len(daily) + 3
        ws.cell(summary_row, 1, "TOTAL PERÍODO").font = Font(
            bold=True, color=_C_CYAN, name="Calibri", size=10)
        ws.cell(summary_row, 2, round(total_receita, 2)).number_format = 'R$ #,##0.00'
        ws.cell(summary_row, 3, int(total_transacoes))
        ws.cell(summary_row, 4, round(ticker_geral, 2)).number_format = 'R$ #,##0.00'
        for ci in range(1, 5):
            cell = ws.cell(summary_row, ci)
            cell.fill   = PatternFill("solid", fgColor="FF0B1A30")
            cell.font   = Font(bold=True, color=_C_CYAN, name="Calibri", size=10)
            cell.border = _THIN_BORDER

        wb.save(xlsx_path)
        return str(xlsx_path)

    except Exception as exc:  # noqa: BLE001
        print(f"[sales_ops] sync_csv_to_excel_daily_ops failed: {exc}")
        return None
