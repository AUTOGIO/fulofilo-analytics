# FulôFiló Analytics Pro — Repository Audit & Cleanup

**Date:** 2026-04-22
**Scope:** Conservative cleanup — no code refactor, no history rewrite
**Target repo:** https://github.com/AUTOGIO/fulofilo-analytics

---

## 1. Findings (pre-cleanup)

### Junk tracked on disk (not all in git, but cluttering the tree)
| Item | Size | Action |
|---|---|---|
| `.venv/` | 1.2 GB | Kept on disk (user's local venv), remains gitignored |
| `cf-worker/node_modules/` | 173 MB | **Removed from disk**; reinstall via `npm install` |
| `cf-worker/.wrangler/` | — | **Removed from disk** |
| `.uv-cache/` | 20 KB | **Removed from disk** |
| `.pytest_cache/` | 20 KB | **Removed from disk** |
| `.tmp/` | empty | **Removed from disk** |
| `.DS_Store` (×29) | — | **Deleted everywhere** except inside `.git/`/`.venv/` |
| `__pycache__/` (×9 outside `.venv`) | — | **Deleted everywhere** outside `.venv/` |

### Secrets
| File | Status |
|---|---|
| `.env.cloudflare` | Contains a live `CLOUDFLARE_API_TOKEN`. **Never committed** (verified via `git log --all -S 'cfut_'`). Already gitignored by `.env.*` pattern. |

**Action:** created `.env.cloudflare.example` (redacted, committed). Real file stays local and gitignored.

> ⚠️ The token value was read during the audit. Rotate it in the Cloudflare dashboard if you want full safety.

### Root-level loose files (moved into proper subfolders)
| Before | After |
|---|---|
| `WhatsApp Image 2026-03-26 at 15.09.06.jpeg` | `assets/images/whatsapp_2026-03-26_150906.jpeg` |
| `GMT.png` | `assets/images/GMT.png` |
| `regionais.pdf` | `docs/attachments/regionais.pdf` |
| `daily_sales_conversion.xlsx` | `reports/archive/daily_sales_conversion.xlsx` |
| `FuloFilo_Report_2026-03-27.xlsx` | `reports/archive/FuloFilo_Report_2026-03-27.xlsx` (now gitignored by `FuloFilo_Report_*.xlsx` rule) |
| `sales_automation_bundle.zip` | `reports/archive/sales_automation_bundle.zip` (gitignored) |

### Portuguese folder names with accents / spaces (renamed to ASCII)
| Before | After |
|---|---|
| `FF_Grafica/Apresentação/` | `FF_Grafica/apresentacao/` |
| `FF_Grafica/Suporte Gráfico/` | `FF_Grafica/suporte_grafico/` |
| `FF_Grafica/Manual da Marca/` | `FF_Grafica/manual_da_marca/` |
| `FF_Grafica/Stickers/` | `FF_Grafica/stickers/` |
| `FF_Grafica/Logotipo/` | `FF_Grafica/logotipo/` |
| `FF_Grafica/Fontes/` | `FF_Grafica/fontes/` |
| `FF_Grafica/Fontes/Cangaço/` | `FF_Grafica/fontes/cangaco/` |
| `FF_Grafica/Fontes/Gliker/` | `FF_Grafica/fontes/gliker/` |
| `FF_Grafica/Fontes/Regards/` | `FF_Grafica/fontes/regards/` |
| `FF_Grafica/gabarito-cartão-visita-1.ai` | `FF_Grafica/gabarito_cartao_visita_1.ai` |

Why: case-only and accent-containing paths break on case-sensitive Linux CI and are fragile across tools.
Code references were grepped — none were hardcoded to the old names.

### `.gitignore` gaps closed
Added missing patterns:

- `.uv-cache/`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, `.coverage`, `.tox/`
- `cf-worker/.wrangler/`, top-level `node_modules/`
- `.claude/` (editor scratch), `*~`, `*.orig`
- `FuloFilo_Report_*.xlsx` at repo root (not just `excel/`)
- `reports/*.tmp.xlsx`, `sales_automation_bundle.zip`
- `*.pem`, `*.key`
- `!.env.example`, `!.env.*.example` whitelist so example files are committable
- `build/`, `dist/`, `*.egg-info/`

---

## 2. What was NOT touched (out of scope)

- `.venv/` contents (local runtime, not in git)
- `FF_Dados_Fiscais/Saida copy.xls`, `Saida-2.xls`, `Saida-3.xls` — possible real fiscal data duplicates, needs user review
- No code refactoring (Python, Streamlit, ETL untouched)
- No git history rewrite
- `uv.lock` kept on disk but gitignored per original policy

---

## 3. Recommended next steps (not executed)

1. **Rotate the Cloudflare API token** in the Cloudflare dashboard.
2. **Add CI** (`.github/workflows/ci.yml`) running `pytest` + `ruff check` on push.
3. **Add pre-commit hooks** (`pre-commit-config.yaml`) for `ruff`, `black`, `end-of-file-fixer`, `trailing-whitespace`.
4. **Consolidate docs** — `DOCUMENTATION.md` at root overlaps with `docs/`. Consider moving into `docs/` and keeping README lean.
5. **Review `FF_Dados_Fiscais` duplicates** (`Saida copy.xls`, `Saida-2.xls`, `Saida-3.xls`) — delete stale copies.
6. **Consider switching to `uv.lock` tracked** instead of ignored, for reproducible installs. Current `pyproject.toml` alone doesn't pin exact versions.
7. **Split repo?** `visual_pos/` + `src/fulofilo_ai/` (ML experiment) have a very different release cadence than the dashboard — consider a separate repo if they stabilize.

---

## 4. Execution summary

```
.DS_Store removed:            29 files
__pycache__ removed:           9 dirs (outside .venv)
cf-worker/node_modules:        173 MB freed
Folders renamed (PT→ASCII):    10
Loose root files relocated:    6
.gitignore rules added:        ~20
New files:                     .env.cloudflare.example, docs/AUDIT_REPORT.md
```
