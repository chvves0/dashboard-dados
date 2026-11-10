    empresas["gap"] = empresas["gap_calc"].combine_first(
        pd.to_numeric(empresas.get("gap", pd.Series(dtype=float)), errors="coerce")
    )
    empresas = empresas.drop(columns=["gap_calc"], errors="ignore")

    # ---- Classificar situação de cada EJ ---------------------------------
    empresas["situacao"] = empresas.apply(
        lambda l: faixa_alcance(l["alcance"], l["membros"]), axis=1
    )
    empresas["cluster"]  = empresas["cluster"].fillna(0)

    avisos = {
        "participacoes":   len(participacoes),
        "ejs_rede":        len(empresas),
        "ejs_sem_produto": int((empresas["produtos"] == 0).sum()),
        "ejs_sem_membros": int((empresas["membros"].fillna(0) <= 0).sum()),
    }

    return (
        participacoes,
        empresas.sort_values("ej").reset_index(drop=True),
        avisos,
    )


# --------------------------------------------------------------------------
# Componentes visuais
# --------------------------------------------------------------------------

def barra_situacao(empresas: pd.DataFrame) -> go.Figure:
    total  = max(len(empresas), 1)
    figura = go.Figure()
    for chave in ORDEM_SIT:
        quantidade = int((empresas["situacao"] == chave).sum())
        if quantidade == 0:
            continue
        figura.add_bar(
            x=[quantidade], y=["EJs"], orientation="h",
            name=SITUACOES[chave]["rotulo"],
            marker_color=SITUACOES[chave]["cor"],
            text=[str(quantidade)],
            textposition="inside", insidetextanchor="middle",
            textfont=dict(color="#fff", size=13, family="Poppins"),
            hovertemplate=(
                f"<b>{SITUACOES[chave]['rotulo']}</b><br>"
                f"{quantidade} EJs ({quantidade / total * 100:.1f}%)<extra></extra>"
            ),
        )
    figura.update_layout(
        barmode="stack", height=130,
        margin=dict(l=0, r=0, t=6, b=0),
        showlegend=True,
        legend=dict(orientation="h", y=-0.55, x=0, font=dict(size=11)),
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
    )
    return figura


def barras_horizontais(rotulos, valores, cores, sufixo="", altura=None) -> go.Figure:
    figura = go.Figure(
        go.Bar(
            x=valores, y=rotulos, orientation="h",
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
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False, bargap=0.32,
    )
    return figura


def painel(titulo: str, dica: str) -> None:
    st.markdown(
        f"<div style='margin-bottom:6px'>"
        f"<h3 style='font-family:Poppins;font-size:16px;margin:0;color:{LINHA}'>"
        f"{titulo}</h3>"
        f"<p style='font-size:12.5px;color:{MUDO};margin:2px 0 10px'>{dica}</p></div>",
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------
# Cabeçalho
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

# --------------------------------------------------------------------------
# Sidebar — upload e localização dos arquivos
# --------------------------------------------------------------------------

# Reserva o primeiro espaço da sidebar para a data, preenchida após localizar a base.
slot_data_atualizacao = st.sidebar.empty()

with st.sidebar:
    st.markdown("### Base de dados")
    enviado_produtos = st.file_uploader(
        "Produtos de Conexão (CSV)",
        type=["csv"],
        help="Substitui o arquivo do repositório só nesta sessão.",
        key="up_produtos",
    )
    enviado_rede = st.file_uploader(
        "Dados Gerais da Rede (CSV)",
        type=["csv"],
        help="Substitui o arquivo do repositório só nesta sessão.",
        key="up_rede",
    )

fonte_prod_repo, origem_prod = _localizar(NOMES_PRODUTOS, URL_PRODUTOS)
fonte_rede_repo, origem_rede = _localizar(NOMES_GERAIS,   URL_DADOS_GERAIS)

# Decide fonte de cada arquivo: upload > repositório
if enviado_produtos is not None:
    fonte_prod, orig_prod, ver_prod = (
        enviado_produtos,
        f"arquivo enviado · {enviado_produtos.name}",
        enviado_produtos.name,
    )
elif fonte_prod_repo is not None:
    fonte_prod  = fonte_prod_repo
    orig_prod   = origem_prod
    ver_prod    = _versao_local(fonte_prod_repo)
else:
    st.error(
        "Não encontrei **Produtos_de_Conexão.csv** no repositório. "
        "Commite-o ao lado do `app.py` (ou em `/dados`) ou faça upload acima."
    )
    st.stop()

if enviado_rede is not None:
    fonte_rede, orig_rede, ver_rede = (
        enviado_rede,
        f"arquivo enviado · {enviado_rede.name}",
        enviado_rede.name,
    )
elif fonte_rede_repo is not None:
    fonte_rede = fonte_rede_repo
    orig_rede  = origem_rede
    ver_rede   = _versao_local(fonte_rede_repo)
else:
    st.error(
        "Não encontrei **Dados_Gerais_da_Rede.csv** no repositório. "
        "Commite-o ao lado do `app.py` (ou em `/dados`) ou faça upload acima."
    )
    st.stop()

try:
    data_atualizacao = _ler_data_atualizacao(fonte_rede)
except Exception:
    data_atualizacao = "Não informada"

slot_data_atualizacao.markdown(
    f"""
    <div style="
        padding: 0 0 14px 0;
        margin-bottom: 14px;
        border-bottom: 1px solid {LINHA};
        line-height: 1.35;
    ">
        <div style="
            color: {MUDO};
            font-size: 11px;
            font-weight: 600;
            letter-spacing: .04em;
            text-transform: uppercase;
        ">Última atualização do dashboard</div>
        <div style="
            color: {TEXTO};
            font-family: Poppins, sans-serif;
