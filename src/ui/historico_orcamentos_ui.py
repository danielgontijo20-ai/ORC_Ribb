"""Histórico de orçamentos — consultar (somente leitura) e clonar."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.services.orcamentos import (
    buscar_orcamentos,
    clonar_para_novo,
    obter_orcamento,
    orcamento_para_proposta,
)
from src.ui.formatters import brl
from src.ui.state import bump_form_seq, flash_sucesso, ir_para, voltar


def render_historico_orcamentos(conn) -> None:
    top1, top2 = st.columns([4, 1])
    with top1:
        st.markdown(
            '<p class="orc-title">Histórico de Orçamentos</p>',
            unsafe_allow_html=True,
        )
        st.caption("Consulte orçamentos realizados. Histórico é somente leitura — use Clonar para reaproveitar.")
    with top2:
        if st.button("← Voltar", key="hist_orc_voltar"):
            voltar()

    with st.container(border=True):
        termo = st.text_input(
            "Buscar por número do orçamento ou nome do cliente",
            placeholder="Ex.: ORC-00005 ou ALIMENTO DIAMANTE",
            key="hist_orc_termo",
        )
        b1, b2, _ = st.columns([1, 1, 2])
        with b1:
            buscar = st.button("Buscar", type="primary", use_container_width=True, key="hist_orc_buscar")
        with b2:
            limpar = st.button("Limpar", use_container_width=True, key="hist_orc_limpar")

        if limpar:
            st.session_state.hist_orc_termo = ""
            st.session_state.hist_orc_lista = None
            st.session_state.hist_orc_detalhe_id = None
            st.rerun()

        if buscar or st.session_state.get("hist_orc_lista") is not None:
            with st.spinner("Buscando orçamentos..."):
                rows = buscar_orcamentos(conn, termo=termo or None)
            st.session_state.hist_orc_lista = [dict(r) for r in rows]

        lista = st.session_state.get("hist_orc_lista")
        if lista is None:
            st.info("Digite um termo (ou deixe em branco) e clique em **Buscar**.")
            return

        if not lista:
            st.warning("Nenhum orçamento encontrado.")
            return

        df = pd.DataFrame(
            [
                {
                    "ID": r["id"],
                    "Número": r.get("numero") or "-",
                    "Cliente": r.get("cliente_nome") or "-",
                    "Status": r.get("status") or "-",
                    "Valor total": brl(r.get("valor_total") or 0),
                    "Atualizado em": r.get("atualizado_em") or "-",
                }
                for r in lista
            ]
        )
        st.dataframe(df, use_container_width=True, hide_index=True, height=360)

        opcoes = {
            f"{r.get('numero') or 's/n'} — {r.get('cliente_nome') or '-'} (#{r['id']})": r["id"]
            for r in lista
        }
        escolha = st.selectbox(
            "Selecione um orçamento",
            ["(selecione)"] + list(opcoes.keys()),
            key="hist_orc_escolha",
        )

        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("Abrir (somente leitura)", type="primary", use_container_width=True):
                if escolha == "(selecione)":
                    st.error("Selecione um orçamento.")
                else:
                    _abrir_readonly(conn, opcoes[escolha])
        with c2:
            if st.button("Clonar como novo orçamento", use_container_width=True):
                if escolha == "(selecione)":
                    st.error("Selecione um orçamento.")
                else:
                    _clonar(conn, opcoes[escolha])
        with c3:
            if st.button("Ver detalhes aqui", use_container_width=True):
                if escolha == "(selecione)":
                    st.error("Selecione um orçamento.")
                else:
                    st.session_state.hist_orc_detalhe_id = opcoes[escolha]
                    st.rerun()

    detalhe_id = st.session_state.get("hist_orc_detalhe_id")
    if detalhe_id:
        _painel_detalhe(conn, detalhe_id)


def _abrir_readonly(conn, orcamento_id: int) -> None:
    with st.spinner("Carregando orçamento..."):
        orc = obter_orcamento(conn, orcamento_id)
    if not orc:
        st.error("Orçamento não encontrado.")
        return
    st.session_state.proposta = orcamento_para_proposta(orc)
    st.session_state.proposta_readonly = True
    st.session_state.modo_form = None
    bump_form_seq()
    flash_sucesso(f"Orçamento {orc.get('numero') or orcamento_id} aberto em modo consulta.")
    ir_para("novo_orcamento")


def _clonar(conn, orcamento_id: int) -> None:
    with st.spinner("Clonando orçamento..."):
        orc = obter_orcamento(conn, orcamento_id)
    if not orc:
        st.error("Orçamento não encontrado.")
        return
    st.session_state.proposta = clonar_para_novo(orc)
    st.session_state.proposta_readonly = False
    st.session_state.modo_form = None
    bump_form_seq()
    flash_sucesso(
        f"Clone criado a partir de {orc.get('numero') or orcamento_id}. "
        "Edite e salve como novo orçamento."
    )
    ir_para("novo_orcamento")


def _painel_detalhe(conn, orcamento_id: int) -> None:
    orc = obter_orcamento(conn, orcamento_id)
    if not orc:
        return
    with st.container(border=True):
        st.markdown(f"#### Detalhe — {orc.get('numero') or orcamento_id}")
        st.markdown(
            f"**Cliente:** {orc.get('cliente_nome') or '-'}  \n"
            f"**CNPJ:** {orc.get('cliente_doc') or '-'}  \n"
            f"**Status:** {orc.get('status')}  \n"
            f"**Valor total:** {brl(orc.get('valor_total') or 0)}  \n"
            f"**Lucro:** {brl(orc.get('lucro_total') or 0)}  \n"
            f"**Criado em:** {orc.get('criado_em')}  \n"
            f"**Atualizado em:** {orc.get('atualizado_em')}"
        )
        itens = orc.get("itens") or []
        if itens:
            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            "N°": f"{i+1:02d}",
                            "Descrição": it.get("descricao"),
                            "Und": it.get("unidade"),
                            "Qtd": it.get("quantidade"),
                            "Preço Unit.": it.get("preco_unitario"),
                            "Valor total": it.get("preco_total"),
                        }
                        for i, it in enumerate(itens)
                    ]
                ),
                use_container_width=True,
                hide_index=True,
            )
        c1, c2, _ = st.columns(3)
        with c1:
            if st.button("Abrir este (somente leitura)", key="det_abrir"):
                _abrir_readonly(conn, orcamento_id)
        with c2:
            if st.button("Clonar este", key="det_clonar"):
                _clonar(conn, orcamento_id)
