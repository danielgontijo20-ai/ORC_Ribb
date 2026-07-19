"""Tela Histórico de Vendas (slide 16)."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.services.clientes import buscar_clientes, contar_clientes
from src.services.historico_nf import listar_vendas_por_cliente
from src.ui.formatters import brl, texto_ou_traco
from src.ui.grid_select import dataframe_selecionavel
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
        "Opcional: pesquise um cliente e **clique na linha** da grade. "
        "Em **Buscar vendas** sem filtro, lista todas as vendas (mais recente → mais antiga)."
    )

    with st.container(border=True):
        termo = st.text_input(
            "Pesquisar cliente (nome ou CNPJ)",
            placeholder="Deixe vazio para listar todas as vendas",
            key="hist_termo",
        )
        cliente_id = None
        escolha_label = None

        if termo and termo.strip():
            total = contar_clientes(conn, termo=termo.strip())
            clientes = buscar_clientes(conn, termo=termo.strip(), limite=None)
            st.caption(f"{total} cliente(s) encontrado(s) — clique na linha para selecionar")
            if clientes:
                df = pd.DataFrame([dict(c) for c in clientes])[
                    ["cnpj_cpf", "nome", "uf"]
                ].rename(columns={"cnpj_cpf": "CNPJ", "nome": "Nome", "uf": "UF"})
                idx = dataframe_selecionavel(df, key="hist_cli_grid", height=280)
                if idx is not None:
                    cliente_id = int(clientes[idx]["id"])
                    escolha_label = (
                        f"{clientes[idx]['nome']} | {clientes[idx]['cnpj_cpf']}"
                    )
                    st.success(f"Selecionado: **{escolha_label}**")
                else:
                    st.info("Clique em um cliente na grade, ou busque sem filtro (todas as vendas).")
            else:
                st.warning("Nenhum cliente encontrado para este termo.")

        buscar = st.button("Buscar vendas", type="primary", use_container_width=True)

        if buscar:
            if termo and termo.strip() and not cliente_id:
                st.session_state.hist_resultado = None
                st.error("Clique em um cliente na grade, ou limpe a pesquisa para listar todas.")
            else:
                with st.spinner("Buscando vendas..."):
                    st.session_state.hist_resultado = listar_vendas_por_cliente(
                        conn,
                        cliente_id=cliente_id,
                        termo_cliente=None,
                        limite_notas=500,
                    )
                st.session_state.hist_resultado_label = (
                    escolha_label if cliente_id else "todas as vendas (mais recente → antiga)"
                )

    notas = st.session_state.get("hist_resultado")
    if notas is None:
        st.caption("Nenhuma busca realizada ainda.")
        return

    label = st.session_state.get("hist_resultado_label") or "cliente"
    st.markdown(f"#### Resultado — {label}")

    if not notas:
        st.warning("Nenhuma venda encontrada.")
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
