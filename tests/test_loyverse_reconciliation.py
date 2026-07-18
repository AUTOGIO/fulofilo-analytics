from __future__ import annotations

from pathlib import Path

import pytest

from app.utils.loyverse_reconciliation import compute_adjustments, find_latest_anchor


def test_compute_adjustments_adds_delta_rows():
    anchor_rows = [
        {"sku": "10014", "item": "Regional adulto", "qty": 10.0, "revenue": 600.0},
        {"sku": "10039", "item": "Bolsa kit 125", "qty": 2.0, "revenue": 250.0},
    ]
    ledger = {
        "10014": {"qty": 9.0, "revenue": 540.0, "product": "Regional adulto"},
        "10039": {"qty": 2.0, "revenue": 250.0, "product": "Bolsa kit 125"},
    }
    catalog = {"10014": "Regional adulto", "10039": "Bolsa kit 125"}

    adjustments = compute_adjustments(anchor_rows, ledger, catalog)

    assert len(adjustments) == 1
    assert adjustments[0]["sku"] == "10014"
    assert adjustments[0]["qty"] == pytest.approx(1.0)
    assert adjustments[0]["revenue"] == pytest.approx(60.0)


def test_find_latest_anchor_prefers_latest_end_date(tmp_path: Path):
    incoming = tmp_path / "incoming"
    incoming.mkdir()
    older = incoming / "item-sales-summary-2026-03-01-2026-05-30.csv"
    newer = incoming / "item-sales-summary-2026-03-01-2026-06-19.csv"
    older.write_text("Item,SKU,Categoria,Itens vendidos,Vendas brutas,Itens reembolsados,Reembolsos,Descontos,Vendas líquidas,Custo das mercadorias,Lucro bruto,Margem,Impostos\n", encoding="utf-8")
    newer.write_text(older.read_text(encoding="utf-8"), encoding="utf-8")

    found = find_latest_anchor(search_roots=[incoming])
    assert found == newer
