"""Tela Histórico de Vendas (slide 16)."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.db.database import connect
from src.services.clientes import buscar_clientes, contar_clientes, obter_cliente
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
        "Use **Pesquisar cliente** para abrir o popup (como em orçamentos), "
        "ou **Buscar vendas** sem cliente para listar todas (mais recente → mais antiga)."
    )

    # Popup de cliente
    if st.session_state.get("show_dialog") == "hist_cliente":
        _dialog_cliente_hist()

    with st.container(border=True):
        cli = st.session_state.get("hist_cliente")
        if cli:
            st.success(
                f"Cliente selecionado: **{cli.get('nome')}** | {cli.get('cnpj_cpf') or '-'}"
            )
        else:
            st.info("Nenhum cliente selecionado — a busca listará todas as vendas.")

        b1, b2, b3 = st.columns(3)
        with b1:
            if st.button(
                "Pesquisar cliente",
                use_container_width=True,
                type="primary",
                key="hist_btn_pesq_cli",
            ):
                st.session_state.show_dialog = "hist_cliente"
                st.rerun()
        with b2:
            if st.button(
                "Limpar cliente",
                use_container_width=True,
                key="hist_btn_limpar_cli",
                disabled=not cli,
            ):
                st.session_state.hist_cliente = None
                st.rerun()
        with b3:
            buscar = st.button(
                "Buscar vendas",
                type="primary",
                use_container_width=True,
                key="hist_btn_buscar",
            )

        if buscar:
            cliente_id = cli.get("id") if cli else None
            with st.spinner("Buscando vendas..."):
                st.session_state.hist_resultado = listar_vendas_por_cliente(
                    conn,
                    cliente_id=cliente_id,
                    termo_cliente=None,
                    limite_notas=500,
                )
            if cliente_id and cli:
                st.session_state.hist_resultado_label = (
                    f"{cli.get('nome')} | {cli.get('cnpj_cpf') or '-'}"
                )
            else:
                st.session_state.hist_resultado_label = (
                    "todas as vendas (mais recente → antiga)"
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


def _dismiss_hist_dialog() -> None:
    st.session_state.show_dialog = None


@st.dialog("Selecionar cliente", on_dismiss=_dismiss_hist_dialog)
def _dialog_cliente_hist() -> None:
    termo = st.text_input("Pesquisar por CNPJ ou Nome", key="dlg_hist_cli_termo")
    with connect() as conn:
        total = contar_clientes(conn, termo=termo or None)
        clientes = buscar_clientes(conn, termo=termo or None, limite=None)
        st.caption(
            f"{total} cliente(s) encontrado(s) no banco — clique na linha para selecionar"
        )
        if not clientes:
            st.warning("Nenhum cliente encontrado.")
        else:
            df = pd.DataFrame([dict(c) for c in clientes])[
                ["cnpj_cpf", "nome", "uf"]
            ].rename(columns={"cnpj_cpf": "CNPJ", "nome": "Nome", "uf": "UF"})
            idx = dataframe_selecionavel(df, key="dlg_hist_cli_grid", height=320)
            if idx is not None:
                st.success(
                    f"Selecionado: **{clientes[idx]['nome']}** | {clientes[idx]['cnpj_cpf']}"
                )
            else:
                st.info("Clique em uma linha da grade para selecionar o cliente.")

            if st.button("Confirmar", type="primary", key="dlg_hist_cli_ok"):
                if idx is None:
                    st.error("Clique em um cliente na grade antes de confirmar.")
                else:
                    with connect() as conn2:
                        cli = obter_cliente(conn2, int(clientes[idx]["id"]))
                    st.session_state.hist_cliente = dict(cli)
                    st.session_state.show_dialog = None
                    st.rerun()
    if st.button("Fechar", key="dlg_hist_cli_fechar"):
        st.session_state.show_dialog = None
        st.rerun()
