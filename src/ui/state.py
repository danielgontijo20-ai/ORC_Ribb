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
        st.session_state.modo_form = None
    if "memoria_calculo" not in st.session_state:
        st.session_state.memoria_calculo = None
    if "show_dialog" not in st.session_state:
        st.session_state.show_dialog = None
    if "nav_stack" not in st.session_state:
        st.session_state.nav_stack = []
    if "form_seq" not in st.session_state:
        st.session_state.form_seq = 0
    if "proposta_readonly" not in st.session_state:
        st.session_state.proposta_readonly = False
    if "flash_ok" not in st.session_state:
        st.session_state.flash_ok = None

    if "proposta" not in st.session_state:
        st.session_state.proposta = _nova_proposta(cfg)


def bump_form_seq() -> None:
    """Invalida widgets dos formulários (limpa campos de inserção/seleção)."""
    st.session_state.form_seq = int(st.session_state.get("form_seq") or 0) + 1


def _snapshot_tela() -> dict:
    return {
        "tela": st.session_state.get("tela", "menu"),
        "cadastro_tela": st.session_state.get("cadastro_tela", "hub"),
        "modo_form": st.session_state.get("modo_form"),
    }


def ir_para(tela: str, *, cadastro_tela: str | None = None, modo_form=None) -> None:
    atual = _snapshot_tela()
    if atual["tela"] != tela or (
        cadastro_tela is not None and atual["cadastro_tela"] != cadastro_tela
    ):
        st.session_state.nav_stack.append(atual)

    st.session_state.tela = tela
    if cadastro_tela is not None:
        st.session_state.cadastro_tela = cadastro_tela
    if modo_form is not None:
        st.session_state.modo_form = modo_form

    # Ao abrir Novo ORC (exceto clone/consulta já carregados), limpa modo do form
    if tela == "novo_orcamento":
        bump_form_seq()
        st.session_state.modo_form = None

    # Histórico de vendas só após busca explícita
    if tela == "historico":
        st.session_state.hist_resultado = None
        st.session_state.hist_resultado_label = None

    # Histórico de orçamentos: limpa seleção ao entrar
    if tela == "historico_orcamentos":
        st.session_state.hist_orc_lista = None
        st.session_state.hist_orc_detalhe_id = None

    st.rerun()


def flash_sucesso(msg: str) -> None:
    st.session_state.flash_ok = msg


def consumir_flash() -> None:
    msg = st.session_state.get("flash_ok")
    if msg:
        st.success(msg)
        st.session_state.flash_ok = None


def voltar() -> None:
    stack = st.session_state.get("nav_stack") or []
    if not stack:
        st.session_state.tela = "menu"
        st.session_state.cadastro_tela = "hub"
        st.session_state.modo_form = None
        st.rerun()
        return

    anterior = stack.pop()
    st.session_state.nav_stack = stack
    st.session_state.tela = anterior.get("tela", "menu")
    st.session_state.cadastro_tela = anterior.get("cadastro_tela", "hub")
    st.session_state.modo_form = anterior.get("modo_form")
    st.rerun()


def _nova_proposta(cfg: dict) -> dict:
    return {
        "id": None,
        "numero": None,
        "cliente": None,
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
        "status": None,
    }


def reiniciar_proposta(conn) -> None:
    cfg = carregar_config(conn)
    st.session_state.proposta = _nova_proposta(cfg)
    st.session_state.proposta_readonly = False
    st.session_state.modo_form = None
    st.session_state.memoria_calculo = None
    st.session_state.show_dialog = None
    bump_form_seq()


def totais_proposta() -> tuple[float, float, float]:
    itens = st.session_state.proposta.get("itens", [])
    valor = sum(i.get("valor_venda_total", 0) or 0 for i in itens)
    lucro = sum(i.get("lucro_total", 0) or 0 for i in itens)
    frete = sum(i.get("frete_item", 0) or 0 for i in itens)
    return valor, lucro, frete


def media_lucro_pct_proposta() -> float:
    from src.ui.memoria_ui import media_lucro_pct_proporcional

    itens = st.session_state.proposta.get("itens", [])
    return media_lucro_pct_proporcional(itens)
