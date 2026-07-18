"""Tela Histórico de Vendas (slide 16)."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.services.clientes import buscar_clientes
from src.services.historico_nf import listar_vendas_por_cliente
from src.ui.formatters import brl, texto_ou_traco


def render_historico(conn) -> None:
    top1, top2 = st.columns([4, 1])
    with top1:
        st.markdown(
            '<p class="orc-title">Histórico de Vendas</p>',
            unsafe_allow_html=True,
        )
        st.caption("Menu → Histórico de Vendas")
    with top2:
        if st.button("← Menu", key="hist_menu"):
            st.session_state.tela = "menu"
            st.rerun()

    st.write(
        "Filtre um cliente cadastrado e veja as vendas da mais recente para a mais antiga, "
        "agrupadas por número de NF."
    )

    termo = st.text_input("Pesquisar cliente (nome ou CNPJ)")
    clientes = buscar_clientes(conn, termo=termo or None, limite=100)
    opcoes = {"(todos os clientes)": None}
    opcoes.update({f"{c['nome']} | {c['cnpj_cpf']}": c["id"] for c in clientes})
    escolha = st.selectbox("Cliente", list(opcoes.keys()))
    cliente_id = opcoes[escolha]

    notas = listar_vendas_por_cliente(
        conn,
        cliente_id=cliente_id,
        termo_cliente=None if cliente_id else (termo or None),
        limite_notas=80,
    )

    if not notas:
        st.warning("Nenhuma venda encontrada para o filtro.")
        return

    for nota in notas:
        titulo = (
            f"NF {nota['numero_nota']} | {nota.get('data_emissao') or '-'} | "
            f"{nota.get('nome_cliente') or '-'} | Total {brl(nota.get('valor_nota'))}"
        )
        with st.expander(titulo):
            st.write(
                f"CNPJ: **{texto_ou_traco(nota.get('cnpj_cpf'))}**"
            )
            itens = nota.get("itens") or []
            if itens:
                df = pd.DataFrame(itens).rename(
                    columns={
                        "codigo_item": "Código",
                        "descricao_item": "Descrição",
                        "unidade": "Und",
                        "quantidade": "Qtd",
                        "valor_unitario": "Valor unit.",
                        "valor_total": "Valor total",
                        "data_emissao": "Data",
                    }
                )
                st.dataframe(df, use_container_width=True, hide_index=True)
