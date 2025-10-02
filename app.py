import streamlit as st
import pandas as pd
import sqlite3
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime


# Conexão com o banco
conn = sqlite3.connect("vendas_marketing.db")

st.set_page_config(page_title="Dashboard Vendas & Marketing", layout="wide")
st.title("📊 Dashboard Interativo - Vendas & Marketing")

# Filtros
st.sidebar.header("Filtros")
periodo = st.sidebar.selectbox("Selecione o período", ["Último Trimestre", "Último Semestre", "Ano Completo"])

def get_periodo_sql(periodo):
    if periodo == "Último Trimestre":
        return "date('now', '-3 months')"
    elif periodo == "Último Semestre":
        return "date('now', '-6 months')"
    else:
        return "date('now', '-12 months')"

data_inicio = get_periodo_sql(periodo)
meses_opcoes = {
    "Janeiro": "01", "Fevereiro": "02", "Março": "03", "Abril": "04",
    "Maio": "05", "Junho": "06", "Julho": "07", "Agosto": "08",
    "Setembro": "09", "Outubro": "10", "Novembro": "11", "Dezembro": "12"
}
mes_escolhido = st.sidebar.selectbox("Ou selecione um mês específico", [""] + list(meses_opcoes.keys()))
ano_atual = datetime.now().year

# Campo de busca por cliente
nome_cliente_filtro = st.sidebar.text_input("🔍 Buscar cliente pelo nome")

# Lógica de data
if mes_escolhido:
    mes_num = meses_opcoes[mes_escolhido]
    data_inicio = f"{ano_atual}-{mes_num}-01"
    data_fim = f"date('{data_inicio}', '+1 month', '-1 day')"
    filtro_data_sql = f"data_venda BETWEEN date('{data_inicio}') AND {data_fim}"
else:
    data_inicio = get_periodo_sql(periodo)
    filtro_data_sql = f"data_venda >= {data_inicio}"

# Filtro por cliente
filtro_cliente_sql = f"AND c.nome LIKE '%{nome_cliente_filtro}%'" if nome_cliente_filtro else ""


# Função para gráfico com rótulos
def plot_bar_with_labels(df, x, y, title):
    fig, ax = plt.subplots()
    sns.barplot(data=df, x=x, y=y, ax=ax)
    ax.set_title(title)
    for i in ax.containers:
        ax.bar_label(i, fmt='%.2f', label_type='edge')
    st.pyplot(fig)

# Seção A: Análise de Vendas
st.subheader("🛒 Análise de Vendas")

# Receita por canal
query_canal = f"""
SELECT canal_aquisicao, SUM(valor_total) AS receita
FROM vendas
WHERE data_venda >= '{data_inicio}'
GROUP BY canal_aquisicao;
"""
df_canal = pd.read_sql(query_canal, conn)
st.write("💡 Receita por Canal de Aquisição")
plot_bar_with_labels(df_canal, "canal_aquisicao", "receita", "Receita por Canal")

# Top 5 produtos com margem média
query_produtos = """
SELECT p.nome_produto,
       COUNT(*) AS vendas,
       AVG(v.valor_total - p.custo_unitario) AS margem_media
FROM vendas v
JOIN produtos p ON v.id_produto = p.id_produto
GROUP BY p.nome_produto
ORDER BY vendas DESC
LIMIT 5;
"""
df_produtos = pd.read_sql(query_produtos, conn)
st.write("💡 Top 5 Produtos com Margem Média")
plot_bar_with_labels(df_produtos, "nome_produto", "margem_media", "Margem Média por Produto")

# Segmentação de Clientes 
query_segmento = """
SELECT c.segmento,
       AVG(v.valor_total) AS ticket_medio
FROM vendas v
JOIN clientes c ON v.id_cliente = c.id_cliente  
GROUP BY c.segmento;
"""
df_segmento = pd.read_sql(query_segmento, conn)
st.write("🎯 Ticket Médio por Segmento")
plot_bar_with_labels(df_segmento, "segmento", "ticket_medio", "Ticket Médio por Segmento")

# Segmentação de Clientes
query_ticket_segmento = f"""
SELECT p.nome_produto, c.segmento, AVG(v.valor_total) AS ticket_medio
FROM Vendas v
JOIN Produtos p ON v.id_produto = p.id_produto
JOIN Clientes c ON v.id_cliente = c.id_cliente
WHERE {filtro_data_sql}
{filtro_cliente_sql}
GROUP BY p.nome_produto, c.segmento;
"""

df_ticket_segmento = pd.read_sql(query_ticket_segmento, conn)

st.write("🎯 Ticket Médio por Segmento")
plot_bar_with_labels(df_segmento, "segmento", "ticket_medio", "Ticket Médio por Segmento")

# Sazonalidade
query_sazonalidade = """
SELECT strftime('%Y-%m', data_venda) AS mes, SUM(valor_total) AS receita
FROM vendas
GROUP BY mes
ORDER BY mes;
"""
df_sazonalidade = pd.read_sql(query_sazonalidade, conn)
st.write("📅 Sazonalidade de Vendas")
fig, ax = plt.subplots()
sns.lineplot(data=df_sazonalidade, x="mes", y="receita", marker="o", ax=ax)
ax.set_title("Receita por Mês")
for x, y in zip(df_sazonalidade["mes"], df_sazonalidade["receita"]):
    ax.text(x, y, f'{y:.2f}', ha='center', va='bottom')
st.pyplot(fig)

# Seção B: Análise de Marketing
st.subheader("📣 Análise de Marketing")

# Eficiência das Campanhas
query_campanhas = f"""
SELECT c.nome_campanha,
       COUNT(*) AS conversoes,
       c.custo,
       c.orcamento
FROM Interacoes_Marketing i
JOIN Campanhas_Marketing c ON i.id_campanha = c.id_campanha
WHERE i.tipo_interacao = 'Conversão'
GROUP BY c.nome_campanha, c.custo, c.orcamento;
"""
df_campanhas = pd.read_sql(query_campanhas, conn)
st.write("📈 Eficiência das Campanhas")
st.dataframe(df_campanhas)

# Engajamento por Canal
query_engajamento = f"""
SELECT c.canal_marketing, COUNT(*) AS interacoes
FROM Interacoes_Marketing i
JOIN Campanhas_Marketing c ON i.id_campanha = c.id_campanha
GROUP BY c.canal_marketing;
"""
df_engajamento = pd.read_sql(query_engajamento, conn)
st.write("📬 Engajamento por Canal de Marketing")
plot_bar_with_labels(df_engajamento, "canal_marketing", "interacoes", "Interações por Canal")

# Seção C: Análise Integrada
st.subheader("🔗 Análise Integrada (Vendas + Marketing)")

# Vendas pós campanha
query_relacao = """
SELECT p.nome_produto, COUNT(*) AS vendas_pos_campanha
FROM Vendas v
JOIN Campanhas_Marketing c ON v.id_campanha = c.id_campanha
JOIN Produtos p ON v.id_produto = p.id_produto
WHERE julianday(v.data_venda) - julianday(c.data_inicio) BETWEEN 0 AND 15
GROUP BY p.nome_produto;
"""
df_relacao = pd.read_sql(query_relacao, conn)
st.write("⏱️ Vendas após Início de Campanhas")
st.dataframe(df_relacao)

# Receita por cidade
query_regiao = f"""
SELECT c.cidade,
       COUNT(*) AS vendas,
       SUM(v.valor_total) AS receita
FROM Vendas v
JOIN Clientes c ON v.id_cliente = c.id_cliente
WHERE {filtro_data_sql}
{filtro_cliente_sql}
GROUP BY c.cidade
ORDER BY receita DESC
LIMIT 10;
"""
df_regiao = pd.read_sql(query_regiao, conn)
st.write("🌍 Cidades com Maior Receita")
plot_bar_with_labels(df_regiao, "cidade", "receita", "Receita por Cidade")

# Seção D: Análises Adicionais
st.subheader("🧠 Seção D: Análises Adicionais")

# Clientes Inativos
query_churn = """
SELECT c.segmento,
       COUNT(*) AS clientes_inativos
FROM Clientes c
LEFT JOIN Vendas v ON c.id_cliente = v.id_cliente
WHERE v.data_venda IS NULL OR v.data_venda < date('now', '-6 months')
GROUP BY c.segmento;
"""
df_churn = pd.read_sql(query_churn, conn)
st.write("🚪 Clientes Inativos por Segmento")
plot_bar_with_labels(df_churn, "segmento", "clientes_inativos", "Clientes Inativos")

# Conversões por mês
query_campanhas_mes = """
SELECT strftime('%Y-%m', c.data_inicio) AS mes,
       COUNT(i.id_interacao) AS conversoes
FROM Interacoes_Marketing i
JOIN Campanhas_Marketing c ON i.id_campanha = c.id_campanha
WHERE i.tipo_interacao = 'Conversão'
GROUP BY mes
ORDER BY mes;
"""
df_campanhas_mes = pd.read_sql(query_campanhas_mes, conn)
st.write("📆 Evolução das Conversões por Campanha")
fig, ax = plt.subplots()
sns.lineplot(data=df_campanhas_mes, x="mes", y="conversoes", marker="o", ax=ax)
ax.set_title("Conversões por Mês")
for x, y in zip(df_campanhas_mes["mes"], df_campanhas_mes["conversoes"]):
    ax.text(x, y, f'{y}', ha='center', va='bottom')
st.pyplot(fig)

# Comportamento de Compra
query_comportamento = """
SELECT c.segmento,
       strftime('%w', v.data_venda) AS dia_semana,
       COUNT(*) AS vendas
FROM Vendas v
JOIN Clientes c ON v.id_cliente = c.id_cliente
GROUP BY c.segmento, dia_semana;
"""
df_comportamento = pd.read_sql(query_comportamento, conn)
st.write("🕒 Comportamento de Compra por Dia da Semana")
fig, ax = plt.subplots()
sns.barplot(data=df_comportamento, x="dia_semana", y="vendas", hue="segmento", ax=ax)
ax.set_xlabel("Dia da Semana (0=Domingo)")
ax.set_title("Vendas por Dia e Segmento")
st.pyplot(fig)

# Ticket Médio por Produto e Segmento
query_ticket_segmento = """
SELECT p.nome_produto, c.segmento, AVG(v.valor_total) AS ticket_medio
FROM Vendas v
JOIN Produtos p ON v.id_produto = p.id_produto
JOIN Clientes c ON v.id_cliente = c.id_cliente
GROUP BY p.nome_produto, c.segmento;
"""
df_ticket_segmento = pd.read_sql(query_ticket_segmento, conn)
st.write("💰 Ticket Médio por Produto e Segmento")
df_pivot = df_ticket_segmento.pivot(index="nome_produto", columns="segmento", values="ticket_medio")
st.dataframe(df_pivot)

# Seção E: Interações por Cliente
st.subheader("📋 Interações por Cliente")

# Campo de busca
nome_cliente_filtro = st.text_input("🔍 Buscar cliente pelo nome")

# Consulta detalhada
query_interacoes_cliente = f"""
SELECT 
    c.nome AS nome_cliente,
    COUNT(i.id_interacao) AS total_interacoes
FROM Clientes c
LEFT JOIN Vendas v ON c.id_cliente = v.id_cliente
LEFT JOIN Campanhas_Marketing cm ON v.id_campanha = cm.id_campanha
LEFT JOIN Interacoes_Marketing i ON cm.id_campanha = i.id_campanha
where 1=1
{filtro_cliente_sql}
GROUP BY c.nome
ORDER BY c.nome ASC;
"""

df_interacoes = pd.read_sql(query_interacoes_cliente, conn)

# Aplicar filtro se houver texto
if nome_cliente_filtro:
    df_interacoes = df_interacoes[df_interacoes["nome_cliente"].str.contains(nome_cliente_filtro, case=False, na=False)]

st.write("📊 Clientes e suas Interações")
st.dataframe(df_interacoes)

query_clientes_vendas = """
SELECT 
    c.nome AS nome_cliente,
    COUNT(v.id_venda) AS total_vendas,
    SUM(v.valor_total) AS receita_total
FROM Clientes c
JOIN Vendas v ON c.id_cliente = v.id_cliente
GROUP BY c.nome
ORDER BY receita_total DESC;
"""
df_clientes_vendas = pd.read_sql(query_clientes_vendas, conn)
st.subheader("Clientes por Total de Vendas")
st.dataframe(df_clientes_vendas)

conn.close()
