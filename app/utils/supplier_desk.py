from __future__ import annotations

import html
import json
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent.parent
SUPPLIER_DIR = ROOT / "data" / "suppliers"
SUPPLIER_JSON = SUPPLIER_DIR / "suppliers.json"
SUPPLIER_HTML = SUPPLIER_DIR / "suppliers_dashboard.html"

DEFAULT_CONFIG = {
    "browser_title": "FulôFiló — Fornecedores",
    "header_title": "AI Insights + Supplier Desk",
    "header_kicker": "AI / supplier intelligence",
    "header_flow": "supplier artifacts -> opportunity review -> sourcing decisions",
    "nav_code": "AI",
    "nav_label": "AI Insights",
}

FILE_LINKS = {
    "chaveiro_imgs": ("Chaveiros", "FF_imagens_produtos/chaveiros_individuais/"),
    "necessaire_imgs": ("Nécessaires", "FF_imagens_produtos/necessaires_individuais/"),
    "carteira_imgs": ("Carteiras", "FF_imagens_produtos/carteiras_individuais/"),
    "vestuario_imgs": ("Vestuário", "FF_imagens_produtos/vestuario_e_diversos/"),
    "body_imgs": ("Bodys", "FF_imagens_produtos/bodys_individuais/"),
    "mercadorias_imgs": ("Mercadorias", "FF_imagens_produtos/mercadorias/"),
    "keychain_ctrl": ("Controle Chaveiros", "data/raw/keychain_sales_control.xlsx"),
    "female_keychain": ("Chaveiros Femininos", "data/raw/female_keychain_sales_control.xlsx"),
    "master": ("Master Excel", "data/excel/FuloFilo_Master.xlsx"),
    "suppliers_folder": ("Pasta Fornecedores", "data/suppliers/"),
}


def _clean_text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _split_csv(value: Any) -> list[str]:
    if isinstance(value, list):
        raw = value
    else:
        raw = str(value or "").split(",")
    return [str(item).strip() for item in raw if str(item).strip()]


def _phone_digits(value: str) -> str:
    return re.sub(r"\D+", "", value or "")


def next_supplier_id(suppliers: list[dict[str, Any]]) -> int:
    ids = [int(s.get("id", 0) or 0) for s in suppliers]
    return (max(ids) if ids else 0) + 1


def normalize_supplier(supplier: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": int(supplier.get("id") or 0),
        "name": _clean_text(supplier.get("name")).upper(),
        "contact": _clean_text(supplier.get("contact")),
        "phone": _clean_text(supplier.get("phone")),
        "whatsapp": _phone_digits(_clean_text(supplier.get("whatsapp"))),
        "state": _clean_text(supplier.get("state")).upper(),
        "delivery": _clean_text(supplier.get("delivery")),
        "products": _clean_text(supplier.get("products")),
        "categories": _split_csv(supplier.get("categories")),
        "color": _clean_text(supplier.get("color")) or "#546E7A",
        "files": [key for key in _split_csv(supplier.get("files")) if key in FILE_LINKS],
    }


def load_supplier_desk() -> dict[str, Any]:
    if not SUPPLIER_JSON.exists():
        return {"config": DEFAULT_CONFIG.copy(), "suppliers": []}
    data = json.loads(SUPPLIER_JSON.read_text(encoding="utf-8"))
    config = DEFAULT_CONFIG | data.get("config", {})
    suppliers = [normalize_supplier(item) for item in data.get("suppliers", [])]
    suppliers.sort(key=lambda item: int(item.get("id", 0)))
    return {"config": config, "suppliers": suppliers}


def save_supplier_desk(data: dict[str, Any], *, backup: bool = True) -> None:
    SUPPLIER_DIR.mkdir(parents=True, exist_ok=True)
    if backup and SUPPLIER_JSON.exists():
        backup_dir = SUPPLIER_DIR / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy2(SUPPLIER_JSON, backup_dir / f"suppliers_{stamp}.json")

    payload = {
        "config": DEFAULT_CONFIG | data.get("config", {}),
        "suppliers": [normalize_supplier(item) for item in data.get("suppliers", [])],
    }
    SUPPLIER_JSON.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def render_supplier_html(data: dict[str, Any]) -> str:
    config = DEFAULT_CONFIG | data.get("config", {})
    suppliers = [normalize_supplier(item) for item in data.get("suppliers", [])]
    suppliers_json = json.dumps(suppliers, ensure_ascii=False)
    links_json = json.dumps(FILE_LINKS, ensure_ascii=False)
    title = html.escape(config["browser_title"])
    header = html.escape(config["header_title"])
    count = len(suppliers)
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
  background: #030303;
  color: #e7e3d7;
  font-family: "IBM Plex Mono", "SF Mono", Menlo, monospace;
  min-height: 100vh;
}}
header {{
  background: linear-gradient(180deg, #191919 0%, #080808 100%);
  border-bottom: 1px solid rgba(114,114,114,0.48);
  padding: 14px 18px 10px;
}}
.header-top {{ align-items: center; display: flex; gap: 10px; margin-bottom: 10px; }}
h1 {{ color: #e7e3d7; font-size: 1.33rem; letter-spacing: .04em; text-transform: uppercase; }}
.badge {{ background: #c06e00; color: #050505; font-size: 0.97rem; font-weight: 900; padding: 3px 10px; }}
.file-bar {{ display: flex; flex-wrap: wrap; gap: 7px; }}
.flink, .cf, .btn {{
  border: 1px solid rgba(114,114,114,0.48);
  color: #f5a623;
  text-decoration: none;
}}
.flink {{ background: #0a0a0a; display: inline-flex; font-size: 1.01rem; font-weight: 800; padding: 5px 12px; }}
.controls {{ background: #050505; border-bottom: 1px solid rgba(114,114,114,0.48); padding: 12px 18px; }}
.controls input {{
  background: #0c0c0c;
  border: 1px solid rgba(114,114,114,0.48);
  color: #e7e3d7;
  font: inherit;
  outline: none;
  padding: 8px 12px;
  width: min(560px, 100%);
}}
.count {{ color: #9b9588; font-size: 1.01rem; padding: 10px 18px 0; }}
.grid {{ display: grid; gap: 12px; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); padding: 14px 18px 28px; }}
.card {{ background: #080808; border: 1px solid rgba(114,114,114,0.48); display: flex; flex-direction: column; min-height: 250px; }}
.card-header {{ align-items: flex-start; display: flex; gap: 10px; padding: 12px 14px 8px; }}
.avatar {{ align-items: center; color: #fff; display: flex; flex-shrink: 0; font-size: 1.15rem; font-weight: 800; height: 34px; justify-content: center; width: 34px; }}
.card-name {{ color: #f5a623; font-size: 1.13rem; font-weight: 900; line-height: 1.3; text-transform: uppercase; }}
.card-contact {{ color: #e7e3d7; font-size: 1.01rem; margin-top: 3px; }}
.card-body {{ flex: 1; padding: 0 14px 8px; }}
.products {{ border-top: 1px solid rgba(114,114,114,0.30); color: #e7e3d7; font-size: 1.03rem; line-height: 1.5; padding-top: 8px; }}
.products strong {{ color: #4bb7ff; display: block; font-size: 0.93rem; letter-spacing: .04em; margin-bottom: 2px; text-transform: uppercase; }}
.card-files {{ background: #050505; border-top: 1px solid rgba(114,114,114,0.48); display: flex; flex-wrap: wrap; gap: 5px; padding: 8px 14px; }}
.card-files-label {{ color: #9b9588; font-size: 0.91rem; font-weight: 800; letter-spacing: .04em; margin-bottom: 2px; text-transform: uppercase; width: 100%; }}
.cf {{ background: #0a0a0a; display: inline-flex; font-size: 0.97rem; font-weight: 800; padding: 4px 8px; }}
.card-footer {{ border-top: 1px solid rgba(114,114,114,0.48); display: flex; gap: 6px; padding: 8px 14px; }}
.btn {{ align-items: center; display: flex; flex: 1; font-size: 1.01rem; font-weight: 900; justify-content: center; padding: 7px 6px; }}
.btn-call {{ background: #063b7a; color: #fff; }}
.btn-wa {{ background: #13a84a; color: #050505; }}
.btn-na {{ background: #1a1a1a; color: #9b9588; }}
.empty {{ color: #9b9588; grid-column: 1/-1; padding: 54px 20px; text-align: center; }}
</style>
</head>
<body>
<header>
  <div class="header-top">
    <h1>{header}</h1>
    <span class="badge">{count} fornecedores</span>
  </div>
  <div class="file-bar">
    <a class="flink" href="file://{ROOT / 'data' / 'excel' / 'FuloFilo_Master.xlsx'}">Master Excel</a>
    <a class="flink" href="file://{SUPPLIER_DIR / 'SUPPLIERS_DB.xlsx'}">SUPPLIERS_DB.xlsx</a>
    <a class="flink" href="file://{SUPPLIER_DIR / 'ALL_SUPPLIERS_COMPLETE.pdf'}">PDF Completo</a>
    <a class="flink" href="file://{SUPPLIER_DIR}">Pasta Fornecedores</a>
  </div>
</header>
<div class="controls">
  <input type="text" id="search" placeholder="Buscar fornecedor, produto, estado...">
</div>
<div class="count" id="count-label"></div>
<div class="grid" id="grid"></div>
<script>
const ROOT = "file://{ROOT}";
const SUPPLIERS = {suppliers_json};
const FILE_LINKS = {links_json};
let searchTerm = "";

function escapeHtml(value) {{
  return String(value || "").replace(/[&<>"']/g, c => ({{"&":"&amp;","<":"&lt;",">":"&gt;","\\"":"&quot;","'":"&#39;"}}[c]));
}}
function initials(name) {{
  return String(name || "").split(/\\s+/).slice(0, 2).map(word => word[0] || "").join("").toUpperCase();
}}
function renderFileLinks(keys) {{
  const items = (keys || []).map(key => {{
    const item = FILE_LINKS[key];
    if (!item) return "";
    return `<a class="cf" href="${{ROOT}}/${{item[1]}}" title="${{escapeHtml(item[1])}}">${{escapeHtml(item[0])}}</a>`;
  }}).join("");
  return items ? `<div class="card-files"><div class="card-files-label">Arquivos relacionados</div>${{items}}</div>` : "";
}}
function render() {{
  const q = searchTerm.toLowerCase();
  const filtered = SUPPLIERS.filter(s => !q ||
    String(s.name || "").toLowerCase().includes(q) ||
    String(s.products || "").toLowerCase().includes(q) ||
    String(s.contact || "").toLowerCase().includes(q) ||
    String(s.state || "").toLowerCase().includes(q)
  );
  document.getElementById("count-label").textContent =
    filtered.length + " fornecedor" + (filtered.length !== 1 ? "es" : "") + " encontrado" + (filtered.length !== 1 ? "s" : "");
  const grid = document.getElementById("grid");
  if (!filtered.length) {{
    grid.innerHTML = '<div class="empty">Nenhum fornecedor encontrado.</div>';
    return;
  }}
  grid.innerHTML = filtered.map(s => {{
    const phoneNum = String(s.phone || "").replace(/\\D/g, "");
    const waBtn = s.whatsapp
      ? `<a class="btn btn-wa" href="https://wa.me/${{s.whatsapp}}" target="_blank">WhatsApp</a>`
      : `<span class="btn btn-na">N/D</span>`;
    const callBtn = phoneNum
      ? `<a class="btn btn-call" href="tel:+${{phoneNum}}">Ligar</a>`
      : `<span class="btn btn-na">N/D</span>`;
    const contactLine = s.contact ? `<div class="card-contact">${{escapeHtml(s.contact)}}</div>` : "";
    return `<div class="card">
      <div class="card-header">
        <div class="avatar" style="background:${{escapeHtml(s.color || "#546E7A")}}">${{escapeHtml(initials(s.name))}}</div>
        <div><div class="card-name">${{escapeHtml(s.name)}}</div>${{contactLine}}</div>
      </div>
      <div class="card-body"><div class="products"><strong>Produtos</strong>${{escapeHtml(s.products)}}</div></div>
      ${{renderFileLinks(s.files)}}
      <div class="card-footer">${{waBtn}}${{callBtn}}</div>
    </div>`;
  }}).join("");
}}
document.getElementById("search").addEventListener("input", event => {{
  searchTerm = event.target.value;
  render();
}});
render();
</script>
</body>
</html>
"""


def rebuild_supplier_dashboard(data: dict[str, Any] | None = None) -> Path:
    payload = data or load_supplier_desk()
    SUPPLIER_HTML.write_text(render_supplier_html(payload), encoding="utf-8")
    return SUPPLIER_HTML
