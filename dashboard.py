import streamlit as st
import pandas as pd
import plotly.express as px

# ── Configuração da página ──────────────────────────────────────────────────
st.set_page_config(page_title="Dashboard de Vendas", page_icon="📊", layout="wide")
st.title("📊 Dashboard de Vendas")

# ── Carregar dados ──────────────────────────────────────────────────────────
df = pd.read_csv("dados_vendas.csv")
df["data"] = pd.to_datetime(df["data"])
df["mes"] = df["data"].dt.to_period("M").astype(str)

# ── Sidebar com filtros ─────────────────────────────────────────────────────
st.sidebar.header("🔎 Filtros")

vendedores = st.sidebar.multiselect(
    "Vendedor",
    options=df["vendedor"].unique(),
    default=df["vendedor"].unique()
)

regioes = st.sidebar.multiselect(
    "Região",
    options=df["regiao"].unique(),
    default=df["regiao"].unique()
)

categorias = st.sidebar.multiselect(
    "Categoria",
    options=df["categoria"].unique(),
    default=df["categoria"].unique()
)

# ── Aplicar filtros ─────────────────────────────────────────────────────────
df_filtrado = df[
    df["vendedor"].isin(vendedores) &
    df["regiao"].isin(regioes) &
    df["categoria"].isin(categorias)
]

# ── KPIs ────────────────────────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("💰 Receita Total", f"R$ {df_filtrado['total'].sum():,.2f}")

with col2:
    st.metric("🛒 Nº de Vendas", f"{len(df_filtrado)}")

with col3:
    ticket = df_filtrado["total"].mean() if len(df_filtrado) > 0 else 0
    st.metric("🎯 Ticket Médio", f"R$ {ticket:,.2f}")

with col4:
    qtd = df_filtrado["quantidade"].sum()
    st.metric("📦 Itens Vendidos", f"{qtd}")

st.divider()

# ── Gráficos ─────────────────────────────────────────────────────────────────
col_a, col_b = st.columns(2)

with col_a:
    st.subheader("📈 Receita por Mês")
    receita_mes = df_filtrado.groupby("mes")["total"].sum().reset_index()
    fig1 = px.line(receita_mes, x="mes", y="total", markers=True,
                   labels={"mes": "Mês", "total": "Receita (R$)"},
                   color_discrete_sequence=["#636EFA"])
    fig1.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig1, use_container_width=True)

with col_b:
    st.subheader("🏆 Receita por Vendedor")
    receita_vendedor = df_filtrado.groupby("vendedor")["total"].sum().reset_index().sort_values("total", ascending=True)
    fig2 = px.bar(receita_vendedor, x="total", y="vendedor", orientation="h",
                  labels={"total": "Receita (R$)", "vendedor": "Vendedor"},
                  color="total", color_continuous_scale="Blues")
    st.plotly_chart(fig2, use_container_width=True)

col_c, col_d = st.columns(2)

with col_c:
    st.subheader("🗂️ Receita por Categoria")
    receita_cat = df_filtrado.groupby("categoria")["total"].sum().reset_index()
    fig3 = px.pie(receita_cat, names="categoria", values="total",
                  color_discrete_sequence=px.colors.sequential.Blues_r)
    st.plotly_chart(fig3, use_container_width=True)

with col_d:
    st.subheader("📍 Receita por Região")
    receita_reg = df_filtrado.groupby("regiao")["total"].sum().reset_index().sort_values("total", ascending=False)
    fig4 = px.bar(receita_reg, x="regiao", y="total",
                  labels={"regiao": "Região", "total": "Receita (R$)"},
                  color="total", color_continuous_scale="Blues")
    st.plotly_chart(fig4, use_container_width=True)

st.divider()

# ── Tabela de dados ──────────────────────────────────────────────────────────
st.subheader("📋 Dados Detalhados")
st.dataframe(
    df_filtrado.sort_values("data", ascending=False).reset_index(drop=True),
    use_container_width=True
)
