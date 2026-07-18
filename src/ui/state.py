"""Estado da sessão Streamlit para o novo layout."""

from __future__ import annotations

import streamlit as st

from src.services.configuracoes import carregar_config


def init_state(conn) -> None:
    cfg = carregar_config(conn)

    if "tela" not in st.session_state:
        st.session_state.tela = "menu"
    if "cadastro_tela" not in st.session_state:
        st.session_state.cadastro_tela = "hub"
    if "modo_form" not in st.session_state:
        st.session_state.modo_form = None  # etiqueta | suprimentos | None
    if "memoria_calculo" not in st.session_state:
        st.session_state.memoria_calculo = None
    if "show_dialog" not in st.session_state:
        st.session_state.show_dialog = None

    if "proposta" not in st.session_state:
        st.session_state.proposta = _nova_proposta(cfg)


def _nova_proposta(cfg: dict) -> dict:
    return {
        "numero": None,
        "cliente": None,  # dict id/nome/cnpj_cpf ou avulso
        "solicitante": "",
        "itens": [],
        "validade_proposta": cfg.get("validade_proposta", "15 dias"),
        "prazo_pagamento": cfg.get("prazo_pagamento", "21 dias"),
        "prazo_entrega": cfg.get("prazo_entrega", "5 dias"),
        "frete_tipo": cfg.get("frete_tipo", "CIF"),
        "frete_taxa": "",
        "impostos": cfg.get("impostos", "Inclusos"),
        "informacoes_adicionais": cfg.get(
            "informacoes_adicionais",
            "As quantidades podem sofrer alterações de 10% para mais ou para menos",
        ),
        "orcamentista_nome": cfg.get("orcamentista_nome", ""),
        "orcamentista_cargo": cfg.get("orcamentista_cargo", ""),
        "orcamentista_telefone": cfg.get("orcamentista_telefone", ""),
        "orcamentista_email": cfg.get("orcamentista_email", ""),
    }


def reiniciar_proposta(conn) -> None:
    cfg = carregar_config(conn)
    st.session_state.proposta = _nova_proposta(cfg)
    st.session_state.modo_form = None
    st.session_state.memoria_calculo = None
    st.session_state.show_dialog = None


def totais_proposta() -> tuple[float, float, float]:
    itens = st.session_state.proposta.get("itens", [])
    valor = sum(i.get("valor_venda_total", 0) or 0 for i in itens)
    lucro = sum(i.get("lucro_total", 0) or 0 for i in itens)
    frete = sum(i.get("frete_item", 0) or 0 for i in itens)
    return valor, lucro, frete
