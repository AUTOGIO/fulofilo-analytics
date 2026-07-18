"""
FulôFiló — Shared Sidebar with Logo (HUD Edition)
===================================================
Import and call render_sidebar() from every page to get a
consistent logo + navigation across the entire app.
"""

from pathlib import Path
import json
import streamlit as st
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from app.utils.source_health import get_source_health
from app.utils.rede_automation import launch_rede_sales_download
from app.utils.runtime import is_streamlit_cloud, local_automations_available
from app.utils.supplier_desk import DEFAULT_CONFIG, load_supplier_desk

# ── Month filter session-state key ────────────────────────────────────────────
MONTH_FILTER_KEY = "ff_month_filter"

_MONTH_LABELS = {
    "2026-01": "Jan 2026", "2026-02": "Fev 2026", "2026-03": "Mar 2026",
    "2026-04": "Abr 2026", "2026-05": "Mai 2026", "2026-06": "Jun 2026",
    "2026-07": "Jul 2026", "2026-08": "Ago 2026", "2026-09": "Set 2026",
    "2026-10": "Out 2026", "2026-11": "Nov 2026", "2026-12": "Dez 2026",
}


def get_month_filter() -> list[str]:
    """Return the currently selected months (list of 'YYYY-MM').
    Empty list means 'all months'.
    """
    return st.session_state.get(MONTH_FILTER_KEY, [])


def render_month_filter(available_months: list[str]) -> list[str]:
    """Render the month multi-select in the sidebar and return selected months."""
    if not available_months:
        return []

    options_display = [_MONTH_LABELS.get(m, m) for m in available_months]
    raw_map = {_MONTH_LABELS.get(m, m): m for m in available_months}

    selected_display = st.multiselect(
        "🗓 Filtrar por mês",
        options=options_display,
        default=st.session_state.get(MONTH_FILTER_KEY + "_display", []),
        placeholder="Todos os meses",
        key=MONTH_FILTER_KEY + "_widget",
        help="Selecione 1 ou mais meses. Vazio = todos.",
    )

    selected_raw = [raw_map[d] for d in selected_display]
    st.session_state[MONTH_FILTER_KEY] = selected_raw
    st.session_state[MONTH_FILTER_KEY + "_display"] = selected_display
    return selected_raw

ASSETS = Path(__file__).resolve().parent.parent / "assets"
LOGO_FULL   = str(ASSETS / "logo.png")
LOGO_SMALL  = str(ASSETS / "favicon.png")
GMT_LOGO    = ASSETS / "GMT.png"
LOGO_17     = ASSETS / "Logo-17.png"
LOGO_44     = ASSETS / "Logo-44.jpg"

_NAV = [
    ("app.py",                   "EX", "Executive Overview"),
    ("pages/03_inventory.py",     "IN", "Inventory Intelligence"),
    ("pages/04_daily_ops.py",     "DO", "Daily Operations"),
    ("pages/01_abc_analysis.py",  "SA", "Sales Analytics"),
    ("pages/02_margin_matrix.py", "CF", "Cashflow"),
    ("pages/05_categories.py",    "CI", "Category Intelligence"),
    ("pages/08_forecasting.py",   "FC", "Forecasting"),
    ("pages/09_procurement.py",   "PO", "Procurement"),
    ("pages/10_what_if.py",       "SIM", "What-If"),
    ("pages/11_benchmarks.py",    "BM", "Benchmarks"),
    ("pages/12_cohorts.py",       "CH", "Cohorts"),
    ("pages/06_export_excel.py",  "RP", "Reports"),
    ("pages/07_suppliers.py",     "AI", "AI Insights"),
]


def _navigation_items() -> list[tuple[str, str, str]]:
    items = list(_NAV)
    try:
        config = DEFAULT_CONFIG | load_supplier_desk().get("config", {})
        items[-1] = (
            "pages/07_suppliers.py",
            str(config.get("nav_code") or "AI").upper(),
            str(config.get("nav_label") or "AI Insights"),
        )
    except Exception:
        pass
    return items


def inject_logo():
    """
    Pin the FulôFiló logo at the top of the sidebar using st.logo().
    Call this once per page — before any st.sidebar content.
    Works on Streamlit >= 1.35.
    """
    st.logo(
        image=LOGO_FULL,
        icon_image=LOGO_SMALL,
        link="http://127.0.0.1:8501",
        size="large",
    )


def render_page_header(logo_path=None):
    """Render a logo centered at the top of any page's main content area.

    Args:
        logo_path: Path object or str to override the default Logo-17.
                   If None, falls back to LOGO_17.
    """
    target = Path(logo_path) if logo_path else LOGO_17
    if not target.exists():
        return
    _, col_center, _ = st.columns([2, 1, 2])
    with col_center:
        st.image(str(target), width="stretch")
    st.markdown("<div style='margin-bottom:8px;'></div>", unsafe_allow_html=True)


def get_selected_period() -> str:
    """Canonical Excel sync exposes a single current-state dataset."""
    return "ALL"


def _is_streamlit_cloud() -> bool:
    return is_streamlit_cloud()


def _local_automations_available() -> bool:
    return local_automations_available()


def _run_local_automation(action: str, force: bool = False, extra_args: list[str] | None = None) -> tuple[bool, dict, str]:
    import subprocess

    root = Path(__file__).resolve().parent.parent.parent
    if not _local_automations_available():
        return False, {}, "Local automations are disabled on Streamlit Cloud. Use FF Terminal on macOS."

    venv_runner = root / ".venv" / "bin" / "python3"
    runner = venv_runner if venv_runner.exists() else Path(sys.executable)
    cmd = [str(runner), str(root / "scripts" / "automation_cli.py"), action]
    if extra_args:
        cmd.extend(extra_args)
    if force:
        cmd.append("--force")

    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(root))
    payload = {}
    stdout = (result.stdout or "").strip()
    if stdout:
        try:
            json_start = stdout.find("{")
            payload = json.loads(stdout[json_start:]) if json_start >= 0 else {}
        except Exception:
            payload = {}
    return result.returncode == 0, payload, (result.stderr or "").strip()


def _run_shell_script(script: Path, *args: str) -> tuple[bool, str]:
    import subprocess

    root = Path(__file__).resolve().parent.parent.parent
    if not _local_automations_available():
        return False, "Local automations are disabled on Streamlit Cloud. Use FF Terminal on macOS."

    result = subprocess.run(
        ["bash", str(script), *args],
        capture_output=True,
        text=True,
        cwd=str(root),
    )
    log = "\n".join(part for part in [result.stdout or "", result.stderr or ""] if part).strip()
    return result.returncode == 0, log


def render_sidebar(active_page: str = ""):
    """
    Render logo + full HUD-styled navigation sidebar.
    Args:
        active_page: filename of the current page (e.g. 'app.py')
    """
    inject_logo()
    local_automations_disabled = not _local_automations_available()

    # HUD sidebar extra CSS (supplements hud.py global styles)
    st.markdown("""
<style>
[data-testid="stSidebar"] .stPageLink a {
    display: block;
    padding: 5px 9px;
    border-radius: 3px;
    font-size: 1.03rem;
    letter-spacing: 0.06em;
    transition: background 0.12s, border-color 0.12s;
    text-decoration: none !important;
    border: 1px solid transparent;
    text-transform: uppercase;
}
[data-testid="stSidebarNav"] {
    display: none !important;
}
[data-testid="stSidebar"] .stPageLink a:hover {
    background: rgba(55,213,232,0.08) !important;
    border-color: rgba(55,213,232,0.22);
}
.sidebar-section-label {
    font-size: 0.87rem;
    letter-spacing: 0.15em;
    color: #82908C;
    text-transform: uppercase;
    padding: 4px 12px 2px;
    margin-top: 8px;
}
.sidebar-footer {
    font-size: 0.93rem;
    color: #4A5568;
    letter-spacing: 0.06em;
    text-align: center;
    padding: 8px 0 4px;
}
.sidebar-status-dot {
    display: inline-block;
    width: 7px; height: 7px;
    border-radius: 50%;
    background: #35D07F;
    box-shadow: none;
    margin-right: 5px;
    vertical-align: middle;
}
</style>
""", unsafe_allow_html=True)

    with st.sidebar:
        st.markdown('<hr style="border-color:rgba(0,212,255,0.18);margin:4px 0 10px;">', unsafe_allow_html=True)

        # ── Month filter ──────────────────────────────────────────────────────
        st.markdown('<div class="sidebar-section-label">Command Window</div>', unsafe_allow_html=True)
        st.text_input(
            "Search / command palette",
            placeholder="SYNC, SKU, ALERT, REPORT...",
            label_visibility="collapsed",
            key="ff_command_palette",
        )

        st.markdown('<div class="sidebar-section-label">Period Filter</div>', unsafe_allow_html=True)
        st.caption("All synchronized months")
        st.session_state.setdefault(MONTH_FILTER_KEY, [])

        st.markdown('<hr style="border-color:rgba(0,212,255,0.18);margin:8px 0 10px;">', unsafe_allow_html=True)
        st.markdown('<div class="sidebar-section-label">Operational Navigation</div>', unsafe_allow_html=True)

        for page, icon, label in _navigation_items():
            st.page_link(page, label=f"{icon}  {label}")

        st.markdown('<div style="padding:4px 12px 0;">', unsafe_allow_html=True)
        st.caption("AL Alerts")
        st.caption("SH System Health")
        st.markdown('</div>', unsafe_allow_html=True)

        # ── Data contract label ────────────────────────────────────────────────
        st.markdown('<hr style="border-color:rgba(0,212,255,0.18);margin:10px 0 8px;">', unsafe_allow_html=True)
        st.markdown('<div class="sidebar-section-label">Canonical Source</div>', unsafe_allow_html=True)
        st.markdown(
            '<div style="text-align:center;font-size:1rem;color:#00D4FF;'
            'letter-spacing:0.06em;padding:6px 0;opacity:0.9;">'
            'EXCEL MASTER ONLINE<br>'
            '<span style="font-size:0.93rem;color:#82908C;">data/excel/FuloFilo_Master.xlsx</span>'
            '</div>',
            unsafe_allow_html=True,
        )
        status = get_source_health()
        health = status.get("health", {})
        if status.get("errors"):
            st.error("Status: sync com erro")
        elif status.get("ok") and health.get("healthy_production_data", False):
            st.success("Status: pronto para produção")
        elif status.get("ok") and not health.get("healthy_production_data", True):
            st.warning(
                "Status: não pronto para produção. "
                "Carregue dados reais no Excel master antes de confiar nos indicadores."
            )

        st.markdown('<hr style="border-color:rgba(0,212,255,0.18);margin:10px 0 8px;">', unsafe_allow_html=True)
        st.markdown('<div class="sidebar-section-label">Automation Controls</div>', unsafe_allow_html=True)
        if local_automations_disabled:
            st.caption("Automações locais ficam no FF Terminal em macOS. A nuvem exibe os dados já sincronizados.")
        else:
            st.caption("Use a rotina automática após atualizar vendas e dados operacionais na planilha Excel.")
        if st.button("Executar rotina automática", width="stretch", type="primary", disabled=local_automations_disabled):
            with st.spinner("Executando sync, alertas e relatórios..."):
                ok, payload, stderr = _run_local_automation("run-daily-automation")
            if ok:
                details = payload.get("details", {})
                steps = details.get("automation_steps", [])
                st.success(f"Rotina concluída. Etapas executadas: {len(steps)}.")
                st.cache_data.clear()
            else:
                error = payload.get("error") or stderr or "Falha ao executar rotina automática."
                st.error(error)

        if st.button("✔ Validar dados", width="stretch", disabled=local_automations_disabled):
            with st.spinner("Executando validação estrita..."):
                ok, payload, stderr = _run_local_automation("validate-data-integrity")
            if ok:
                st.success("Validação concluída com sucesso.")
            else:
                error = payload.get("error") or stderr or "Falha na validação."
                st.error(error)

        st.markdown('<div class="sidebar-section-label">Rede Downloads</div>', unsafe_allow_html=True)
        st.caption("Baixa relatórios Rede. Local-only; não altera o Excel master nem os dados Loyverse.")
        rede_target_date = st.date_input("Dia Rede", key="rede_download_target_date")
        rede_formats = st.multiselect(
            "Formato",
            options=["csv", "excel", "pdf"],
            default=["csv"],
            key="rede_download_formats",
        )
        st.session_state.setdefault("rede_download_status", "idle")
        st.caption(f"Status: {st.session_state['rede_download_status']}")
        if st.button("Baixar vendas Rede", width="stretch", disabled=local_automations_disabled):
            st.session_state["rede_download_status"] = "running"
            result = launch_rede_sales_download("date", rede_target_date, rede_formats)
            st.session_state["rede_download_status"] = "downloaded" if result.ok else "failed"
            if result.ok:
                st.success(result.message)
            else:
                st.error(result.message)

        st.markdown('<div class="sidebar-section-label">Loyverse Sales</div>', unsafe_allow_html=True)
        st.caption("Baixa vendas Loyverse, importa no Excel master e atualiza dashboard/app. Local-only.")
        loyverse_mode = st.radio(
            "Período Loyverse",
            options=["um dia", "intervalo"],
            index=0,
            horizontal=True,
            key="loyverse_download_mode",
        )
        loyverse_target_date = st.date_input("Dia Loyverse", key="loyverse_download_target_date")
        loyverse_end_date = None
        if loyverse_mode == "intervalo":
            loyverse_end_date = st.date_input("Até", value=loyverse_target_date, key="loyverse_download_end_date")
        loyverse_format = st.radio(
            "Formato Loyverse",
            options=["csv", "xlsx", "pdf"],
            index=0,
            horizontal=True,
            key="loyverse_download_format",
        )
        loyverse_force = st.checkbox("Forçar novo download Loyverse", value=False, key="loyverse_download_force")
        st.session_state.setdefault("loyverse_download_status", "idle")
        st.caption(f"Status: {st.session_state['loyverse_download_status']}")
        if st.button("Baixar + importar Loyverse", width="stretch", disabled=local_automations_disabled):
            st.session_state["loyverse_download_status"] = "running"
            with st.spinner("Baixando Loyverse e atualizando pipeline..."):
                if loyverse_mode == "intervalo":
                    action = "download-loyverse-sales-period"
                    extra_args = [
                        "--from",
                        loyverse_target_date.isoformat(),
                        "--to",
                        (loyverse_end_date or loyverse_target_date).isoformat(),
                        "--format",
                        loyverse_format,
                    ]
                else:
                    action = "download-loyverse-daily-sales"
                    extra_args = ["--date", loyverse_target_date.isoformat(), "--format", loyverse_format]
                ok, payload, stderr = _run_local_automation(
                    action,
                    force=loyverse_force,
                    extra_args=extra_args,
                )
            details = payload.get("details", {})
            st.session_state["loyverse_download_status"] = details.get("status", "failed" if not ok else "validated")
            if ok:
                st.success(details.get("message") or "Download concluído.")
                if details.get("raw_path"):
                    st.caption(f"Raw: {details['raw_path']}")
                if details.get("processed_path"):
                    st.caption(f"Processed: {details['processed_path']}")
                st.cache_data.clear()
            else:
                error = details.get("message") or payload.get("error") or stderr or "Falha no download Loyverse."
                st.error(error)

        st.markdown('<hr style="border-color:rgba(0,212,255,0.18);margin:10px 0 8px;">', unsafe_allow_html=True)
        st.markdown(
            '<div class="sidebar-footer">'
            '<span class="sidebar-status-dot"></span>'
            'FulôFiló AI<br>'
            'iMac M3 · macOS · local-first'
            '</div>',
            unsafe_allow_html=True,
        )

        # ── Sync & Deploy button (local only — no-op on Streamlit Cloud) ─────────
        if not local_automations_disabled:
            st.markdown('<hr style="border-color:rgba(0,212,255,0.10);margin:6px 0;">', unsafe_allow_html=True)
            st.markdown('<div class="sidebar-section-label">Deploy</div>', unsafe_allow_html=True)
            if st.button(
                "Sync & Push",
                width="stretch",
                help="Sincroniza Excel → parquets, valida e faz git push → Streamlit Cloud redeploys",
            ):
                sync_script = Path(__file__).resolve().parent.parent.parent / "scripts" / "sync_and_push.sh"
                try:
                    with st.spinner("Sincronizando e publicando..."):
                        ok, log_output = _run_shell_script(sync_script)
                except Exception as exc:
                    ok = False
                    log_output = f"Falha ao executar sync_and_push.sh: {exc}"

                if ok:
                    st.success("Push realizado. App atualiza em ~60s")
                else:
                    st.error("Falha no Sync & Push. Veja o log abaixo.")

                with st.expander("Log do Sync & Push", expanded=not ok):
                    st.code(log_output or "(sem saída)", language="text")

        # ── GMT branding ───────────────────────────────────────────────────────
        if GMT_LOGO.exists():
            st.markdown(
                '<div class="sidebar-footer" style="margin-top:4px;">'
                'Develop by Giovannini Mare<br>Technology'
                '</div>',
                unsafe_allow_html=True,
            )
            st.image(str(GMT_LOGO), width="stretch")
