"""
Dashboard ECM - Produtos de Conexão
------------------------------------
Análise de gap de membros por EJ, com deduplicação correta
(uma EJ que participou de vários produtos/eventos não tem o gap
contado mais de uma vez).

Para rodar:
    streamlit run app.py
"""

import pandas as pd
import plotly.express as px
import streamlit as st

# --------------------------------------------------------------------------
# Configuração da página
# --------------------------------------------------------------------------
st.set_page_config(
    page_title="ECM - Produtos de Conexão",
    page_icon="📊",
    layout="wide",
)

SHEET_NAME = "Produtos de Conexão"

NUMERIC_COLS = [
    "NPS",
    "PARTICIPANTES",
    "CLUSTER",
    "ECM META",
    "ECM ATUAL",
    "MEMBROS TOTAL",
    "MEMBROS ECM",
    "GAP MEMBROS",
]


# --------------------------------------------------------------------------
# Carregamento e limpeza dos dados
# --------------------------------------------------------------------------
def _to_numeric_br(series: pd.Series) -> pd.Series:
    """
    Converte para número aceitando tanto '0.75' (ponto) quanto '0,75'
    (vírgula, formato BR — comum quando a base vem de CSV exportado do
    Sheets/Excel em pt-BR). Valores inválidos (ex.: '#REF!') viram NaN.
    """
    if series.dtype != object and not pd.api.types.is_string_dtype(series):
        return pd.to_numeric(series, errors="coerce")
    cleaned = series.astype(str).str.strip().str.replace(",", ".", regex=False)
    return pd.to_numeric(cleaned, errors="coerce")


@st.cache_data
def load_data(file) -> pd.DataFrame:
    # Aceita tanto .xlsx (com a aba "Produtos de Conexão") quanto .csv
    # já exportado dessa mesma aba.
    name = getattr(file, "name", str(file))
    if name.lower().endswith(".csv"):
        df = pd.read_csv(file)
    else:
        df = pd.read_excel(file, sheet_name=SHEET_NAME)

    # Remove linhas totalmente vazias (sem EJ) que às vezes sobram na planilha
    df = df.dropna(subset=["EJ"]).copy()

    # Corrige colunas numéricas que vieram como texto (ex.: erros de fórmula
    # como "#REF!" viram NaN, e "0,75" com vírgula vira 0.75)
    for col in NUMERIC_COLS:
        if col in df.columns:
            df[col] = _to_numeric_br(df[col])

    # Padroniza texto (remove espaços extras que causam "EJs duplicadas"
    # por grafias diferentes)
    for col in ["EJ", "FEDERACAO", "PRODUTO_DE_CONEXAO"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    return df


def dedup_por_ej(df: pd.DataFrame) -> pd.DataFrame:
    """
    Retorna uma linha por EJ, com o GAP MEMBROS correto (ele é um atributo
    da EJ, repetido em cada linha/produto que ela participou — aqui usamos
    o valor máximo, que equivale ao valor único já que não varia por EJ).

    Isso é o equivalente, em pandas, ao problema que no Looker Studio exige
    truques de agregação em dois níveis: aqui basta um groupby.
    """
    agg_dict = {
        "GAP MEMBROS": "max",
        "MEMBROS TOTAL": "max",
        "MEMBROS ECM": "max",
        "ECM META": "max",
        "ECM ATUAL": "max",
        "CLUSTER": "max",
        "FEDERACAO": "first",
    }
    agg_dict = {k: v for k, v in agg_dict.items() if k in df.columns}
    return df.groupby("EJ", as_index=False).agg(agg_dict)


# --------------------------------------------------------------------------
# Carregar arquivo
# --------------------------------------------------------------------------
st.sidebar.title("📂 Base de dados")
uploaded_file = st.sidebar.file_uploader(
    "Envie a base (Base_de_Dados_ECM.xlsx ou o .csv da aba 'Produtos de Conexão')",
    type=["xlsx", "csv"],
)

if uploaded_file is None:
    st.title("📊 Dashboard ECM - Produtos de Conexão")
    st.info(
        "Envie o arquivo **.xlsx** (com a aba 'Produtos de Conexão') ou o "
        "**.csv** exportado dessa aba, na barra lateral, para começar."
    )
    st.stop()

df = load_data(uploaded_file)

# --------------------------------------------------------------------------
# Filtros (sidebar)
# --------------------------------------------------------------------------
st.sidebar.title("🔎 Filtros")

produtos_sel = st.sidebar.multiselect(
    "Produto de Conexão",
    options=sorted(df["PRODUTO_DE_CONEXAO"].dropna().unique()),
    default=None,
)
clusters_sel = st.sidebar.multiselect(
    "Cluster",
    options=sorted(df["CLUSTER"].dropna().unique()),
    default=None,
)
federacoes_sel = st.sidebar.multiselect(
    "Federação",
    options=sorted(df["FEDERACAO"].dropna().unique()),
    default=None,
)
ejs_sel = st.sidebar.multiselect(
    "EJ",
    options=sorted(df["EJ"].dropna().unique()),
    default=None,
)

df_filt = df.copy()
if produtos_sel:
    df_filt = df_filt[df_filt["PRODUTO_DE_CONEXAO"].isin(produtos_sel)]
if clusters_sel:
    df_filt = df_filt[df_filt["CLUSTER"].isin(clusters_sel)]
if federacoes_sel:
    df_filt = df_filt[df_filt["FEDERACAO"].isin(federacoes_sel)]
if ejs_sel:
    df_filt = df_filt[df_filt["EJ"].isin(ejs_sel)]

if df_filt.empty:
    st.warning("Nenhum registro encontrado para os filtros selecionados.")
    st.stop()

# Base deduplicada por EJ — é ela que alimenta os KPIs e comparativos de gap
df_ej = dedup_por_ej(df_filt)

# --------------------------------------------------------------------------
# Título
# --------------------------------------------------------------------------
st.title("📊 Dashboard ECM - Produtos de Conexão")
st.caption(
    "Gap de membros somado por EJ única — cada EJ conta apenas uma vez, "
    "independentemente de quantos produtos/eventos ela participou."
)

# --------------------------------------------------------------------------
# KPIs
# --------------------------------------------------------------------------
col1, col2, col3, col4 = st.columns(4)

col1.metric("EJs únicas (no filtro)", f"{df_ej['EJ'].nunique()}")
col2.metric("Gap total de membros", f"{int(df_ej['GAP MEMBROS'].sum())}")
col3.metric(
    "Gap médio por EJ",
    f"{df_ej['GAP MEMBROS'].mean():.1f}" if not df_ej.empty else "-",
)
col4.metric(
    "NPS médio (produtos filtrados)",
    f"{df_filt['NPS'].mean():.1f}" if df_filt["NPS"].notna().any() else "-",
)

st.divider()

# --------------------------------------------------------------------------
# Comparativos entre grupos
# --------------------------------------------------------------------------
st.subheader("Comparativos entre grupos")

c1, c2 = st.columns(2)

with c1:
    gap_por_cluster = (
        df_ej.groupby("CLUSTER", as_index=False)["GAP MEMBROS"]
        .sum()
        .sort_values("CLUSTER")
    )
    fig = px.bar(
        gap_por_cluster,
        x="CLUSTER",
        y="GAP MEMBROS",
        title="Gap total de membros por Cluster (EJs únicas)",
        text_auto=True,
    )
    fig.update_layout(xaxis_type="category")
    st.plotly_chart(fig, use_container_width=True)

with c2:
    if df_ej["FEDERACAO"].nunique() > 1:
        gap_por_fed = (
            df_ej.groupby("FEDERACAO", as_index=False)["GAP MEMBROS"]
            .sum()
            .sort_values("GAP MEMBROS", ascending=False)
        )
        fig = px.bar(
            gap_por_fed,
            x="FEDERACAO",
            y="GAP MEMBROS",
            title="Gap total de membros por Federação (EJs únicas)",
            text_auto=True,
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        # Com uma federação só, mostra a distribuição do gap por EJ
        top_ej = df_ej.sort_values("GAP MEMBROS", ascending=False).head(15)
        fig = px.bar(
            top_ej,
            x="EJ",
            y="GAP MEMBROS",
            title="Top 15 EJs por gap de membros",
            text_auto=True,
        )
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)

st.subheader("Comparativo entre Produtos de Conexão")

c3, c4 = st.columns(2)

with c3:
    nps_por_produto = (
        df_filt.groupby("PRODUTO_DE_CONEXAO", as_index=False)["NPS"]
        .mean()
        .sort_values("NPS", ascending=False)
    )
    fig = px.bar(
        nps_por_produto,
        x="PRODUTO_DE_CONEXAO",
        y="NPS",
        title="NPS médio por Produto de Conexão",
        text_auto=".2f",
    )
    fig.update_layout(xaxis_tickangle=-30)
    st.plotly_chart(fig, use_container_width=True)

with c4:
    participantes_por_produto = df_filt.groupby(
        "PRODUTO_DE_CONEXAO", as_index=False
    )["PARTICIPANTES"].sum().sort_values("PARTICIPANTES", ascending=False)
    fig = px.bar(
        participantes_por_produto,
        x="PRODUTO_DE_CONEXAO",
        y="PARTICIPANTES",
        title="Total de participantes por Produto de Conexão",
        text_auto=True,
    )
    fig.update_layout(xaxis_tickangle=-30)
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# --------------------------------------------------------------------------
# Tabela detalhada por EJ (já deduplicada)
# --------------------------------------------------------------------------
st.subheader("Detalhamento por EJ (deduplicado)")
st.dataframe(
    df_ej.sort_values("GAP MEMBROS", ascending=False),
    use_container_width=True,
    hide_index=True,
)

with st.expander("Ver base bruta filtrada (uma linha por EJ x produto)"):
    st.dataframe(df_filt, use_container_width=True, hide_index=True)
