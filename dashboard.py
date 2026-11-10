# --------------------------------------------------------------------------
# Tabela de EJs
# --------------------------------------------------------------------------

st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

with st.container(border=True):
    painel(
        "EJs da seleção",
        "Clique no cabeçalho para reordenar. O alcance é o quanto a EJ já cumpriu da "
        "própria meta.",
    )

    tabela = selecao.copy()
    tabela["situacao_txt"] = tabela["situacao"].map(lambda s: SITUACOES[s]["rotulo"])
    tabela["cluster_txt"]  = tabela["cluster"].map(
        lambda c: f"C{int(c)}" if c > 0 else "—"
    )
    tabela["meta_pct"]  = tabela["meta"]  * 100
    tabela["atual_pct"] = tabela["atual"] * 100

    exibir = tabela[[
        "ej", "cluster_txt", "membros", "engajados", "atual_pct", "meta_pct",
        "alcance", "gap", "produtos", "presencas", "situacao_txt",
    ]].sort_values("gap", ascending=False, na_position="last")

    st.dataframe(
        exibir,
        hide_index=True,
        width="stretch",
        height=520,
        column_config={
            "ej":           st.column_config.TextColumn("Empresa Júnior",  width="large"),
            "cluster_txt":  st.column_config.TextColumn("Cluster",         width="small"),
            "membros":      st.column_config.NumberColumn("Membros",       format="%d", width="small"),
            "engajados":    st.column_config.NumberColumn("Engajados",     format="%d", width="small"),
            "atual_pct":    st.column_config.NumberColumn("% ECM atual",   format="%.1f%%"),
            "meta_pct":     st.column_config.NumberColumn("Meta",          format="%.0f%%", width="small"),
            "alcance":      st.column_config.ProgressColumn(
                "Alcance da meta", format="%.0f%%", min_value=0, max_value=150
            ),
            "gap":          st.column_config.NumberColumn("Faltam",        format="%d", width="small"),
            "produtos":     st.column_config.NumberColumn("Produtos",      format="%d", width="small"),
            "presencas":    st.column_config.NumberColumn("Presenças",     format="%d", width="small"),
            "situacao_txt": st.column_config.TextColumn("Situação",        width="medium"),
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

# --------------------------------------------------------------------------
# Detalhe de uma EJ
# --------------------------------------------------------------------------

with st.container(border=True):
    painel("Detalhe de uma EJ", "Situação da meta e produtos de conexão em que apareceu.")

    escolhida = st.selectbox(
        "Empresa Júnior", sorted(selecao["ej"].tolist()), key="detalhe"
    )
    linha = selecao[selecao["ej"] == escolhida].iloc[0]

    detalhe = st.columns(4)
    detalhe[0].metric("Membros",  num(linha["membros"]))
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
                "produto":       st.column_config.TextColumn("Produto de conexão"),
                "participantes": st.column_config.NumberColumn("Membros presentes", format="%d"),
            },
        )

# --------------------------------------------------------------------------
# Rodapé
# --------------------------------------------------------------------------

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
    <b>Meta da FEJERS.</b> O bloco da federação conta as EJs com ECM individual de
    {pct(META_FED_PISO * 100, 0)} ou mais e compara com o alvo de
    {math.ceil(META_FED_SHARE * avisos['ejs_rede'] - 1e-9)} EJs
    ({pct(META_FED_SHARE * 100, 0)} das {avisos['ejs_rede']}). Presença sem chegar ao
    piso não entra. O critério alternativo — EJ que bate a própria meta — aparece como
    contraponto no mesmo bloco.<br>
    <b>Registro é gargalo.</b> Participação que não foi lançada no Portal BJ não aparece
