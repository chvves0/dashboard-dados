"""
Dashboard de Engajamento com o MEJ (ECM)
Análise do indicador a partir da base de Produtos de Conexão.
"""

import io
import math
import unicodedata
from pathlib import Path
from urllib.parse import quote, urlparse

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# --------------------------------------------------------------------------
# Configuração e identidade visual
# --------------------------------------------------------------------------

st.set_page_config(
    page_title="Engajamento com o MEJ",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

NAVY = "#02195B"
AMARELO = "#FFC831"
VERDE = "#2D783A"
VERMELHO = "#C8442E"
VINHO = "#8C2D1B"
OURO = "#E0A800"
CINZA = "#9AA3B2"
LINHA = "#E3E6EC"
TEXTO = "#0B1B3D"
MUDO = "#68718A"

# Cores dos cartões de KPI — mexa aqui para mudar o visual dos indicadores.
FUNDO_KPI = "#FFFFFF"          # fundo do cartão
BORDA_KPI = LINHA              # contorno
ROTULO_KPI = MUDO              # título pequeno em cima
VALOR_KPI = TEXTO              # o número grande
LEGENDA_KPI = MUDO             # a linha de apoio embaixo
# Faixa colorida na lateral esquerda, uma cor por coluna (esquerda → direita).
# Deixe a lista vazia para tirar as faixas: TRILHOS_KPI = []
TRILHOS_KPI = [NAVY, VERDE, OURO]

# --------------------------------------------------------------------------
# Origem dos dados
# --------------------------------------------------------------------------
# O app lê o CSV que está no próprio repositório, ao lado deste arquivo (ou
# dentro de uma pasta "dados"). Basta commitar a planilha junto do app.py.
#
# Se você preferir apontar para o arquivo em OUTRO repositório — ou trocar a
# base sem precisar de um novo deploy — cole aqui o link "raw" do GitHub:
#
#   URL_DADOS = "https://raw.githubusercontent.com/USUARIO/REPO/main/dados/produtos.csv"
#
# Deixe a string vazia para usar o arquivo local do repositório.
URL_DADOS = ""

# Minutos que o app segura a base em cache quando lê por URL. Depois disso ele
# busca o arquivo de novo, então uma atualização no GitHub aparece sozinha.
CACHE_MINUTOS = 10

PASTA_APP = Path(__file__).resolve().parent

NOMES_ACEITOS = [
    "Produtos_de_Conexão.csv",
    "Produtos_de_Conexao.csv",
    "produtos_de_conexao.csv",
    "produtos_de_conexão.csv",
]

SITUACOES = {
    "sem_registro": {"rotulo": "Não aparece em nenhum produto", "cor": VINHO, "ordem": 0},
    "abaixo": {"rotulo": "Abaixo de 50% da meta", "cor": VERMELHO, "ordem": 1},
    "parcial": {"rotulo": "Entre 50% e 99% da meta", "cor": OURO, "ordem": 2},
    "meta": {"rotulo": "Meta de ECM batida", "cor": VERDE, "ordem": 3},
    "sem_dados": {"rotulo": "Sem base de membros", "cor": CINZA, "ordem": 4},
}
ORDEM_SIT = sorted(SITUACOES, key=lambda k: SITUACOES[k]["ordem"])

TRILHOS_CSS = "\n".join(
    f'    div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]'
    f":nth-child({posicao}) div[data-testid=\"stMetric\"] "
    f"{{ border-left: 4px solid {cor}; }}"
    for posicao, cor in enumerate(TRILHOS_KPI, start=1)
)

st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&family=Raleway:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] {{ font-family: 'Raleway', sans-serif; }}
    h1, h2, h3, h4 {{ font-family: 'Poppins', sans-serif; letter-spacing: -0.01em; }}

    .bloco-topo {{
        background: {NAVY};
        border-bottom: 4px solid {AMARELO};
        border-radius: 14px;
        padding: 26px 30px 22px;
        margin-bottom: 22px;
    }}
    .bloco-topo h1 {{ color: #fff; font-size: 28px; font-weight: 600; margin: 0 0 6px; }}
    .bloco-topo p {{ color: #B9C3DE; font-size: 14px; margin: 0; max-width: 820px; }}
    .bloco-topo .selo {{
        font-family: 'Poppins', sans-serif; font-size: 11px; letter-spacing: .18em;
        text-transform: uppercase; color: {AMARELO}; font-weight: 600;
    }}

    div[data-testid="stMetric"] {{
        background: {FUNDO_KPI}; border: 1px solid {BORDA_KPI}; border-radius: 14px;
        padding: 16px 18px 14px; box-shadow: 0 2px 10px rgba(2,25,91,.05);
    }}
    div[data-testid="stMetric"] label,
    div[data-testid="stMetricLabel"],
    div[data-testid="stMetricLabel"] p {{
        font-family: 'Poppins', sans-serif; font-size: 12px; font-weight: 600;
        color: {ROTULO_KPI} !important; letter-spacing: .03em;
    }}
    div[data-testid="stMetricValue"],
    div[data-testid="stMetricValue"] div {{
        font-family: 'Poppins', sans-serif; color: {VALOR_KPI} !important;
        font-weight: 600;
    }}
    div[data-testid="stMetricDelta"],
    div[data-testid="stMetricDelta"] div,
    div[data-testid="stMetricDelta"] p {{
        color: {LEGENDA_KPI} !important; background: transparent !important;
        font-size: 12.5px;
    }}
    div[data-testid="stMetricDelta"] svg {{ display: none; }}
{TRILHOS_CSS}

    .painel {{
        background: #fff; border: 1px solid {LINHA}; border-radius: 14px;
        padding: 18px 20px 14px; height: 100%;
    }}
    .painel h3 {{ font-size: 16px; margin: 0 0 2px; color: {LINHA}; }}
    .painel .dica {{ font-size: 12.5px; color: {MUDO}; margin: 0 0 12px; }}

    .rodape {{
        font-size: 12.5px; color: {MUDO}; line-height: 1.7;
        border-top: 1px solid {LINHA}; padding-top: 16px; margin-top: 8px;
    }}
    .rodape b {{ color: {LINHA}; }}

    div[data-testid="stSidebar"] {{ background: #FAFBFD; }}
    </style>
    """,
    unsafe_allow_html=True,
)


# --------------------------------------------------------------------------
# Formatação
# --------------------------------------------------------------------------

def num(valor) -> str:
    """Inteiro no padrão brasileiro. Vazio vira travessão."""
    if valor is None or pd.isna(valor):
        return "—"
    return f"{int(round(float(valor))):,}".replace(",", ".")


def pct(valor, casas: int = 1) -> str:
    """Percentual no padrão brasileiro. Vazio vira travessão."""
    if valor is None or pd.isna(valor):
        return "—"
    valor = float(valor)
    texto = f"{valor:,.{casas}f}".replace(",", "@").replace(".", ",").replace("@", ".")
    return f"{texto}%"


def sem_acento(texto: str) -> str:
    normalizado = unicodedata.normalize("NFKD", str(texto))
    return "".join(c for c in normalizado if not unicodedata.combining(c)).lower().strip()


# --------------------------------------------------------------------------
# Leitura e preparo da base
# --------------------------------------------------------------------------

def _para_numero(serie: pd.Series) -> pd.Series:
    """Converte texto com vírgula decimal e sujeira de planilha em número."""
    limpo = (
        serie.astype("string")
        .str.strip()
        .str.replace("%", "", regex=False)
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
    )
    limpo = limpo.mask(limpo.str.contains("REF|DIV|N/A|VALUE", case=False, na=False))
    return pd.to_numeric(limpo, errors="coerce")


def localizar_base() -> tuple[object | None, str]:
    """
    Decide de onde ler a planilha e devolve (fonte, descrição da origem).

    Ordem: URL_DADOS, se preenchida; senão o CSV do repositório, procurando
    pelos nomes conhecidos, depois qualquer .csv na pasta do app ou em /dados.
    """
    if URL_DADOS.strip():
        endereco = URL_DADOS.strip()
        # nomes com acento precisam ser escapados para virar URL válida
        partes = urlparse(endereco)
        endereco = partes._replace(path=quote(partes.path)).geturl()
        return endereco, f"GitHub · {Path(partes.path).name}"

    candidatos = [PASTA_APP / nome for nome in NOMES_ACEITOS]
    candidatos += [PASTA_APP / "dados" / nome for nome in NOMES_ACEITOS]
    for caminho in candidatos:
        if caminho.exists():
            return caminho, f"repositório · {caminho.name}"

    sobras = sorted(PASTA_APP.glob("*.csv")) + sorted((PASTA_APP / "dados").glob("*.csv"))
    if sobras:
        return sobras[0], f"repositório · {sobras[0].name}"

    return None, ""


@st.cache_data(show_spinner="Lendo a base…", ttl=CACHE_MINUTOS * 60)
def carregar(fonte, _versao: str = "") -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """
    Lê o CSV exportado da planilha e devolve:
      - participacoes: uma linha por produto de conexão × EJ
      - empresas: uma linha por EJ (universo completo da rede)
      - avisos: contagens úteis para exibir no rodapé
    """
    try:
        bruto = pd.read_csv(fonte, dtype=str, encoding="utf-8")
    except UnicodeDecodeError:
        if hasattr(fonte, "seek"):
            fonte.seek(0)
        bruto = pd.read_csv(fonte, dtype=str, encoding="latin-1")

    bruto.columns = [c.strip() for c in bruto.columns]

    # ---- bloco principal: produto de conexão × EJ -------------------------
    participacoes = bruto[bruto["ID_DO_PRODUTO"].notna() & bruto["EJ"].notna()].copy()

    renomear = {
        "ID_DO_PRODUTO": "id_produto",
        "PRODUTO_DE_CONEXAO": "produto",
        "NPS": "nps",
        "ID_EJ": "id_ej",
        "EJ": "ej",
        "FEDERACAO": "federacao",
        "PARTICIPANTES": "participantes",
        "CLUSTER": "cluster",
        "ECM META": "meta",
        "ECM ATUAL": "atual",
        "MEMBROS TOTAL": "membros",
        "MEMBROS ECM": "engajados",
        "GAP MEMBROS": "gap_planilha",
    }
    participacoes = participacoes.rename(columns=renomear)
    participacoes = participacoes[[c for c in renomear.values() if c in participacoes.columns]]

    for coluna in ["participantes", "cluster", "membros", "engajados", "gap_planilha", "nps", "id_ej"]:
        if coluna in participacoes.columns:
            participacoes[coluna] = _para_numero(participacoes[coluna])

    for coluna in ["meta", "atual"]:
        participacoes[coluna] = _para_numero(participacoes[coluna])
        # aceita tanto 0,75 quanto 75
        if participacoes[coluna].max(skipna=True) is not pd.NA and participacoes[coluna].max() > 1.5:
            participacoes[coluna] = participacoes[coluna] / 100

    for coluna in ["ej", "produto", "federacao"]:
        participacoes[coluna] = participacoes[coluna].astype("string").str.strip()

    participacoes["produto"] = participacoes["produto"].fillna("Produto sem nome")

    # ---- bloco lateral: universo de EJs da rede ---------------------------
    universo = pd.DataFrame(columns=["ej", "gap_lateral"])
    if "EJ Única" in bruto.columns:
        lateral = bruto[["EJ Única"]].copy()
        lateral["gap_lateral"] = (
            _para_numero(bruto["Gap por EJ"]) if "Gap por EJ" in bruto.columns else pd.NA
        )
        lateral = lateral.rename(columns={"EJ Única": "ej"})
        lateral["ej"] = lateral["ej"].astype("string").str.strip()
        universo = lateral[lateral["ej"].notna() & (lateral["ej"] != "")].drop_duplicates("ej")

    # ---- consolidação por EJ ---------------------------------------------
    colunas_ej = ["ej", "federacao", "cluster", "meta", "atual", "membros", "engajados"]
    empresas = (
        participacoes.sort_values("ej")
        .drop_duplicates("ej")[colunas_ej]
        .reset_index(drop=True)
    )

    resumo = (
        participacoes.groupby("ej", as_index=False)
        .agg(produtos=("id_produto", "nunique"), presencas=("participantes", "sum"))
    )
    empresas = empresas.merge(resumo, on="ej", how="left")

    # EJs da rede que não aparecem em nenhum produto de conexão
    if not universo.empty:
        chave_main = {sem_acento(e) for e in empresas["ej"]}
        ausentes = universo[~universo["ej"].map(sem_acento).isin(chave_main)].copy()
        if not ausentes.empty:
            ausentes["federacao"] = empresas["federacao"].mode().iat[0] if len(empresas) else pd.NA
            ausentes["engajados"] = 0.0
            ausentes["atual"] = 0.0
            ausentes["produtos"] = 0
            ausentes["presencas"] = 0.0
            empresas = pd.concat([empresas, ausentes], ignore_index=True)

    if "gap_lateral" in empresas.columns:
        empresas["gap_lateral"] = _para_numero(empresas["gap_lateral"].astype("string"))
    else:
        empresas["gap_lateral"] = pd.NA

    empresas["produtos"] = empresas["produtos"].fillna(0).astype(int)
    empresas["presencas"] = empresas["presencas"].fillna(0)

    # ---- métricas do indicador -------------------------------------------
    empresas["atual"] = empresas.apply(
        lambda l: (l["engajados"] / l["membros"])
        if pd.notna(l.get("membros")) and l.get("membros", 0) > 0 and pd.notna(l.get("engajados"))
        else l.get("atual"),
        axis=1,
    )

    empresas["alcance"] = (empresas["atual"] / empresas["meta"] * 100).where(
        empresas["meta"].notna() & (empresas["meta"] > 0)
    )

    def calcular_gap(linha):
        if pd.notna(linha["meta"]) and pd.notna(linha["membros"]) and linha["membros"] > 0:
            alvo = math.ceil(linha["meta"] * linha["membros"] - 1e-9)
            return max(0, int(alvo - (linha["engajados"] or 0)))
        if pd.notna(linha["gap_lateral"]):
            return int(linha["gap_lateral"])
        return pd.NA

    empresas["gap"] = empresas.apply(calcular_gap, axis=1)

    def situacao(linha):
        if linha["produtos"] == 0:
            return "sem_registro"
        if pd.isna(linha["membros"]) or (linha["membros"] or 0) <= 0 or pd.isna(linha["alcance"]):
            return "sem_dados"
        if linha["alcance"] >= 100:
            return "meta"
        if linha["alcance"] >= 50:
            return "parcial"
        return "abaixo"

    empresas["situacao"] = empresas.apply(situacao, axis=1)
    empresas["cluster"] = empresas["cluster"].fillna(0)
    empresas["federacao"] = empresas["federacao"].fillna("Não informada")

    avisos = {
        "linhas_lidas": len(bruto),
        "participacoes": len(participacoes),
        "ejs_rede": len(empresas),
        "ejs_sem_produto": int((empresas["produtos"] == 0).sum()),
        "ejs_sem_membros": int((empresas["situacao"] == "sem_dados").sum()),
    }

    return participacoes, empresas.sort_values("ej").reset_index(drop=True), avisos


# --------------------------------------------------------------------------
# Componentes visuais
# --------------------------------------------------------------------------

def barra_situacao(empresas: pd.DataFrame) -> go.Figure:
    total = max(len(empresas), 1)
    figura = go.Figure()
    for chave in ORDEM_SIT:
        quantidade = int((empresas["situacao"] == chave).sum())
        if quantidade == 0:
            continue
        figura.add_bar(
            x=[quantidade],
            y=["EJs"],
            orientation="h",
            name=SITUACOES[chave]["rotulo"],
            marker_color=SITUACOES[chave]["cor"],
            text=[str(quantidade)],
            textposition="inside",
            insidetextanchor="middle",
            textfont=dict(color="#fff", size=13, family="Poppins"),
            hovertemplate=(
                f"<b>{SITUACOES[chave]['rotulo']}</b><br>"
                f"{quantidade} EJs ({quantidade / total * 100:.1f}%)<extra></extra>"
            ),
        )
    figura.update_layout(
        barmode="stack",
        height=130,
        margin=dict(l=0, r=0, t=6, b=0),
        showlegend=True,
        legend=dict(orientation="h", y=-0.55, x=0, font=dict(size=11)),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return figura


def barras_horizontais(rotulos, valores, cores, sufixo="", altura=None) -> go.Figure:
    figura = go.Figure(
        go.Bar(
            x=valores,
            y=rotulos,
            orientation="h",
            marker_color=cores,
            text=[f"{num(v)}{sufixo}" for v in valores],
            textposition="outside",
            textfont=dict(family="Poppins", size=12, color=LINHA),
            hovertemplate="<b>%{y}</b><br>%{x}<extra></extra>",
        )
    )
    limite = max(valores) if len(valores) and max(valores) > 0 else 1
    figura.update_layout(
        height=altura or max(150, 42 * len(rotulos) + 40),
        margin=dict(l=0, r=40, t=6, b=6),
        xaxis=dict(visible=False, range=[0, limite * 1.18]),
        yaxis=dict(autorange="reversed", tickfont=dict(size=12.5)),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        bargap=0.32,
    )
    return figura


def painel(titulo: str, dica: str) -> None:
    st.markdown(
        f"<div style='margin-bottom:6px'><h3 style=\"font-family:Poppins;font-size:16px;"
        f"margin:0;color:{LINHA}\">{titulo}</h3>"
        f"<p style='font-size:12.5px;color:{MUDO};margin:2px 0 10px'>{dica}</p></div>",
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------
# Aplicação
# --------------------------------------------------------------------------

st.markdown(
    """
    <div class="bloco-topo">
      <div class="selo">Planejamento Estratégico 25-27 · Lideranças Protagonistas</div>
      <h1>Engajamento com o MEJ</h1>
      <p>Cada EJ tem uma meta própria de percentual de membros que participam de produtos
      de conexão. Este painel mostra onde a rede está em relação a essas metas, quantas
      pessoas ainda faltam engajar e quais produtos de conexão alcançaram quais EJs.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("### Base de dados")
    enviado = st.file_uploader(
        "Enviar outra planilha (só nesta sessão)",
        type=["csv"],
        help="Use para testar um arquivo sem commitar nada no repositório.",
    )

fonte_repo, origem = localizar_base()

if enviado is not None:
    fonte, origem, versao = enviado, f"arquivo enviado · {enviado.name}", enviado.name
elif fonte_repo is None:
    st.error(
        "Não encontrei nenhum CSV no repositório. Commite a planilha ao lado do "
        "`app.py` (ou dentro de uma pasta `dados/`), ou preencha `URL_DADOS` no "
        "topo do arquivo com o link raw do GitHub."
    )
    st.stop()
else:
    fonte = fonte_repo
    # arquivo local: o horário de modificação invalida o cache quando o CSV muda
    versao = (
        str(fonte_repo.stat().st_mtime) if isinstance(fonte_repo, Path) else URL_DADOS
    )

try:
    participacoes, empresas, avisos = carregar(fonte, versao)
except FileNotFoundError:
    st.error(f"O arquivo **{fonte}** não existe mais. Confira o caminho no repositório.")
    st.stop()
except Exception as erro:  # noqa: BLE001
    st.error(
        f"Não consegui ler a planilha ({origem}): {erro}\n\n"
        "Se estiver lendo por URL, confirme que o link é o **raw** do GitHub "
        "(`raw.githubusercontent.com`) e que o repositório é público."
    )
    st.stop()

# ---- filtros --------------------------------------------------------------

with st.sidebar:
    st.markdown("### Filtros")

    federacoes = sorted(empresas["federacao"].dropna().unique())
    if len(federacoes) > 1:
        escolha_fed = st.selectbox("Federação", ["Todas"] + federacoes)
    else:
        escolha_fed = federacoes[0] if federacoes else "Todas"
        st.caption(f"Federação: **{escolha_fed}**")

    clusters = sorted(int(c) for c in empresas["cluster"].dropna().unique())
    escolha_cluster = st.multiselect(
        "Cluster",
        clusters,
        format_func=lambda c: f"Cluster {c}" if c > 0 else "Sem cluster",
    )

    produtos = sorted(participacoes["produto"].dropna().unique())
    escolha_produto = st.multiselect("Participou de qual produto de conexão", produtos)

    situacoes_na_base = [s for s in ORDEM_SIT if (empresas["situacao"] == s).any()]
    escolha_situacao = st.multiselect(
        "Situação da meta",
        situacoes_na_base,
        format_func=lambda s: SITUACOES[s]["rotulo"],
    )

    busca = st.text_input("Buscar EJ pelo nome", placeholder="ex.: Crop")

    st.divider()
    st.caption(
        f"{avisos['participacoes']} registros de participação · "
        f"{avisos['ejs_rede']} EJs na rede · "
        f"{participacoes['produto'].nunique()} produtos de conexão"
    )
    st.caption(f"Fonte: {origem}")
    if st.button("Recarregar a base", width="stretch"):
        st.cache_data.clear()
        st.rerun()

filtro = pd.Series(True, index=empresas.index)
if escolha_fed and escolha_fed != "Todas":
    filtro &= empresas["federacao"] == escolha_fed
if escolha_cluster:
    filtro &= empresas["cluster"].isin(escolha_cluster)
if escolha_situacao:
    filtro &= empresas["situacao"].isin(escolha_situacao)
if busca.strip():
    alvo = sem_acento(busca)
    filtro &= empresas["ej"].map(lambda e: alvo in sem_acento(e))
if escolha_produto:
    presentes = set(participacoes.loc[participacoes["produto"].isin(escolha_produto), "ej"])
    filtro &= empresas["ej"].isin(presentes)

selecao = empresas[filtro].copy()
part_selecao = participacoes[participacoes["ej"].isin(set(selecao["ej"]))].copy()

if selecao.empty:
    st.warning("Nenhuma EJ atende a esses filtros. Ajuste a seleção na barra lateral.")
    st.stop()

# ---- indicadores principais ----------------------------------------------

bateram = int(((selecao["gap"] == 0) & (selecao["situacao"] != "sem_registro")).sum())
membros_rede = selecao["membros"].sum(skipna=True)
engajados_rede = selecao["engajados"].sum(skipna=True)
ecm_rede = (engajados_rede / membros_rede * 100) if membros_rede else float("nan")
gap_total = selecao["gap"].dropna().sum()
ejs_com_gap = int((selecao["gap"].fillna(0) > 0).sum())
sem_produto = int((selecao["produtos"] == 0).sum())

linha1 = st.columns(3)
linha1[0].metric(
    "EJs que bateram a meta de ECM",
    f"{bateram}",
    delta=f"{pct(bateram / len(selecao) * 100)} das {len(selecao)} EJ{'s' if len(selecao) != 1 else ''} da seleção",
    delta_color="off",
)
linha1[1].metric(
    "Engajamento da rede",
    pct(ecm_rede),
    delta=f"{num(engajados_rede)} de {num(membros_rede)} membros em produtos de conexão",
    delta_color="off",
)
linha1[2].metric(
    "Pessoas para fechar todas as metas",
    num(gap_total),
    delta=f"distribuídas em {ejs_com_gap} EJ{'s' if ejs_com_gap != 1 else ''}",
    delta_color="off",
)

linha2 = st.columns(3)
linha2[0].metric(
    "EJs sem nenhuma participação",
    f"{sem_produto}",
    delta="não aparecem em nenhum produto de conexão",
    delta_color="off",
)
linha2[1].metric(
    "Produtos de conexão na base",
    f"{part_selecao['produto'].nunique()}",
    delta=f"{num(part_selecao['participantes'].sum())} presenças somadas",
    delta_color="off",
)
linha2[2].metric(
    "Média de produtos por EJ",
    f"{selecao['produtos'].mean():.1f}".replace(".", ","),
    delta="entre as EJs da seleção",
    delta_color="off",
)

st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

# ---- distribuição e faixas de gap ----------------------------------------

col_esq, col_dir = st.columns([1.15, 0.85])

with col_esq:
    with st.container(border=True):
        painel(
            "Onde a rede está em relação à meta",
            "Cada EJ classificada pelo quanto já alcançou da própria meta de ECM.",
        )
        st.plotly_chart(barra_situacao(selecao), width="stretch", key="situacao")

        painel(
            "Quantas pessoas faltam para bater a meta",
            "Só as EJs que ainda não fecharam a meta. O número dentro da barra é a "
            "quantidade de EJs; ao lado, o total de pessoas envolvidas.",
        )
        faixas = [
            ("Falta 1 pessoa", lambda g: g == 1),
            ("Faltam 2", lambda g: g == 2),
            ("Faltam 3 a 5", lambda g: (g >= 3) & (g <= 5)),
            ("Faltam 6 a 10", lambda g: (g >= 6) & (g <= 10)),
            ("Faltam 11 ou mais", lambda g: g >= 11),
        ]
        gaps = selecao["gap"].fillna(0).astype(int)
        rotulos, quantidades, pessoas = [], [], []
        for nome, teste in faixas:
            mascara = teste(gaps)
            rotulos.append(nome)
            quantidades.append(int(mascara.sum()))
            pessoas.append(int(gaps[mascara].sum()))

        if sum(quantidades) == 0:
            st.success("Todas as EJs da seleção já bateram a meta de ECM.")
        else:
            figura = barras_horizontais(
                rotulos, quantidades, [VERMELHO, VERMELHO, OURO, OURO, VINHO]
            )
            figura.data[0].text = [
                f"{q} EJ{'s' if q != 1 else ''} · {p} pessoas"
                for q, p in zip(quantidades, pessoas)
            ]
            st.plotly_chart(figura, width="stretch", key="faixas_gap")
            st.caption(
                f"As {quantidades[0] + quantidades[1]} EJs a uma ou duas pessoas da meta "
                f"somam {pessoas[0] + pessoas[1]} pessoas — é o esforço mais barato da lista."
            )

with col_dir:
    with st.container(border=True):
        painel(
            "Panorama por cluster",
            "Percentual de EJs que já bateram a meta em cada cluster.",
        )
        por_cluster = (
            selecao.assign(
                bateu=(selecao["gap"] == 0) & (selecao["situacao"] != "sem_registro")
            )
            .groupby("cluster")
            .agg(ejs=("ej", "count"), bateram=("bateu", "sum"), gap=("gap", "sum"))
            .reset_index()
        )
        por_cluster["taxa"] = por_cluster["bateram"] / por_cluster["ejs"] * 100
        por_cluster["rotulo"] = por_cluster["cluster"].map(
            lambda c: f"Cluster {int(c)}" if c > 0 else "Sem cluster"
        )
        por_cluster = por_cluster.sort_values("taxa", ascending=False)

        figura_cluster = barras_horizontais(
            por_cluster["rotulo"].tolist(),
            por_cluster["taxa"].round(1).tolist(),
            [VERDE if t >= 50 else OURO if t >= 25 else VERMELHO for t in por_cluster["taxa"]],
        )
        figura_cluster.data[0].text = [
            f"{pct(t)} ({int(b)}/{int(e)})"
            for t, b, e in zip(por_cluster["taxa"], por_cluster["bateram"], por_cluster["ejs"])
        ]
        st.plotly_chart(figura_cluster, width="stretch", key="clusters")

        st.markdown(
            f"<p style='font-size:12.5px;color:{MUDO};margin:10px 0 0'>"
            "Clusters menores costumam ter metas mais baixas e menos membros: "
            "conseguem fechar a meta com pouca gente, mas somem do painel quando "
            "nenhum produto chega até eles.</p>",
            unsafe_allow_html=True,
        )

# ---- produtos de conexão --------------------------------------------------

st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

with st.container(border=True):
    painel(
        "Alcance de cada produto de conexão",
        "Quantas EJs diferentes cada produto tocou e quantas dependeram só dele. "
        "Para o indicador da federação, espalhar entre EJs vale mais que lotar o evento.",
    )

    if part_selecao.empty:
        st.info(
            "Nenhuma EJ desta seleção aparece em produtos de conexão, então não há "
            "alcance por produto para mostrar aqui."
        )
    else:
        contagem_ej = participacoes.groupby("ej")["id_produto"].nunique()
        exclusivas = set(contagem_ej[contagem_ej == 1].index)

        por_produto = (
            part_selecao.groupby("produto")
            .agg(ejs=("ej", "nunique"), presencas=("participantes", "sum"))
            .reset_index()
        )
        por_produto["exclusivas"] = por_produto["produto"].map(
            lambda p: len(set(part_selecao.loc[part_selecao["produto"] == p, "ej"]) & exclusivas)
        )
        for coluna in ["ejs", "presencas", "exclusivas"]:
            por_produto[coluna] = pd.to_numeric(por_produto[coluna]).fillna(0).astype(int)
        por_produto["cobertura"] = por_produto["ejs"] / len(empresas) * 100
        por_produto["media"] = por_produto["presencas"] / por_produto["ejs"].replace(0, pd.NA)
        por_produto = por_produto.sort_values("ejs", ascending=False)

        col_a, col_b = st.columns([1, 1])

        with col_a:
            figura_produto = go.Figure()
            figura_produto.add_bar(
                x=(por_produto["ejs"] - por_produto["exclusivas"]).tolist(),
                y=por_produto["produto"].tolist(),
                orientation="h",
                name="EJs que também foram a outros produtos",
                marker_color=NAVY,
                hovertemplate="<b>%{y}</b><br>%{x} EJs (também em outros produtos)<extra></extra>",
            )
            figura_produto.add_bar(
                x=por_produto["exclusivas"].tolist(),
                y=por_produto["produto"].tolist(),
                orientation="h",
                name="EJs alcançadas só por este produto",
                marker_color=AMARELO,
                hovertemplate="<b>%{y}</b><br>%{x} EJs exclusivas<extra></extra>",
            )
            figura_produto.update_layout(
                barmode="stack",
                height=max(220, 46 * len(por_produto) + 70),
                margin=dict(l=0, r=20, t=6, b=0),
                xaxis=dict(title="EJs alcançadas", gridcolor=LINHA, zeroline=False),
                yaxis=dict(autorange="reversed", tickfont=dict(size=12)),
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                legend=dict(orientation="h", y=-0.22, x=0, font=dict(size=11)),
            )
            st.plotly_chart(figura_produto, width="stretch", key="produtos")

        with col_b:
            tabela_produto = por_produto.assign(
                cobertura_txt=por_produto["cobertura"].map(pct),
                media_txt=por_produto["media"].map(
                    lambda v: "—" if pd.isna(v) else f"{v:.1f}".replace(".", ",")
                ),
            )[["produto", "ejs", "cobertura_txt", "presencas", "media_txt", "exclusivas"]]

            st.dataframe(
                tabela_produto,
                hide_index=True,
                width="stretch",
                column_config={
                    "produto": st.column_config.TextColumn("Produto de conexão"),
                    "ejs": st.column_config.NumberColumn("EJs", width="small"),
                    "cobertura_txt": st.column_config.TextColumn("% da rede", width="small"),
                    "presencas": st.column_config.NumberColumn("Presenças", width="small"),
                    "media_txt": st.column_config.TextColumn("Média/EJ", width="small"),
                    "exclusivas": st.column_config.NumberColumn("Exclusivas", width="small"),
                },
            )
            st.caption(
                "**Exclusivas** são EJs que apareceram em um único produto no ano — se "
                "aquele produto não existisse, elas ficariam com zero engajamento."
            )

# ---- tabela de EJs --------------------------------------------------------

st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

with st.container(border=True):
    painel(
        "EJs da seleção",
        "Clique no cabeçalho para reordenar. O alcance é o quanto a EJ já cumpriu da "
        "própria meta.",
    )

    tabela = selecao.copy()
    tabela["situacao_txt"] = tabela["situacao"].map(lambda s: SITUACOES[s]["rotulo"])
    tabela["cluster_txt"] = tabela["cluster"].map(
        lambda c: f"C{int(c)}" if c > 0 else "—"
    )
    tabela["meta_pct"] = tabela["meta"] * 100
    tabela["atual_pct"] = tabela["atual"] * 100

    exibir = tabela[
        [
            "ej", "cluster_txt", "membros", "engajados", "atual_pct", "meta_pct",
            "alcance", "gap", "produtos", "presencas", "situacao_txt",
        ]
    ].sort_values("gap", ascending=False, na_position="last")

    st.dataframe(
        exibir,
        hide_index=True,
        width="stretch",
        height=520,
        column_config={
            "ej": st.column_config.TextColumn("Empresa Júnior", width="large"),
            "cluster_txt": st.column_config.TextColumn("Cluster", width="small"),
            "membros": st.column_config.NumberColumn("Membros", format="%d", width="small"),
            "engajados": st.column_config.NumberColumn("Engajados", format="%d", width="small"),
            "atual_pct": st.column_config.NumberColumn("% ECM atual", format="%.1f%%"),
            "meta_pct": st.column_config.NumberColumn("Meta", format="%.0f%%", width="small"),
            "alcance": st.column_config.ProgressColumn(
                "Alcance da meta", format="%.0f%%", min_value=0, max_value=150
            ),
            "gap": st.column_config.NumberColumn("Faltam", format="%d", width="small"),
            "produtos": st.column_config.NumberColumn("Produtos", format="%d", width="small"),
            "presencas": st.column_config.NumberColumn("Presenças", format="%d", width="small"),
            "situacao_txt": st.column_config.TextColumn("Situação", width="medium"),
        },
    )

    saida = io.StringIO()
    exibir.to_csv(saida, index=False, sep=";", decimal=",", encoding="utf-8")
    st.download_button(
        "Baixar seleção em CSV",
        data="\ufeff" + saida.getvalue(),
        file_name="engajamento_com_o_mej.csv",
        mime="text/csv",
    )

# ---- detalhe de uma EJ ----------------------------------------------------

with st.container(border=True):
    painel("Detalhe de uma EJ", "Situação da meta e produtos de conexão em que apareceu.")

    escolhida = st.selectbox("Empresa Júnior", sorted(selecao["ej"].tolist()), key="detalhe")
    linha = selecao[selecao["ej"] == escolhida].iloc[0]

    detalhe = st.columns(4)
    detalhe[0].metric("Membros", num(linha["membros"]))
    detalhe[1].metric("Engajados", num(linha["engajados"]))
    detalhe[2].metric(
        "% ECM atual",
        pct(linha["atual"] * 100) if pd.notna(linha["atual"]) else "—",
        delta=f"meta de {pct(linha['meta'] * 100, 0)}" if pd.notna(linha["meta"]) else None,
        delta_color="off",
    )
    detalhe[3].metric(
        "Faltam para a meta",
        num(linha["gap"]) if pd.notna(linha["gap"]) else "—",
        delta=SITUACOES[linha["situacao"]]["rotulo"],
        delta_color="off",
    )

    historico = participacoes[participacoes["ej"] == escolhida][["produto", "participantes"]]
    if historico.empty:
        st.info(
            f"**{escolhida}** não aparece em nenhum produto de conexão desta base. "
            "Vale confirmar se houve participação sem registro no Portal BJ antes de "
            "tratar como ausência real."
        )
    else:
        historico = historico.sort_values("participantes", ascending=False)
        st.dataframe(
            historico,
            hide_index=True,
            width="stretch",
            column_config={
                "produto": st.column_config.TextColumn("Produto de conexão"),
                "participantes": st.column_config.NumberColumn("Membros presentes", format="%d"),
            },
        )

# ---- rodapé ---------------------------------------------------------------

st.markdown(
    f"""
    <div class="rodape">
    <b>Como as contas são feitas.</b>
    % ECM atual = membros engajados ÷ membros totais.
    Alcance da meta = % ECM atual ÷ meta da EJ × 100.
    Pessoas que faltam = teto(meta × membros) − membros já engajados, sempre arredondado
    para cima, porque não existe meia pessoa engajada.<br>
    <b>Presenças não são pessoas únicas.</b> A soma de participantes por produto conta a
    mesma pessoa em cada evento que ela frequentou; o ECM conta cada membro uma vez só.
    Por isso as presenças somadas superam o número de engajados.<br>
    <b>Cobertura da rede</b> usa como denominador as {avisos['ejs_rede']} EJs da base,
    incluindo as {avisos['ejs_sem_produto']} que não aparecem em nenhum produto de conexão.
    Para o indicador da federação, só conta a EJ que bate a própria meta de Engajamento
    com o MEJ — presença sem atingir a meta não entra.<br>
    <b>Registro é gargalo.</b> Participação que não foi lançada no Portal BJ não aparece
    aqui e não conta para o indicador.
    </div>
    """,
    unsafe_allow_html=True,
)
