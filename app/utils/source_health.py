from __future__ import annotations

import json
from pathlib import Path

import polars as pl
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
STATUS_PATH = ROOT / "data" / "excel" / "source_sync_status.json"
PRODUCTS_PATH = ROOT / "data" / "parquet" / "products.parquet"
INVENTORY_PATH = ROOT / "data" / "parquet" / "inventory.parquet"
SALES_PATH = ROOT / "data" / "parquet" / "daily_sales.parquet"
CASHFLOW_PATH = ROOT / "data" / "parquet" / "cashflow.parquet"


def get_source_health() -> dict:
    status = {"ok": False, "warnings": [], "errors": [], "health": {}}
    if STATUS_PATH.exists():
        try:
            status = json.loads(STATUS_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            status = {"ok": False, "warnings": [], "errors": ["source_sync_status.json is invalid JSON."], "health": {}}

    health = dict(status.get("health", {}))
    if not health:
        health = {
            "catalog_rows": 0,
            "catalog_real_rows": 0,
            "inventory_rows": 0,
            "inventory_placeholder_only": False,
            "daily_sales_rows": 0,
            "cashflow_rows": 0,
            "category_override_rows": 0,
            "category_overrides_empty": True,
            "placeholder_only": False,
            "meta_present_keys": [],
            "meta_missing_keys": [],
            "healthy_production_data": False,
            "readiness_state": "incomplete",
        }
        if PRODUCTS_PATH.exists():
            products = pl.read_parquet(PRODUCTS_PATH)
            health["catalog_rows"] = products.height
            health["placeholder_only"] = (
                products.height == 1 and products["full_name"].to_list() == ["Produto Exemplo"]
            )
            health["catalog_real_rows"] = 0 if health["placeholder_only"] else products.height
        if INVENTORY_PATH.exists():
            inventory = pl.read_parquet(INVENTORY_PATH)
            health["inventory_rows"] = inventory.height
            health["inventory_placeholder_only"] = (
                inventory.height == 1 and inventory["product"].to_list() == ["Produto Exemplo"]
            )
        if SALES_PATH.exists():
            health["daily_sales_rows"] = pl.read_parquet(SALES_PATH).height
        if CASHFLOW_PATH.exists():
            health["cashflow_rows"] = pl.read_parquet(CASHFLOW_PATH).height
        health["healthy_production_data"] = bool(
            health["catalog_real_rows"] >= 5
            and health["inventory_rows"] > 0
            and not health["inventory_placeholder_only"]
            and health["daily_sales_rows"] > 0
            and health["cashflow_rows"] > 0
            and not health["placeholder_only"]
        )
        health["readiness_state"] = "ready" if health["healthy_production_data"] else ("bootstrap" if health["placeholder_only"] else "incomplete")
        status["health"] = health
    return status


def render_source_health_warning() -> None:
    status = get_source_health()
    health = status.get("health", {})
    warnings = status.get("warnings", [])

    if status.get("errors"):
        st.error(
            "Status: não pronto para produção. A sincronização canônica reportou erros. Revise "
            "`data/excel/source_sync_status.json` antes de confiar nos indicadores."
        )
        return

    if status.get("ok") and health.get("healthy_production_data", False):
        return

    if status.get("ok") and not health.get("healthy_production_data", True):
        messages = []
        if health.get("placeholder_only"):
            messages.append("catálogo ainda em modo bootstrap/demo")
        elif int(health.get("catalog_real_rows", 0)) < 5:
            messages.append(f"catálogo com poucos SKUs reais ({int(health.get('catalog_real_rows', 0))})")
        if int(health.get("inventory_rows", 0)) == 0:
            messages.append("estoque vazio")
        elif health.get("inventory_placeholder_only"):
            messages.append("estoque ainda em modo placeholder")
        if int(health.get("daily_sales_rows", 0)) == 0:
            messages.append("sem histórico de vendas")
        if int(health.get("cashflow_rows", 0)) == 0:
            messages.append("sem histórico de caixa")
        if health.get("meta_missing_keys"):
            messages.append("Meta incompleta")

        detail = "; ".join(messages[:4]) if messages else "os dados sincronizados ainda não representam operação real"
        st.warning(
            "Status: não pronto para produção. "
            f"{detail}. Consulte `data/excel/FuloFilo_Master.xlsx`, rode `bash scripts/sync_excel.sh` "
            "e revise `data/excel/source_sync_status.json`."
        )
    elif warnings:
        st.info("Avisos da última sincronização: " + " | ".join(str(w) for w in warnings))
