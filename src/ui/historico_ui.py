"""Tela Histórico de Vendas (slide 16)."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.services.clientes import buscar_clientes, contar_clientes
from src.services.historico_nf import listar_vendas_por_cliente
from src.ui.formatters import brl, texto_ou_traco
from src.ui.state import voltar


def render_historico(conn) -> None:
    top1, top2 = st.columns([4, 1])
    with top1:
        st.markdown(
            '<p class="orc-title">Histórico de Vendas</p>',
            unsafe_allow_html=True,
        )
        st.caption("Menu → Histórico de Vendas")
    with top2:
        if st.button("← Voltar", key="hist_voltar"):
            voltar()

    st.write(
        "Pesquise um cliente e clique em **Buscar vendas**. "
        "A tela não carrega o histórico automaticamente."
    )

    with st.container(border=True):
        termo = st.text_input(
            "Pesquisar cliente (nome ou CNPJ)",
            placeholder="Digite parte do nome ou CNPJ",
            key="hist_termo",
        )
        c1, c2 = st.columns([3, 1])
        with c1:
            # Lista de clientes só para ajudar a escolher — sem carregar vendas ainda
            if termo and termo.strip():
                total = contar_clientes(conn, termo=termo.strip())
                clientes = buscar_clientes(conn, termo=termo.strip(), limite=None)
                st.caption(f"{total} cliente(s) encontrado(s) na busca")
                opcoes = {
                    f"{c['nome']} | {c['cnpj_cpf']}": c["id"] for c in clientes
                }
                if opcoes:
                    escolha = st.selectbox(
                        "Selecione o cliente",
                        list(opcoes.keys()),
                        key="hist_cliente_sel",
                    )
                    cliente_id = opcoes[escolha]
                else:
                    escolha = None
                    cliente_id = None
                    st.warning("Nenhum cliente encontrado para este termo.")
            else:
                cliente_id = None
                st.info("Digite um termo de pesquisa para localizar o cliente.")
        with c2:
            st.write("")
            st.write("")
            buscar = st.button("Buscar vendas", type="primary", use_container_width=True)

        if buscar:
            if not (termo and termo.strip()):
                st.session_state.hist_resultado = None
                st.error("Informe um termo de pesquisa antes de buscar.")
            elif not cliente_id:
                st.session_state.hist_resultado = None
                st.error("Selecione um cliente na lista.")
            else:
                st.session_state.hist_resultado = listar_vendas_por_cliente(
                    conn,
                    cliente_id=cliente_id,
                    termo_cliente=None,
                    limite_notas=200,
                )
                st.session_state.hist_resultado_label = escolha

    # Só mostra vendas depois de uma busca explícita
    notas = st.session_state.get("hist_resultado")
    if notas is None:
        st.caption("Nenhuma busca realizada ainda.")
        return

    label = st.session_state.get("hist_resultado_label") or "cliente"
    st.markdown(f"#### Resultado — {label}")

    if not notas:
        st.warning("Nenhuma venda encontrada para este cliente.")
        return

    for nota in notas:
        titulo = (
            f"NF {nota['numero_nota']} | {nota.get('data_emissao') or '-'} | "
            f"{nota.get('nome_cliente') or '-'} | Total {brl(nota.get('valor_nota'))}"
        )
        with st.expander(titulo):
            st.write(f"CNPJ: **{texto_ou_traco(nota.get('cnpj_cpf'))}**")
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
