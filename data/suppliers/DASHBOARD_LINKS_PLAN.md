# Dashboard File Links — Implementation Plan
**Date:** 26/04/2026  
**Scope:** `suppliers_dashboard.html` — add clickable file/folder links per supplier card

---

## Architecture

Each supplier card gets a **📁 Files** row with icon-buttons. Links use `file://` protocol — works natively when the HTML is opened from Finder/browser locally on macOS.

Two tiers of links:

- **Card-level** — specific to each supplier (product images, sales control)
- **Header bar** — shared across all suppliers (master Excel, PDF, restock alerts)

---

## Header Bar — Shared Links (always visible)

| Button | Opens | Path |
|--------|-------|------|
| 📊 Master Excel | `FuloFilo_Master.xlsx` — master product + sales database | `data/excel/FuloFilo_Master.xlsx` |
| 📦 Suppliers DB | `SUPPLIERS_DB.xlsx` — this session's supplier workbook | `data/suppliers/SUPPLIERS_DB.xlsx` |
| 📄 Suppliers PDF | `ALL_SUPPLIERS_COMPLETE.pdf` — original PDF source | `data/suppliers/ALL_SUPPLIERS_COMPLETE.pdf` |
| ⚠️ Restock Alerts | `alertas_reposicao.xlsx` — current restock alert report | `data/outputs/alertas_reposicao.xlsx` |
| 📂 Suppliers Folder | Opens `data/suppliers/` in Finder | `data/suppliers/` |

---

## Per-Supplier Card Links

### Chaveiro Suppliers
**Applies to:** BRINDES E SOUVENIRS CEARÁ · CLEBERSON LIMA · JUNIOR CHAVEIRO · TIAGO MANIA

| Button | Opens | Path |
|--------|-------|------|
| 🖼 Product Images | Folder with keychain product photos | `FF_imagens_produtos/chaveiros_individuais/` |
| 📋 Sales Control | Keychain sales control spreadsheet | `data/raw/keychain_sales_control.xlsx` |
| 📋 Female Keychain Sales | Female keychain names sales control | `data/raw/female_keychain_sales_control.xlsx` |
| 📂 Name Catalog | CSV with all keychain name catalog | `data/raw/keychain_names_catalog.csv` |

> BRINDES also gets: 🏛 Fiscal Data → `FF_Dados_Fiscais/` (only supplier with CNPJ + IE on file)

---

### Roupa Suppliers
**Applies to:** ALGODOEIRO ECO FASHION · OFICINA DE ARTE – Ecobags · VANDA COLORIDO · PATRICIA CAMISAS

| Button | Opens | Path |
|--------|-------|------|
| 🖼 Vestuário Images | Regional shirts, dresses, misc | `FF_imagens_produtos/vestuario_e_diversos/` |
| 🖼 Body Images | Baby body product photos | `FF_imagens_produtos/bodys_individuais/` |
| 📊 Master Excel | Full product + sales data | `data/excel/FuloFilo_Master.xlsx` |

> VANDA COLORIDO gets both vestuário + body folders (supplies Body, Vestido, Macaquinho)

---

### Bolsa / Nécessaire Suppliers
**Applies to:** ALAN BOLSAS · DISTRIBUIDOR (Genérico)

| Button | Opens | Path |
|--------|-------|------|
| 🖼 Nécessaire Images | Nécessaire product photos | `FF_imagens_produtos/necessaires_individuais/` |
| 🖼 Carteira Images | Wallet/carteira product photos | `FF_imagens_produtos/carteiras_individuais/` |
| 📊 Master Excel | Full product + sales data | `data/excel/FuloFilo_Master.xlsx` |

---

### Canga Suppliers
**Applies to:** GIRISH INDIANA · ALAN BOLSAS (also)

| Button | Opens | Path |
|--------|-------|------|
| 📊 Master Excel | Full product + sales data | `data/excel/FuloFilo_Master.xlsx` |
| 📂 Suppliers Folder | All supplier source files | `data/suppliers/` |

> No dedicated canga images folder exists yet — placeholder noted.

---

### Caneca Suppliers
**Applies to:** MAURÍCIO FRIZZO · EXCLUSIVART – Sarah Canecas

| Button | Opens | Path |
|--------|-------|------|
| 📊 Master Excel | Full product + sales data | `data/excel/FuloFilo_Master.xlsx` |
| 📂 Suppliers Folder | All supplier source files | `data/suppliers/` |

> No dedicated caneca images folder exists yet — placeholder noted.

---

### Imã Suppliers
**Applies to:** TIAGO MANIA / Chaveiros Mania

| Button | Opens | Path |
|--------|-------|------|
| 📊 Master Excel | Full product + sales data | `data/excel/FuloFilo_Master.xlsx` |
| 🖼 Product Images | Keychain images folder (closest match) | `FF_imagens_produtos/chaveiros_individuais/` |

---

## Missing Folders (gaps to create later)
| Category | Missing | Action |
|----------|---------|--------|
| Cangas | No `FF_imagens_produtos/cangas_individuais/` | Create folder + add images |
| Canecas | No `FF_imagens_produtos/canecas_individuais/` | Create folder + add images |
| Imãs | No `FF_imagens_produtos/imas_individuais/` | Create folder + add images |

---

## Implementation Notes

- All `file://` links use absolute macOS paths (`/Users/giovannini_nuovo/Documents/GitHub/FuloFilo/...`)
- Folder links open in Finder when clicked from a locally-opened HTML file on macOS
- File links open in the system default app (Excel → Numbers/Excel, PDF → Preview, CSV → Numbers/Excel)
- Link buttons styled differently from WhatsApp/Call buttons — use a neutral `📁` style to avoid visual clutter

---

*Plan generated: 26/04/2026*
