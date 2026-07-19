"""Tela menu principal (slide 1)."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from src.services.configuracoes import carregar_config
from src.ui.state import ir_para, reiniciar_proposta


def render_menu(conn) -> None:
    cfg = carregar_config(conn)
    st.markdown('<div class="orc-top-spacer"></div>', unsafe_allow_html=True)
    st.markdown('<p class="orc-title">ORC_Ribb</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="orc-sub">Menu principal — elabore orçamentos, gerencie cadastros e consulte o histórico.</p>',
        unsafe_allow_html=True,
    )

    # Topo alinhado: logo e botão NOVO ORC começam na mesma linha
    try:
        left, right = st.columns([1, 2], gap="large", vertical_alignment="top")
    except TypeError:
        left, right = st.columns([1, 2], gap="large")

    with left:
        st.markdown('<div class="menu-btn">', unsafe_allow_html=True)
        if st.button("NOVO ORC", use_container_width=True, type="primary"):
            reiniciar_proposta(conn)
            ir_para("novo_orcamento")
        if st.button("CADASTROS", use_container_width=True):
            ir_para("cadastros", cadastro_tela="hub")
        if st.button("HISTÓRICO DE ORÇAMENTOS", use_container_width=True):
            ir_para("historico_orcamentos")
        if st.button("HISTÓRICO DE VENDAS", use_container_width=True):
            ir_para("historico")
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        logo = cfg.get("logo_master") or ""
        st.markdown(
            '<div class="menu-logo-host"><div class="menu-logo">',
            unsafe_allow_html=True,
        )
        if logo and Path(logo).exists():
            st.image(logo, use_container_width=True)
        else:
            st.markdown(
                """
                #### Logo Master
                Faça upload em **Cadastros → Valores Nativos**.

                Tamanho sugerido: **1200 × 330 px** (proporção ~8,0 × 2,2).
                """
            )
            empresa = cfg.get("empresa_nome") or "Sua empresa"
            st.info(
                f"Cabeçalho da proposta usará: **{empresa}** "
                f"| CNPJ: **{cfg.get('empresa_cnpj') or '(preencher)'}**"
            )
        st.markdown("</div></div>", unsafe_allow_html=True)
