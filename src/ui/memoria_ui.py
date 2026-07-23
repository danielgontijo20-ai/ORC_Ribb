"""Exibição da memória de cálculo em tabelas (Streamlit)."""

from __future__ import annotations

import html

import streamlit as st

from src.services.memoria_format import (
    _LABELS_CALC,
    _LABELS_PARAM,
    _dict_para_linhas,
    _resultado_para_dict,
    coletar_secoes_memoria,
    lucro_total_itens,
    media_lucro_pct_proporcional,
    resumo_memoria,
)
from src.ui.formatters import brl, pct

# Reexporta helpers usados por outros módulos Streamlit
__all__ = [
    "coletar_secoes_memoria",
    "lucro_total_itens",
    "media_lucro_pct_proporcional",
    "render_memoria_completa",
    "render_memorias_itens",
    "render_tabela_memoria",
    "resumo_memoria",
]


def _tabela_html_str(linhas: list[tuple[str, str]], *, caption: str) -> str:
    """HTML da tabela com contraste alto."""
    if not linhas:
        return ""
    rows_html = []
    for i, (campo, valor) in enumerate(linhas):
        zebra = "mem-row-even" if i % 2 == 0 else "mem-row-odd"
        rows_html.append(
            f'<tr class="{zebra}"><td class="mem-campo">{html.escape(str(campo))}</td>'
            f'<td class="mem-valor">{html.escape(str(valor))}</td></tr>'
        )
    return (
        f'<div class="mem-table-wrap">'
        f'<div class="mem-table-caption">{html.escape(caption)}</div>'
        f'<table class="mem-table">'
        f"<thead><tr><th>Campo</th><th>Valor</th></tr></thead>"
        f"<tbody>{''.join(rows_html)}</tbody>"
        f"</table></div>"
    )


def _resumo_topo(itens: list[dict], rascunho: dict | None = None) -> None:
    """Lucro total e média de margens no topo da memória."""
    lucro, media = resumo_memoria(itens, rascunho)
    m1, m2 = st.columns(2)
    m1.metric("Lucro total", brl(lucro))
    m2.metric("Média de margens", pct(media))
    st.divider()


def render_tabela_memoria(
    *,
    titulo: str,
    params: dict | None,
    calculo: dict | None,
    key_prefix: str,
) -> None:
    """Uma memória: título + parâmetros e resultado lado a lado."""
    del key_prefix  # HTML tables não precisam de key Streamlit
    st.markdown(
        f'<div class="mem-item-title">{html.escape(titulo)}</div>',
        unsafe_allow_html=True,
    )
    params_linhas = _dict_para_linhas(params or {}, _LABELS_PARAM) if params else []
    calc_linhas = _dict_para_linhas(calculo or {}, _LABELS_CALC) if calculo else []
    if not params_linhas and not calc_linhas:
        st.info("Sem dados de memória para este item.")
        st.markdown('<div class="mem-sep"></div>', unsafe_allow_html=True)
        return

    left = _tabela_html_str(params_linhas, caption="Parâmetros de entrada")
    right = _tabela_html_str(calc_linhas, caption="Resultado do cálculo")
    if not left:
        left = '<div class="mem-table-wrap mem-table-empty">Sem parâmetros</div>'
    if not right:
        right = '<div class="mem-table-wrap mem-table-empty">Sem resultado</div>'

    st.markdown(
        f'<div class="mem-side-by-side">'
        f'<div class="mem-side-col">{left}</div>'
        f'<div class="mem-side-col">{right}</div>'
        f"</div>"
        f'<div class="mem-sep"></div>',
        unsafe_allow_html=True,
    )


def render_memorias_itens(itens: list[dict], *, key_prefix: str = "mem") -> None:
    """Empilha uma tabela de memória por item da proposta."""
    if not itens:
        st.info("Nenhum item na proposta — memória de cálculo vazia.")
        return
    for i, it in enumerate(itens):
        tipo = (it.get("tipo_item") or "item").capitalize()
        desc = it.get("descricao") or "(sem descrição)"
        titulo = f"Item {i + 1:02d} — {tipo}: {desc}"
        params = it.get("parametros") or {}
        calculo = it.get("calculo") or {}
        render_tabela_memoria(
            titulo=titulo,
            params=params,
            calculo=calculo if isinstance(calculo, dict) else {},
            key_prefix=f"{key_prefix}_{i}",
        )


def render_memoria_completa(
    *,
    itens: list[dict],
    rascunho: dict | None = None,
) -> None:
    """
    Exibe memória completa: resumo no topo + cálculo atual (se houver) + itens.
    """
    _resumo_topo(itens or [], rascunho)

    if rascunho:
        tipo = (rascunho.get("tipo") or "item").capitalize()
        params = rascunho.get("params") or {}
        desc = (
            params.get("Descrição")
            or params.get("Matéria-prima")
            or params.get("Dimensão")
            or "em elaboração"
        )
        calculo = _resultado_para_dict(rascunho.get("resultado"))
        render_tabela_memoria(
            titulo=f"Cálculo atual (não inserido) — {tipo}: {desc}",
            params=params,
            calculo=calculo,
            key_prefix="mem_draft",
        )

    if itens:
        st.markdown("#### Itens incluídos na proposta")
        render_memorias_itens(itens, key_prefix="mem_item")
    elif not rascunho:
        st.warning("Sem memória de cálculo.")
