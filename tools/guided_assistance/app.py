"""
FulôFiló — Guided Assistance (interactive onboarding)
Runs on http://127.0.0.1:8502 — for non-developer operators.
"""

from __future__ import annotations

import subprocess
import sys
from datetime import date
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.utils.automation_paths import loyverse_data_root, rede_automation_root, repo_root

st.set_page_config(
    page_title="FulôFiló — Assistente Guiado",
    page_icon="🌺",
    layout="centered",
    initial_sidebar_state="collapsed",
)

TOTAL_STEPS = 10

STEP_TITLES = [
    "Bem-vindo",
    "Seu perfil",
    "Dois painéis",
    "Loyverse — preparar Chrome",
    "Loyverse — baixar vendas",
    "Rede — credenciais",
    "Rede — baixar relatório",
    "Entender os números",
    "Navegação no sistema",
    "Dicas finais",
]


def _init_state() -> None:
    st.session_state.setdefault("wizard_step", 0)
    st.session_state.setdefault("answers", {})


def _save_answer(key: str, value: object) -> None:
    st.session_state["answers"][key] = value


def _nav_buttons(show_back: bool = True) -> None:
    step = st.session_state["wizard_step"]
    c1, c2, c3 = st.columns([1, 2, 1])
    with c1:
        if show_back and step > 0:
            if st.button("← Voltar", use_container_width=True):
                st.session_state["wizard_step"] = max(0, step - 1)
                st.rerun()
    with c3:
        if st.button("Continuar →", type="primary", use_container_width=True):
            st.session_state["wizard_step"] = min(TOTAL_STEPS - 1, step + 1)
            st.rerun()


def _progress() -> None:
    step = st.session_state["wizard_step"]
    st.progress((step + 1) / TOTAL_STEPS, text=f"Passo {step + 1} de {TOTAL_STEPS}: {STEP_TITLES[step]}")


def _run_cli(action: str, extra: list[str] | None = None) -> tuple[bool, str]:
    runner = ROOT / ".venv" / "bin" / "python3"
    if not runner.exists():
        return False, "Ambiente Python ainda não instalado. Aguarde a instalação automática terminar."
    cmd = [str(runner), str(ROOT / "scripts" / "automation_cli.py"), action]
    if extra:
        cmd.extend(extra)
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    out = (proc.stdout or proc.stderr or "").strip()[:2000]
    return proc.returncode == 0, out


def step_welcome() -> None:
    st.title("🌺 Assistente FulôFiló")
    st.markdown(
        """
Este assistente **interativo** ensina, passo a passo:

1. Como baixar relatórios **Loyverse** (vendas no PDV) e importar no sistema  
2. Como baixar relatórios **Rede** (maquininha)  
3. Como ler os **indicadores** nos painéis  
4. Onde clicar em cada **tela**

**Não precisa ser programador.** Siga as perguntas e use os botões.

Os dois painéis já devem estar abertos:
- **Dashboard web** → [http://127.0.0.1:8501](http://127.0.0.1:8501)
- **FF Terminal (Mac)** → janela nativa escura (se instalou o Xcode)
"""
    )
    if st.checkbox("Li e quero começar o tour", value=False):
        _save_answer("welcome_ack", True)
    _nav_buttons(show_back=False)


def step_profile() -> None:
    st.subheader("Conhecer seu dia a dia")
    used_loyverse = st.radio(
        "Você já exportou relatório de vendas do **Loyverse** (PDV)?",
        ["Nunca", "Já uma vez", "Todo dia"],
        index=0,
        key="q_loyverse_exp",
    )
    used_rede = st.radio(
        "Você baixa relatório de vendas no portal **Rede** (maquininha)?",
        ["Nunca", "Às vezes", "Regularmente"],
        index=0,
        key="q_rede_exp",
    )
    role = st.selectbox(
        "O que você mais quer fazer aqui?",
        [
            "Ver vendas e margem no painel",
            "Baixar relatórios automaticamente",
            "Controlar estoque e reposição",
            "Tudo acima",
        ],
        key="q_role",
    )
    _save_answer("loyverse_exp", used_loyverse)
    _save_answer("rede_exp", used_rede)
    _save_answer("role", role)

    if used_loyverse == "Nunca":
        st.info("Sem problema — vamos ensinar Loyverse nos próximos passos.")
    if used_rede == "Nunca":
        st.caption("Rede é opcional se você só usa Loyverse; ainda assim recomendamos ter o CSV da maquininha.")
    _nav_buttons()


def step_two_dashboards() -> None:
    st.subheader("Dois painéis, um objetivo")
    st.markdown(
        """
| Painel | Onde abre | Para quê |
|--------|-----------|----------|
| **Dashboard web (Streamlit)** | Navegador — porta 8501 | Operar no dia a dia: vendas, estoque, alertas, botões Loyverse/Rede |
| **FF Terminal (macOS)** | App nativa Swift | Visão executiva estilo terminal: KPIs, gráficos densos |

**Fonte da verdade:** planilha Excel `FuloFilo_Master.xlsx` dentro do projeto.  
Depois de importar Loyverse, os números aparecem nos dois painéis após sincronizar.
"""
    )
    quiz = st.radio(
        "Onde você clica para **baixar vendas Loyverse** no dashboard web?",
        [
            "Barra lateral → Loyverse Sales",
            "Página de Cashflow apenas",
            "Não existe botão",
        ],
        key="quiz_nav_loyverse",
    )
    if quiz and quiz != "Barra lateral → Loyverse Sales":
        st.warning("Resposta: barra lateral esquerda, seção **Loyverse Sales**.")
    else:
        st.success("Correto!")
    col1, col2 = st.columns(2)
    with col1:
        if st.link_button("Abrir dashboard web", "http://127.0.0.1:8501"):
            pass
    _nav_buttons()


def step_loyverse_chrome() -> None:
    st.subheader("Loyverse — abrir Chrome correto")
    profile = loyverse_data_root() / "chrome-profile"
    st.markdown(
        f"""
O Loyverse precisa de um **Chrome dedicado** (perfil separado do seu Chrome normal).

**Pasta do perfil:** `{profile}`

### O que fazer agora
1. Feche outras janelas Chrome que usem o mesmo perfil de automação.  
2. O instalador pode abrir o Chrome por você — botão abaixo.  
3. Na janela que abrir, **entre na Loyverse** e deixe logado.  
4. **Não feche** essa janela enquanto baixa relatórios.
"""
    )
    chrome_cmd = (
        '/Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome '
        f'--remote-debugging-port=9222 --user-data-dir="{profile}"'
    )
    st.code(chrome_cmd, language="bash")
    if st.button("Abrir Chrome Loyverse automaticamente", type="primary"):
        try:
            subprocess.Popen(
                [
                    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                    "--remote-debugging-port=9222",
                    f"--user-data-dir={profile}",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            st.success("Chrome iniciado. Faça login na Loyverse nesta janela.")
        except FileNotFoundError:
            st.error("Google Chrome não encontrado. Instale Chrome e clique de novo.")
    _nav_buttons()


def step_loyverse_download() -> None:
    st.subheader("Loyverse — baixar um dia de vendas")
    target = st.date_input("Qual dia deseja baixar?", value=date.today(), key="guide_loyverse_date")
    st.markdown(
        """
Isso vai:
1. Baixar o relatório de itens vendidos na Loyverse  
2. Importar na planilha Excel master  
3. Atualizar o dashboard  

**Requisito:** Chrome do passo anterior aberto e logado na Loyverse.
"""
    )
    if st.button("Baixar e importar este dia (automático)", type="primary"):
        with st.spinner("Baixando... pode levar até 2 minutos."):
            ok, out = _run_cli(
                "download-loyverse-daily-sales",
                ["--date", target.isoformat(), "--format", "csv"],
            )
        if ok:
            st.success("Concluído! Abra o dashboard e confira Executive Overview.")
            st.balloons()
        else:
            st.error("Não foi possível concluir. Mensagem:")
            st.code(out or "sem detalhe")
            st.markdown(
                """
**Causas comuns**
- Chrome não está na porta 9222 → volte ao passo anterior  
- Sessão Loyverse expirou → faça login de novo no Chrome dedicado  
- Dia sem vendas → escolha outro dia  
"""
            )
    _nav_buttons()


def step_rede_keychain() -> None:
    st.subheader("Rede — senha guardada no Mac (uma vez)")
    st.markdown(
        """
A automação Rede usa o **Chaveiro do macOS**, não arquivo de senha no projeto.

Peça a alguém de confiança (ou suporte) para rodar **uma vez** no Terminal:

```bash
security add-generic-password -a "rede-email" -s "rede-automation-email" -w "SEU_EMAIL" -U
security add-generic-password -a "rede-password" -s "rede-automation-password" -w "SUA_SENHA" -U
```

Depois disso, o botão abaixo abre o navegador Rede sozinho. Se aparecer **CAPTCHA ou SMS**, complete na janela e pressione Enter no Terminal.
"""
    )
    has_creds = st.radio("As credenciais Rede já foram configuradas no Chaveiro?", ["Ainda não", "Sim, já configurei"], key="rede_creds")
    _save_answer("rede_creds", has_creds)
    if has_creds == "Ainda não":
        st.warning("Configure o Chaveiro antes de baixar. Você pode pular Rede e voltar depois.")
    _nav_buttons()


def step_rede_download() -> None:
    st.subheader("Rede — baixar relatório de vendas")
    target = st.date_input("Dia do relatório Rede", value=date.today(), key="guide_rede_date")
    fmt = st.multiselect("Formato", ["csv", "excel", "pdf"], default=["csv"])
    st.caption(f"Arquivos vão para: `~/Downloads/Rede` · Projeto: `{rede_automation_root()}`")

    if st.button("Iniciar download Rede (abre Terminal)", type="primary"):
        from app.utils.rede_automation import launch_rede_sales_download

        result = launch_rede_sales_download("date", target, fmt or ["csv"])
        if result.ok:
            st.success(result.message)
        else:
            st.error(result.message)
    st.markdown("**Importante:** Rede **não** entra direto no Excel — use o CSV para conferência ou processos manuais.")
    _nav_buttons()


def step_metrics() -> None:
    st.subheader("Entender os números (quiz rápido)")
    metrics = {
        "Receita": "Total vendido no período (DailySales).",
        "Margem": "Lucro bruto vs receita — depende do custo no catálogo.",
        "Ticket médio": "Receita ÷ número de transações/dias.",
        "Estoque baixo": "SKUs abaixo do ponto de reposição.",
        "Sell-through": "Quanto do estoque virou venda no período.",
    }
    for name, desc in metrics.items():
        with st.expander(name, expanded=False):
            st.write(desc)

    q = st.selectbox(
        "Qual indicador usa **custo do produto no catálogo**?",
        ["Receita", "Margem", "Ticket médio", "Sell-through"],
        key="quiz_margin",
    )
    if q == "Margem":
        st.success("Certo — margem precisa de custo cadastrado no Excel (aba Catalog).")
    elif q:
        st.info("A resposta correta é **Margem**.")
    _nav_buttons()


def step_navigation() -> None:
    st.subheader("Onde clicar no dashboard web")
    st.markdown(
        """
| Página | Use quando |
|--------|------------|
| Executive Overview | Ver KPIs e tendência do negócio |
| Daily Operations | Lançar ou revisar vendas do dia |
| Inventory Intelligence | Reposição e alertas de estoque |
| Sales Analytics | Curva ABC e performance |
| Reports | Exportar Excel/PDF de relatórios |
"""
    )
    q2 = st.radio(
        "Para **alertas de reposição**, qual página?",
        ["Inventory Intelligence", "Cashflow", "Category Intelligence"],
        key="quiz_inv",
    )
    if q2 == "Inventory Intelligence":
        st.success("Correto!")
    _nav_buttons()


def step_tips() -> None:
    st.subheader("Dicas que evitam dor de cabeça")
    tips = [
        "Um arquivo Loyverse por **dia de calendário** — não use export cumulativo de vários meses como se fosse um dia.",
        "Depois de editar o Excel, rode **Executar rotina automática** na barra lateral.",
        "Domingo costuma não ter Loyverse na loja — backfill ignora domingo automaticamente (dias úteis Seg–Sáb).",
        "Se os KPIs parecerem zerados, use **Validar dados** na barra lateral.",
        "Guia completo de erros: `docs/AUTOMATIONS_USER_GUIDE.md` no projeto.",
    ]
    for i, tip in enumerate(tips, 1):
        st.markdown(f"{i}. {tip}")

    if st.session_state.get("tour_complete"):
        st.balloons()
        st.success("Tour concluído! Use o dashboard no dia a dia. Reabra este assistente em http://127.0.0.1:8502")
        st.link_button("Ir para o dashboard", "http://127.0.0.1:8501", use_container_width=True)
    elif st.button("Concluir tour 🎉", type="primary"):
        st.session_state["tour_complete"] = True
        st.rerun()

    if not st.session_state.get("tour_complete"):
        _nav_buttons()


def main() -> None:
    _init_state()
    st.markdown(
        "<style>[data-testid='stSidebar']{display:none;}</style>",
        unsafe_allow_html=True,
    )
    _progress()
    step = st.session_state["wizard_step"]
    steps = [
        step_welcome,
        step_profile,
        step_two_dashboards,
        step_loyverse_chrome,
        step_loyverse_download,
        step_rede_keychain,
        step_rede_download,
        step_metrics,
        step_navigation,
        step_tips,
    ]
    steps[step]()
    with st.sidebar:
        st.caption("Atalho")
        jump = st.selectbox("Ir para passo", range(TOTAL_STEPS), format_func=lambda i: STEP_TITLES[i], index=step)
        if jump != step:
            st.session_state["wizard_step"] = jump
            st.rerun()
        st.caption(f"Repo: {repo_root()}")


main()
