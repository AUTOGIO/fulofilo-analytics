# 🌺 FulôFiló Analytics Pro

Um sistema completo de inteligência de negócios e gestão de estoque para a loja FulôFiló, projetado especificamente para rodar localmente com máxima performance no **iMac M3**.

O sistema substitui planilhas frágeis por uma stack moderna de dados: **DuckDB** (motor analítico), **Polars** (processamento de dados) e **Streamlit** (dashboard interativo).

---

## 🚀 Como Começar (Setup no iMac M3)

### 1. Instalar o gerenciador de pacotes `uv`
O `uv` é um gerenciador de pacotes Python ultrarrápido escrito em Rust.
Abra o Terminal (iTerm2) e rode:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Instalar as dependências do projeto
Na pasta raiz do projeto (`FuloFilo_Analytics_Pro`), rode:
```bash
uv sync
```

### 3. Preparar os Dados Iniciais
O sistema precisa processar os dados brutos para criar o banco de dados DuckDB.
```bash
# 1. Constrói o Catálogo Mestre e cruza com as vendas (gera products.parquet)
uv run python etl/build_catalog.py

# 2. Converte os dados brutos em Parquet e gera templates de estoque/cashflow
uv run python etl/ingest_eleve.py
```

### 4. Iniciar o Dashboard
```bash
uv run streamlit run app/app.py
```
O painel abrirá automaticamente no seu navegador em `http://localhost:8501`.

---

## 📂 Estrutura do Projeto

```text
FuloFilo_Analytics_Pro/
├── app/                    # Dashboard Streamlit
│   ├── app.py              # Página inicial (Visão Geral)
│   ├── db.py               # Motor DuckDB (consultas SQL)
│   └── pages/              # Páginas secundárias
│       ├── 01_abc_analysis.py
│       ├── 02_margin_matrix.py
│       ├── 03_inventory.py
│       └── 04_daily_ops.py
├── data/                   # Armazenamento local (NÃO VAI PARA O GITHUB)
│   ├── raw/                # CSVs exportados do Eleve Vendas
│   ├── parquet/            # Dados processados (alta performance)
│   └── fulofilo.duckdb     # Banco de dados local
├── etl/                    # Scripts de Extração, Transformação e Carga
│   ├── ingest_eleve.py     # Lê CSVs e converte para Parquet
│   └── build_catalog.py    # Limpa nomes e cria o Catálogo Mestre
├── visual_pos/             # Sistema de Reconhecimento Visual (YOLOv11)
│   └── README_VISUAL_POS.md
├── pyproject.toml          # Dependências do projeto
└── README.md               # Este arquivo
```

---

## 🔄 Fluxo de Trabalho Diário / Semanal

Para manter o painel atualizado com novos dados de vendas:

1. Exporte os relatórios do **Eleve Vendas** em formato CSV.
2. Salve os arquivos na pasta `data/raw/` (substituindo os templates).
3. Atualize a contagem de estoque no arquivo `data/raw/inventory_TEMPLATE.csv`.
4. Rode o pipeline de atualização:
   ```bash
   uv run python etl/build_catalog.py
   uv run python etl/ingest_eleve.py
   ```
5. Abra o painel (`uv run streamlit run app/app.py`) para ver os dados atualizados.

---

## 🤖 Prompts Úteis para Manutenção (Cursor / ChatGPT)

Se você precisar modificar o código no futuro, copie e cole estes prompts no Cursor ou ChatGPT:

**Para adicionar uma nova página no Streamlit:**
> "Crie uma nova página Streamlit em `app/pages/05_cashflow.py` que leia a view `cashflow` do DuckDB (`app/db.py`) e mostre um gráfico de barras de Entradas vs Saídas por mês. Siga o mesmo padrão visual e de cores das outras páginas."

**Para adicionar um novo produto ao catálogo:**
> "Abra o arquivo `etl/build_catalog.py`. Preciso adicionar um novo produto chamado 'Bolsa de Praia Grande', SKU '00160', custo R$ 35, preço sugerido R$ 80, categoria 'Bolsas'. Adicione-o à lista `CATALOG` e me diga como rodar o script para atualizar o banco."
