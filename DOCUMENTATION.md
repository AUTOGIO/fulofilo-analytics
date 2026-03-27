# FulôFiló Analytics Pro
## Documentação Técnica e Manual do Usuário

**Versão:** 1.0  
**Data:** Março 2026  
**Ambiente:** macOS Apple Silicon (M3/M4) · Local-first · Sem dependências de nuvem

---

## Índice

1. [Visão Geral do Sistema](#1-visão-geral-do-sistema)
2. [Manual do Usuário](#2-manual-do-usuário)
3. [Métricas e Interpretação](#3-métricas-e-interpretação)
4. [Workflows Operacionais](#4-workflows-operacionais)
5. [Troubleshooting](#5-troubleshooting)
6. [Boas Práticas](#6-boas-práticas)

---

# 1. Visão Geral do Sistema

## 1.1 Propósito

FulôFiló Analytics Pro é um sistema de Business Intelligence local desenvolvido exclusivamente para a loja **FulôFiló** — varejo de souvenirs, roupas e acessórios regionais nordestinos. O sistema entrega análises acionáveis: classificação ABC de produtos, análise de margem, controle de estoque e monitoramento de vendas diárias.

O sistema opera **100% offline**, sem dependência de nuvem, respeitando a realidade de operação de um micro-varejo.

> **Estado atual da alimentação de dados:** Os dados de vendas e receita presentes no sistema foram utilizados para estruturar e testar o dashboard. A integração com PDV externo **está em definição** — a empresa está avaliando qual será a fonte oficial de dados para o ciclo operacional contínuo. Até essa decisão, os dados de vendas são registrados manualmente via página **Operações Diárias** e atualizações de estoque são feitas via CSV.

## 1.2 Problemas que Resolve

| Problema Anterior | Solução no Sistema |
|---|---|
| Controle de estoque em planilha manual desatualizada | Parquet atualizado via CSV template + alerta automático de reposição |
| Impossível identificar quais produtos realmente lucram | Matriz de Margem: Volume × Lucratividade por produto |
| Sem visibilidade sobre concentração de receita | Análise ABC com curva de Pareto interativa |
| Registros de venda do dia perdidos ao fechar o app | Persistência imediata em CSV + Parquet na submissão |
| Relatórios Excel gerados manualmente e desatualizados | Geração automática de workbook Excel de 9 abas sob demanda |
| Categorias de produtos inconsistentes | Motor de categorização com 30+ regras + interface de correção manual |
| Ausência de fonte de dados estruturada | Catálogo mestre de 48 SKUs com custos, preços e margens definidos manualmente |

## 1.3 Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                        FONTES DE DADOS                       │
│  daily_sales_TEMPLATE.csv  ·  inventory_TEMPLATE.csv        │
│  cashflow_TEMPLATE.csv  ·  [fonte PDV — a definir]          │
└───────────────────┬─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│                      ETL PIPELINE                            │
│  build_catalog.py  →  ingest_eleve.py  →  categorize.py     │
│  (scripts/refresh_data.sh executa os 3 em sequência)        │
└───────────────────┬─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│                    CAMADA DE DADOS                           │
│  data/parquet/                                               │
│    products.parquet      inventory.parquet                   │
│    daily_sales.parquet   cashflow.parquet                    │
│    revenue_report.parquet  profit_report.parquet             │
│    quantity_report.parquet                                   │
│  data/fulofilo.duckdb  (views sobre os parquets)            │
└───────────────────┬─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│                    DASHBOARD (Streamlit)                      │
│  app.py (KPIs gerais)     01_abc_analysis.py                 │
│  02_margin_matrix.py      03_inventory.py                    │
│  04_daily_ops.py          05_categories.py                   │
│  06_export_excel.py                                          │
└─────────────────────────────────────────────────────────────┘
```

## 1.4 Componentes do Sistema

### ETL Scripts (`etl/`)

| Script | Função | Input | Output |
|---|---|---|---|
| `build_catalog.py` | Constrói o catálogo mestre de 48 SKUs com custos, preços e ABC | `dashboard_data.json` (seed) | `products.parquet`, `product_catalog.csv` |
| `ingest_eleve.py` | ~~Importa export do Eleve Vendas~~ **Legado — utilizado apenas na fase de testes. Não é mais a fonte ativa de dados.** | `dashboard_data.json` | `revenue_report.parquet`, `profit_report.parquet`, `quantity_report.parquet` |
| `categorize_products.py` | Aplica 30+ regras de categorização por palavras-chave | `product_catalog.csv` | `product_catalog_categorized.csv` |

### Banco de Dados (`data/fulofilo.duckdb`)

DuckDB com configuração M3 otimizada. Não armazena dados diretamente — registra **views** que lêem os arquivos Parquet em tempo real. Configurações ativas:

```sql
SET threads = 8;               -- todos os performance cores do M3
SET memory_limit = '8GB';      -- seguro abaixo de 16GB unified memory
SET enable_progress_bar = false;
SET temp_directory = '/tmp/duckdb_fulofilo';
```

Views registradas: `products`, `sales`, `inventory`, `cashflow`.

### Dashboard (`app/`)

Aplicação Streamlit com dark theme, executando em `http://127.0.0.1:8501`. Cache de dados com TTL de 300 segundos na maioria das páginas (60s no estoque).

---

# 2. Manual do Usuário

## 2.1 Setup e Execução

### Primeira execução

```bash
cd /Users/eduardogiovannini/dev/products/FuloFilo

# 1. Criar ambiente virtual e instalar dependências
uv venv && uv sync

# 2. Rodar pipeline ETL inicial
source .venv/bin/activate
python3 etl/build_catalog.py
python3 etl/ingest_eleve.py
python3 etl/categorize_products.py

# 3. Iniciar dashboard
bash scripts/launch_app.sh
```

### Execução do dia a dia

**Opção A — Ícone no Desktop (mais simples):**
Clique duplo em `🌺 FulôFiló Analytics.app` na Área de Trabalho. O app verifica se o Streamlit já está rodando (porta 8501) e abre o browser diretamente.

**Opção B — Terminal:**
```bash
cd /Users/eduardogiovannini/dev/products/FuloFilo
bash scripts/launch_app.sh
```

**Opção C — Arquivo clicável:**
Clique duplo em `FuloFilo.command` na raiz do projeto.

### Verificar se está rodando
```bash
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8501
# Retorna 200 se ativo
```

---

## 2.2 Workflow de Atualização de Dados

> ⚠️ **Nota sobre fonte de dados de vendas:** O script `ingest_eleve.py` e o arquivo `dashboard_data.json` foram utilizados exclusivamente para estruturar o sistema e realizar testes com dados reais. **O Eleve Vendas não é mais a fonte ativa de dados.** A empresa está definindo qual será a integração oficial de PDV. Até essa decisão, todas as vendas são registradas manualmente via página **Operações Diárias**.

### Fontes de dados ativas (situação atual)

| Dado | Origem | Como atualizar |
|---|---|---|
| Vendas diárias | Formulário manual no dashboard | Página Operações Diárias |
| Estoque | `inventory_TEMPLATE.csv` | Editar CSV + regenerar parquet |
| Fluxo de caixa | `cashflow_TEMPLATE.csv` | Editar CSV + regenerar parquet |
| Catálogo / preços / margens | `etl/build_catalog.py` (CATALOG dict) | Editar código + rodar script |
| Categorias | `product_catalog_categorized.csv` | Página Categorias ou editar CSV |

---

### Atualizar estoque (`inventory_TEMPLATE.csv`)

1. Abra o arquivo `data/raw/inventory_TEMPLATE.csv` no Numbers ou Excel
2. Colunas disponíveis:

| Coluna | Tipo | Descrição |
|---|---|---|
| `sku` | texto | SKU do produto (ex: `00007`) — não alterar |
| `product` | texto | Nome do produto — não alterar |
| `category` | texto | Categoria — não alterar |
| `current_stock` | inteiro | **Estoque atual** — atualizar aqui |
| `min_stock` | inteiro | Estoque mínimo aceitável |
| `reorder_qty` | inteiro | Quantidade sugerida para reposição |
| `supplier` | texto | Nome do fornecedor (opcional) |
| `lead_time_days` | inteiro | Prazo de entrega em dias (opcional) |
| `notes` | texto | Observações (opcional) |

3. Atualize **apenas a coluna `current_stock`** para refletir a contagem física
4. Salve o arquivo como CSV (separado por vírgula, UTF-8)

### Executar atualizações por componente

```bash
cd /Users/eduardogiovannini/dev/products/FuloFilo
source .venv/bin/activate

# Reconstruir catálogo (após editar preços/custos/SKUs em build_catalog.py)
python3 etl/build_catalog.py

# Recategorizar produtos (após adicionar novos SKUs)
python3 etl/categorize_products.py

# Atualizar parquet de estoque (após editar inventory_TEMPLATE.csv)
python3 -c "
import polars as pl
pl.read_csv('data/raw/inventory_TEMPLATE.csv').write_parquet('data/parquet/inventory.parquet')
print('✅ inventory.parquet atualizado')
"

# Atualizar parquet de caixa (após editar cashflow_TEMPLATE.csv)
python3 -c "
import polars as pl
pl.read_csv('data/raw/cashflow_TEMPLATE.csv').write_parquet('data/parquet/cashflow.parquet')
print('✅ cashflow.parquet atualizado')
"
```

> **Sobre `refresh_data.sh`:** O script completo ainda inclui a chamada a `ingest_eleve.py`. Ele pode ser executado sem problemas desde que `dashboard_data.json` esteja presente — mas o passo do Eleve será substituído quando a nova fonte de dados for definida.

### Verificar sucesso do pipeline

```bash
# Verificar datas de modificação dos parquets
ls -lh data/parquet/

# Checar log do último refresh
tail -30 logs/refresh.log

# Validar no DuckDB
source .venv/bin/activate
python3 -c "
from app.db import get_conn
conn = get_conn()
print('products:', conn.execute('SELECT COUNT(*) FROM products').fetchone()[0])
print('inventory:', conn.execute('SELECT COUNT(*) FROM inventory').fetchone()[0])
"
```

---

## 2.3 Uso do Dashboard — Página por Página

### 🏠 Dashboard Principal (`/`)

**Propósito:** Visão executiva do negócio — snapshot de toda a operação em uma tela.

**O que mostra:**
- 5 KPI cards no topo: Receita Total, Unidades Vendidas, Lucro Bruto, Margem %, Ticket Médio
- Gráfico de barras: Top 15 produtos por receita, colorido por classe ABC
- Gráfico de pizza: Distribuição de receita por categoria
- Tabela resumo ABC: quantos produtos e quanto de receita cada classe representa

**Quando usar:** Início do dia para entender o estado geral. Antes de reuniões de compra ou reposição.

**Decisões suportadas:** "Quais categorias estão gerando mais receita?", "Qual é minha margem global?"

---

### 📊 Análise ABC (`/abc_analysis`)

**Propósito:** Identificar quais produtos merecem atenção máxima e quais podem ser descontinuados.

**O que mostra:**
- Cards: total de produtos por classe e receita de cada classe
- **Aba Pareto:** Gráfico de barras com linha de % acumulado. A linha vermelha tracejada em 80% marca o corte da Classe A
- **Aba Treemap:** Mapa de calor hierárquico Categoria → Produto, colorido por classe
- **Aba Tabela:** Todos os produtos com classe, receita, quantidade e lucro

**Filtros disponíveis:** Por categoria, por classe ABC, por volume mínimo de vendas (≥5 unidades)

**Quando usar:** Decisão de reposição prioritária, negociação com fornecedores, revisão de portfólio.

**Decisões suportadas:** "Quais 20% dos produtos geram 80% da receita?", "Posso descontinuar este produto?"

---

### 💹 Matriz de Margem (`/margin_matrix`)

**Propósito:** Identificar o posicionamento estratégico de cada produto no binômio volume × lucratividade.

**O que mostra:**
- Scatter plot: eixo X = quantidade vendida, eixo Y = margem %, tamanho da bolha = receita
- Linhas de corte baseadas na **mediana** de cada eixo, dividindo o gráfico em 4 quadrantes
- Top 10 maior margem e bottom 10 menor margem em tabelas laterais

**Quadrantes:**

| Quadrante | Posição | Interpretação |
|---|---|---|
| 🌟 **Stars** | Alto volume + Alta margem | Produtos ideais. Manter estoque sempre cheio |
| 🐄 **Cash Cows** | Alto volume + Margem moderada | Base do negócio. Estável, baixo risco |
| 💎 **Hidden Gems** | Baixo volume + Alta margem | Potencial oculto. Investigar por que não vende mais |
| 🐕 **Dogs** | Baixo volume + Baixa margem | Candidatos à descontinuação ou renegociação de custo |

**Quando usar:** Revisão de portfólio, negociação de preços com fornecedores, decisão de descontinuação.

---

### 📦 Gestão de Estoque (`/inventory`)

**Propósito:** Monitorar níveis de estoque em tempo real e identificar itens que precisam de reposição.

**O que mostra:**
- Banner vermelho de alerta se houver itens críticos
- 4 KPIs: Total SKUs, Crítico, Baixo, OK
- **Aba Níveis:** Gráfico de barras horizontal com cor por status. Filtrável por status
- **Aba Reposição:** Tabela apenas dos itens abaixo do ponto de reposição, com quantidade sugerida
- **Aba Valor em Estoque:** Barras por categoria mostrando `current_stock × unit_cost`

**Níveis de alerta (calculados em `db.py`):**

| Status | Condição |
|---|---|
| 🔴 Crítico | `current_stock ≤ min_stock × 0.5` |
| 🟡 Baixo | `current_stock ≤ min_stock` |
| 🟢 OK | `current_stock > min_stock` |

**Quando usar:** Diariamente antes de abrir a loja. Antes de eventos ou alta temporada.

**Ação direta:** Botão "Exportar lista de reposição (Excel)" gera arquivo para enviar ao fornecedor.

---

### ⚡ Operações Diárias (`/daily_ops`)

**Propósito:** Registro de vendas em tempo real durante o funcionamento da loja + consulta rápida de produto.

**Seções:**

**1. Consulta Rápida de Produto**
- Campo de busca por nome ou SKU
- Retorna: SKU, nome, categoria, custo, preço sugerido, margem

**2. Registro de Vendas**
- Campos: Data, Produto, Quantidade, Preço Unitário, Forma de Pagamento, Observações
- **Ao clicar "Registrar Venda":** o dado é gravado imediatamente em `data/raw/daily_sales_TEMPLATE.csv` e o `daily_sales.parquet` é regenerado
- A página recarrega automaticamente após o registro

**3. Resumo do Dia**
- 3 KPIs do dia atual: quantidade de vendas, receita total, ticket médio
- Gráfico de barras dos últimos 30 dias
- Tabela expansível com todas as vendas registradas

**Quando usar:** Durante o atendimento para consultar preços/margens. Ao fechar o caixa para registrar vendas não capturadas automaticamente.

---

### 🏷️ Gerenciador de Categorias (`/categories`)

**Propósito:** Visualizar e corrigir as categorias dos produtos. Garante consistência nos relatórios.

**O que mostra:**
- 5 KPIs: total SKUs, alta confiança, média confiança, não classificados, categorias únicas
- Alerta expandível para produtos sem categoria — permite atribuição manual inline
- Tabela completa com todos os produtos e suas categorias/subcategorias/nível de confiança
- Gráfico de receita por categoria (lido do DuckDB)

**Níveis de confiança:**

| Nível | Significado |
|---|---|
| `high` | Correspondência exata com regras de palavras-chave |
| `medium` | Correspondência parcial |
| `unmatched` | Não foi possível categorizar automaticamente |
| `manual` | Atribuído manualmente pelo usuário |

**Ações disponíveis:**
- Botão **"Re-executar Auto-Categorização"**: roda `etl/categorize_products.py` e recarrega a página
- Botão **"Exportar CSV categorizado"**: baixa `product_catalog_categorized.csv`
- Formulário de atribuição manual para produtos `unmatched`

**Quando usar:** Após adicionar novos produtos ao catálogo. Quando um produto aparece errado em relatórios.

---

### 📤 Exportar Excel (`/export_excel`)

**Propósito:** Gerar o workbook Excel completo de 9 abas sob demanda.

**Abas geradas:**

| Aba | Conteúdo |
|---|---|
| Dashboard | KPIs, totais por categoria |
| ABC Analysis | Tabela completa com classes, receita, lucro por produto |
| Margin Matrix | Pivot margem × volume |
| Inventory | Status de estoque com ícones de alerta |
| Daily Ops | Vendas diárias registradas |
| Cashflow | Entradas e saídas de caixa |
| Products Catalog | Catálogo completo com custos e preços |
| Product Categories | Produtos com categorias e subcategorias |
| Pivot Cat×Month | Receita cruzada por categoria e mês |

**Como usar:**
1. Marque as abas desejadas (todas selecionadas por padrão)
2. Clique em **"⚡ Gerar Relatório"**
3. Aguarde a barra de progresso completar
4. Clique em **"📥 Baixar Excel"**

O arquivo é salvo também em `excel/FuloFilo_Report_YYYY-MM-DD.xlsx` para histórico. Os últimos 5 relatórios ficam visíveis na seção "Relatórios anteriores".

---

# 3. Métricas e Interpretação

## 3.1 KPIs do Dashboard Principal

### Receita Total

| Campo | Detalhe |
|---|---|
| **Fórmula** | `SUM(revenue)` da view `products` no DuckDB |
| **Fonte** | `products.parquet` ← construído por `etl/build_catalog.py` com dados do período de testes |
| **Significado** | Soma de toda receita bruta gerada por vendas no período carregado |
| **Interpretação** | Representa o faturamento total. Não desconta devoluções nem impostos |
| **Atenção** | Os dados de receita no dashboard refletem o período de teste inicial. Serão substituídos quando a nova fonte de dados for integrada |

---

### Unidades Vendidas (Quantidade)

| Campo | Detalhe |
|---|---|
| **Fórmula** | `SUM(qty_sold)` da view `products` |
| **Fonte** | `products.parquet` ← dados do período de testes |
| **Significado** | Total de unidades vendidas em todos os SKUs no período |
| **Interpretação** | Volume operacional. Alto volume com baixa receita indica produtos de baixo ticket |

---

### Lucro Bruto

| Campo | Detalhe |
|---|---|
| **Fórmula** | `SUM(profit)` da view `products` |
| **Fonte** | `products.parquet` ← campo `profit` dos dados de teste |
| **Significado** | Receita menos custo dos produtos vendidos (CPV) |
| **Interpretação** | Resultado antes de despesas operacionais (aluguel, funcionários, etc.) |

---

### Margem %

| Campo | Detalhe |
|---|---|
| **Fórmula** | `(Lucro Bruto / Receita Total) × 100` |
| **Cálculo por produto** | `(suggested_price - unit_cost) / suggested_price × 100` |
| **Fonte** | `unit_cost` e `suggested_price` definidos em `etl/build_catalog.py` (CATALOG) |
| **Interpretação** | Percentual de cada R$ de venda que vira lucro bruto |
| **Referência** | Margem > 40% = saudável para varejo de souvenirs/moda |

---

### Ticket Médio

| Campo | Detalhe |
|---|---|
| **Fórmula** | `SUM(revenue) / SUM(qty_sold)` |
| **Fonte** | Calculado na query `get_summary_kpis()` em `app/db.py` |
| **Significado** | Valor médio de cada unidade vendida |
| **Interpretação** | Compara com o preço sugerido médio do catálogo para avaliar se há desconto excessivo |

---

## 3.2 Classificação ABC (Análise de Pareto)

| Campo | Detalhe |
|---|---|
| **Algoritmo** | Receita cumulativa ordenada de forma decrescente |
| **Fórmula** | `cum_revenue / total_revenue × 100` → percentual acumulado |
| **Classe A** | Produtos com percentual acumulado ≤ 80% da receita total |
| **Classe B** | Produtos entre 80% e 95% do acumulado |
| **Classe C** | Produtos nos últimos 5% da receita |
| **Fonte** | Calculado em `etl/build_catalog.py` e recalculado em tempo real na página ABC |
| **Leitura correta** | Um produto Classe A não é necessariamente o mais lucrativo — é o que mais contribui para a receita. Sempre cruzar com a Margem % |

**Exemplo de uso:**
> "Cangas e Nécessaires são Classe A. Devo garantir estoque máximo desses itens antes de feriados."

> "Vestido Sereia é Classe C com margem de 47% — é Hidden Gem, não descontinuar."

---

## 3.3 Matriz de Margem — Quadrantes

A matriz divide os produtos usando a **mediana** de quantidade vendida e de margem % como linhas de corte.

### 🌟 Stars — Alto Volume + Alta Margem
- Posição: acima da mediana de volume E acima da mediana de margem
- Ação: prioridade máxima de estoque; nunca deixar faltar; negociar melhores condições com fornecedor
- Exemplo típico: Chaveiros, Imãs (alta rotatividade + custo baixo)

### 🐄 Cash Cows — Alto Volume + Margem Moderada/Baixa
- Posição: acima da mediana de volume, abaixo da mediana de margem
- Ação: base estável do negócio; não descontinuar; tentar reduzir custo para elevar margem
- Exemplo típico: Cangas (volume alto, custo de produção razoável)

### 💎 Hidden Gems — Baixo Volume + Alta Margem
- Posição: abaixo da mediana de volume, acima da mediana de margem
- Ação: investigar por que não vende mais; testar posicionamento, vitrine, promoção pontual
- Exemplo típico: Vestido Sereia (margem ~47%, mas vende pouco)

### 🐕 Dogs — Baixo Volume + Baixa Margem
- Posição: abaixo da mediana em ambos os eixos
- Ação: avaliar descontinuação; renegociar custo com fornecedor; ou liquidar estoque
- Atenção: verificar antes se o produto é complementar a um Star (venda cruzada)

**Como ler o scatter plot:**
- Eixo X (horizontal) = quantidade total vendida no período
- Eixo Y (vertical) = margem % calculada com base no custo cadastrado
- Tamanho da bolha = receita total gerada pelo produto
- Cor = intensidade da margem (verde escuro = alta, vermelho = baixa)

---

## 3.4 Métricas de Estoque

### Alertas de Reposição

| Status | Fórmula | Ação recomendada |
|---|---|---|
| 🔴 Crítico | `current_stock ≤ min_stock × 0.5` | Pedir imediatamente |
| 🟡 Baixo | `current_stock ≤ min_stock` | Pedir nos próximos 2–3 dias |
| 🟢 OK | `current_stock > min_stock` | Monitorar normalmente |

### Valor em Estoque por Categoria

| Campo | Detalhe |
|---|---|
| **Fórmula** | `current_stock × unit_cost` por SKU, agrupado por categoria |
| **Fonte** | `inventory.parquet` ✕ `products.parquet` (join por `sku`) |
| **Uso** | Identificar onde o capital está imobilizado em estoque |

---

# 4. Workflows Operacionais

## 4.1 Abertura Diária (5–10 min)

```
1. Abrir FulôFiló Analytics.app na Área de Trabalho
2. Acessar Dashboard → checar KPIs gerais do período atual
3. Acessar Estoque (03_inventory) → verificar alertas 🔴 e 🟡
4. Se houver itens críticos → exportar lista de reposição e contatar fornecedor
5. Deixar página Operações Diárias aberta para registrar vendas ao longo do dia
```

## 4.2 Registro de Vendas no Dia

```
Durante o expediente:
1. Abrir aba Operações Diárias no browser
2. Para cada venda não capturada pelo Eleve (ex: dinheiro, sem nota):
   a. Preencher: Produto, Quantidade, Preço Unitário, Forma de Pagamento
   b. Clicar "✅ Registrar Venda"
   c. O dado é gravado em daily_sales_TEMPLATE.csv imediatamente
   d. A seção "Resumo do Dia" atualiza automaticamente

Ao final do dia:
   - Verificar "Resumo do Dia" para conferir total de vendas manuais
   - Usar o gráfico de 30 dias para comparar com dias anteriores
```

## 4.3 Atualização Semanal de Dados (10–15 min)

> ⚠️ O passo de exportação do Eleve Vendas foi removido deste workflow. A fonte de dados de PDV está em definição.

```
1. Atualizar current_stock em data/raw/inventory_TEMPLATE.csv com contagem física
2. Regenerar parquet de estoque:
      cd /Users/eduardogiovannini/dev/products/FuloFilo && source .venv/bin/activate
      python3 -c "import polars as pl; pl.read_csv('data/raw/inventory_TEMPLATE.csv').write_parquet('data/parquet/inventory.parquet')"
3. Se houver lançamentos de caixa novos: atualizar cashflow_TEMPLATE.csv e regenerar parquet
4. Abrir dashboard e conferir alertas de estoque
5. Opcionalmente: gerar Excel via página Export Excel para arquivo histórico
```

## 4.4 Decisão de Reposição de Produto

```
Quando considerar repor:
   - Produto com status 🔴 Crítico no Estoque
   - Produto Classe A no ABC → prioridade alta
   - Produto Stars na Matriz de Margem → prioridade máxima

Quantidade a pedir:
   - Usar coluna "reorder_qty" da tabela de Reposição como base
   - Ajustar conforme sazonalidade (férias, datas comemorativas)

Quando NÃO repor:
   - Produto 🐕 Dog na Matriz de Margem
   - Produto Classe C no ABC sem nenhuma venda recente
```

## 4.5 Decisão de Descontinuação de Produto

```
Critérios para descontinuação (produto com TODOS estes fatores):
   - Classe C no ABC (contribui para menos de 5% da receita)
   - Posição Dog na Matriz (volume baixo + margem baixa)
   - Sem vendas nas últimas 4 semanas (verificar daily_sales)
   - Sem justificativa estratégica (ex: não é complementar a produto A)

Processo:
   1. Remover da próxima compra (não repor)
   2. Liquidar estoque atual com desconto se necessário
   3. Remover SKU do CATALOG em etl/build_catalog.py
   4. Executar: python3 etl/build_catalog.py
```

## 4.6 Adição de Novo Produto ao Catálogo

```
1. Abrir etl/build_catalog.py
2. Adicionar entrada no dicionário CATALOG:
   {
     "sku":             "00XXX",          # próximo SKU disponível
     "raw_key":         "nome no eleve",  # EXATAMENTE como aparece no JSON do Eleve
     "full_name":       "Nome Completo",  # nome amigável para o dashboard
     "category":        "Categoria",      # categoria do produto
     "unit_cost":       0.00,             # custo de aquisição em R$
     "suggested_price": 0.00,             # preço de venda sugerido em R$
     "min_stock":       10,               # estoque mínimo
     "reorder_qty":     30,               # quantidade a pedir na reposição
   }
3. Executar: python3 etl/build_catalog.py
4. Acessar Gerenciador de Categorias → verificar se o produto foi categorizado
5. Se aparecer como "unmatched", atribuir categoria manualmente na interface
```

---

# 5. Troubleshooting

## 5.1 Dashboard não abre / porta 8501 sem resposta

**Diagnóstico:**
```bash
pgrep -fl streamlit
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8501
```

**Solução:**
```bash
# Matar processo travado
pkill -f streamlit

# Reiniciar
cd /Users/eduardogiovannini/dev/products/FuloFilo
bash scripts/launch_app.sh
```

---

## 5.2 Dashboard mostra "Execute build_catalog.py" em vez de dados

**Causa:** `data/parquet/products.parquet` não existe ou está vazio.

**Solução:**
```bash
cd /Users/eduardogiovannini/dev/products/FuloFilo
source .venv/bin/activate
python3 etl/build_catalog.py
```

---

## 5.3 `ingest_eleve.py` ou `refresh_data.sh` falha (legado)

**Contexto:** `ingest_eleve.py` foi usado na fase de testes e não é mais executado no workflow operacional normal. Se for invocado manualmente ou via `refresh_data.sh`, pode falhar se `dashboard_data.json` estiver ausente ou desatualizado — isso é esperado e não impacta a operação atual.

**Se precisar reexecutar os dados de teste originais:**
```bash
# Verificar se o arquivo de seed existe
ls -lh data/raw/dashboard_data.json

# Se existir, rodar normalmente
source .venv/bin/activate
python3 etl/ingest_eleve.py
```

**Se não existir e não for necessário:** ignorar — os parquets atuais já contêm os dados de referência.

---

## 5.5 Estoque não atualiza após editar inventory_TEMPLATE.csv

**Causa:** O CSV foi editado mas o parquet não foi regenerado.

**Solução:**
```bash
source .venv/bin/activate
python3 -c "
import polars as pl
pl.read_csv('data/raw/inventory_TEMPLATE.csv').write_parquet('data/parquet/inventory.parquet')
print('OK')
"
# Recarregar a página de Estoque no browser (F5)
```

---

## 5.6 Produto aparece como "Não Classificado" nas categorias

**Causa:** O nome do produto no `raw_key` não corresponde a nenhuma regra do motor de categorização.

**Solução A — Correção via interface:**
1. Abrir página Categorias no dashboard
2. Localizar o produto no alerta "Produtos SEM categorização"
3. Selecionar Categoria e Subcategoria manualmente
4. Clicar "💾 Salvar atribuições manuais"

**Solução B — Correção permanente:**
1. Editar `etl/categorize_products.py` e adicionar uma regra no dicionário `CATEGORY_RULES`
2. Executar `python3 etl/categorize_products.py`

---

## 5.7 Erro DuckDB "unrecognized configuration parameter"

**Causa:** PRAGMA inválido no `app/db.py`.

**Diagnóstico:** Ver mensagem de erro completa no terminal onde o Streamlit foi iniciado.

**Solução:** Em `app/db.py`, remover qualquer `PRAGMA` que não seja um dos 4 válidos:
```python
conn.execute("SET threads = 8")
conn.execute("SET memory_limit = '8GB'")
conn.execute("SET enable_progress_bar = false")
conn.execute("SET temp_directory = '/tmp/duckdb_fulofilo'")
```

---

## 5.8 Dados de vendas diárias desapareceram após reiniciar o app

**Causa:** Versão antiga da página 04_daily_ops.py armazenava dados apenas em `st.session_state`.

**Verificação:**
```bash
wc -l data/raw/daily_sales_TEMPLATE.csv
```

Se retornar apenas `1` (só o cabeçalho), os dados não foram persistidos.

**Solução para dados futuros:** A versão atual da página grava em CSV + regenera Parquet automaticamente. Se havia dados valiosos na sessão anterior, precisam ser reinseridos manualmente.

---

## 5.9 Excel gerado com abas vazias

**Causa:** O parquet correspondente está vazio ou não existe.

**Diagnóstico:**
```bash
python3 -c "
import polars as pl
from pathlib import Path
for f in Path('data/parquet').glob('*.parquet'):
    df = pl.read_parquet(f)
    print(f.name, len(df), 'rows')
"
```

**Solução:** Executar o pipeline completo `bash scripts/refresh_data.sh` e regenerar o Excel.

---

# 6. Boas Práticas

## 6.1 Frequência de Atualização

| Dado | Frequência recomendada |
|---|---|
| `current_stock` no inventory_TEMPLATE.csv | Semanalmente (ou após reposição) |
| Registro de vendas manuais na Daily Ops | Diariamente, ao fechar o caixa |
| `cashflow_TEMPLATE.csv` | Ao registrar entradas/saídas relevantes |
| Geração de relatório Excel | Quinzenalmente ou antes de reuniões de compra |
| Revisão de categorias (Categorias page) | Ao adicionar novos produtos |
| Atualização do CATALOG em `build_catalog.py` | Ao alterar custos, preços ou adicionar SKUs |
| **Integração com nova fonte PDV** | **A definir — quando implementada, substituirá os registros manuais** |

## 6.2 Higiene dos Dados

- **`raw_key` no CATALOG deve ser idêntico ao `item` no JSON do Eleve.** Qualquer diferença de espaço, acento ou capitalização resulta em produto sem dados de venda.
- **Nunca alterar a coluna `sku`** no inventory_TEMPLATE.csv — é a chave de join com o catálogo.
- **Manter `unit_cost` atualizado** em `etl/build_catalog.py` — a margem % é calculada com base nele. Um custo desatualizado gera análises de margem incorretas.
- **Não editar parquets diretamente.** Sempre editar os arquivos CSV/JSON de origem e regenerar os parquets via ETL.

## 6.3 Backup

```bash
# Backup diário dos dados críticos (adicionar ao crontab se desejado)
cp -r /Users/eduardogiovannini/dev/products/FuloFilo/data/raw \
       /Users/eduardogiovannini/dev/products/FuloFilo/data/raw_backup_$(date +%Y%m%d)
```

Os arquivos mais críticos para preservar são:
- `data/raw/dashboard_data.json` — dados de venda do Eleve
- `data/raw/inventory_TEMPLATE.csv` — estoque atual
- `data/raw/daily_sales_TEMPLATE.csv` — vendas manuais registradas
- `data/raw/product_catalog_categorized.csv` — categorias (inclui atribuições manuais)

## 6.4 Precisão do Estoque

- Realizar **contagem física** mensal para reconciliar `current_stock` com a realidade
- Produtos com `min_stock = 0` **não aparecem nos alertas** — definir sempre um valor mínimo
- O campo `reorder_qty` é apenas uma sugestão — ajustar conforme giro real e sazonalidade

## 6.5 Performance

- O cache do Streamlit expira em **5 minutos** (300s) na maioria das páginas. Se os dados foram atualizados e o dashboard ainda mostra dados antigos, aguardar o TTL ou recarregar com **Ctrl+Shift+R** (hard refresh)
- O DuckDB lê os parquets diretamente do disco via views — qualquer parquet atualizado é refletido na próxima query após o TTL expirar

---

*FulôFiló Analytics Pro · Documentação interna · v1.1 · 2026*  
*v1.1 — Eleve Vendas removido como fonte ativa; dados de teste preservados como referência; fonte de PDV a definir.*
