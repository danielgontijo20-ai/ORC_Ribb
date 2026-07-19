"""Exibição da memória de cálculo em tabelas."""

from __future__ import annotations

import html
from typing import Any

import streamlit as st

from src.services.calculos_orcamento import ResultadoEtiqueta, ResultadoSuprimentos
from src.ui.formatters import brl


# Rótulos amigáveis dos campos de cálculo
_LABELS_CALC = {
    "area_faca": "Área da faca (m²)",
    "m2_rolo": "m² por rolo",
    "m2_total": "m² total",
    "custo_materia_rolo": "Custo matéria / rolo",
    "custo_tubete": "Custo tubete",
    "custo_caixas_total": "Custo caixas (total)",
    "custo_caixas_por_rolo": "Custo caixas / rolo",
    "custo_perda": "Custo perda",
    "custo_sem_frete": "Custo sem frete",
    "frete_por_rolo": "Frete / rolo",
    "custo_com_frete": "Custo com frete",
    "lucro_por_rolo": "Lucro / rolo",
    "lucro_total": "Lucro total",
    "preco_sem_imposto": "Preço sem imposto",
    "preco_com_imposto": "Preço com imposto (unitário)",
    "valor_venda_total": "Valor de venda total",
    "frete_unitario": "Frete unitário",
    "difal_unitario": "Difal unitário",
    "custo_unitario": "Custo unitário",
    "lucro_unitario": "Lucro unitário",
}

_LABELS_PARAM = {
    "Dimensão": "Dimensão",
    "Qtd etiquetas/rolo": "Qtd etiquetas/rolo",
    "Nº rolos": "Nº rolos",
    "Matéria-prima": "Matéria-prima",
    "Tubete": "Tubete",
    "Caixa": "Caixa",
    "Qtd caixas": "Qtd caixas",
    "Perda": "Perda",
    "Frete": "Frete",
    "Lucro": "Lucro (%)",
    "Descrição": "Descrição",
    "Custo": "Custo",
    "Quantidade": "Quantidade",
    "Difal": "Difal",
    "faca": "Dimensão / faca",
    "materia": "Matéria-prima",
    "tubete": "Tubete",
    "caixa": "Caixa",
    "qtd_etq": "Qtd etiquetas/rolo",
    "perda": "Perda",
    "lucro": "Lucro (fator)",
    "custo": "Custo",
    "difal": "Difal",
}


def _fmt_valor(chave: str, valor: Any) -> str:
    if valor is None:
        return "-"
    if isinstance(valor, bool):
        return "SIM" if valor else "NÃO"
    if isinstance(valor, (int, float)):
        # percentuais / fatores de lucro e perda pequenos
        if chave in ("Lucro", "lucro", "Perda", "perda") and abs(float(valor)) <= 5:
            return f"{float(valor) * 100:.2f}%".replace(".", ",")
        # valores monetários e áreas
        if any(
            x in chave.lower()
            for x in ("custo", "preco", "preço", "frete", "lucro", "valor", "difal")
        ):
            return brl(float(valor))
        if "m2" in chave.lower() or "area" in chave.lower() or "área" in chave.lower():
            return f"{float(valor):.6f}".replace(".", ",")
        if float(valor).is_integer():
            return f"{int(valor)}"
        return f"{float(valor):,.4f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return str(valor)


def _dict_para_linhas(dados: dict, labels: dict[str, str]) -> list[tuple[str, str]]:
    linhas = []
    for k, v in (dados or {}).items():
        label = labels.get(k, k.replace("_", " ").capitalize())
        linhas.append((label, _fmt_valor(k, v)))
    return linhas


def _tabela_html(linhas: list[tuple[str, str]], *, caption: str) -> None:
    """Tabela HTML com contraste alto (zebra + borda forte)."""
    if not linhas:
        return
    rows_html = []
    for i, (campo, valor) in enumerate(linhas):
        zebra = "mem-row-even" if i % 2 == 0 else "mem-row-odd"
        rows_html.append(
            f'<tr class="{zebra}"><td class="mem-campo">{html.escape(str(campo))}</td>'
            f'<td class="mem-valor">{html.escape(str(valor))}</td></tr>'
        )
    st.markdown(
        f"""
        <div class="mem-table-wrap">
          <div class="mem-table-caption">{html.escape(caption)}</div>
          <table class="mem-table">
            <thead><tr><th>Campo</th><th>Valor</th></tr></thead>
            <tbody>{''.join(rows_html)}</tbody>
          </table>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _resultado_para_dict(resultado) -> dict:
    if isinstance(resultado, (ResultadoEtiqueta, ResultadoSuprimentos)):
        return resultado.to_dict()
    if isinstance(resultado, dict):
        return resultado
    return {}


def lucro_total_itens(itens: list[dict]) -> float:
    return sum(float(it.get("lucro_total") or 0) for it in (itens or []))


def media_lucro_pct_proporcional(itens: list[dict]) -> float:
    """
    Média de lucro (%) ponderada pelo valor de venda de cada item.
    Usa o fator em parametros['lucro'] quando existir; senão lucro_total/valor.
    """
    soma_peso = 0.0
    soma_pond = 0.0
    for it in itens or []:
        valor = float(it.get("valor_venda_total") or 0)
        if valor <= 0:
            continue
        params = it.get("parametros") or {}
        if params.get("lucro") is not None:
            try:
                pct = float(params["lucro"]) * 100.0
            except (TypeError, ValueError):
                lucro = float(it.get("lucro_total") or 0)
                pct = (lucro / valor) * 100.0
        else:
            lucro = float(it.get("lucro_total") or 0)
            pct = (lucro / valor) * 100.0
        soma_pond += pct * valor
        soma_peso += valor
    if soma_peso <= 0:
        return 0.0
    return soma_pond / soma_peso


def _resumo_topo(itens: list[dict], rascunho: dict | None = None) -> None:
    """Lucro total e média de margens no topo da memória."""
    lucro = lucro_total_itens(itens)
    media = media_lucro_pct_proporcional(itens)

    # Inclui rascunho (cálculo atual) se ainda não inserido
    if rascunho and rascunho.get("resultado") is not None:
        calc = _resultado_para_dict(rascunho.get("resultado"))
        lucro_r = float(calc.get("lucro_total") or 0)
        valor_r = float(calc.get("valor_venda_total") or 0)
        params = rascunho.get("params") or {}
        if params.get("Lucro") is not None:
            try:
                pct_r = float(params["Lucro"]) * 100.0
            except (TypeError, ValueError):
                pct_r = (lucro_r / valor_r * 100.0) if valor_r else 0.0
        elif params.get("lucro") is not None:
            try:
                pct_r = float(params["lucro"]) * 100.0
            except (TypeError, ValueError):
                pct_r = (lucro_r / valor_r * 100.0) if valor_r else 0.0
        else:
            pct_r = (lucro_r / valor_r * 100.0) if valor_r else 0.0

        # média combinada: itens + rascunho
        valor_itens = sum(float(it.get("valor_venda_total") or 0) for it in (itens or []))
        lucro = lucro + lucro_r
        peso = valor_itens + valor_r
        if peso > 0:
            media = ((media * valor_itens) + (pct_r * valor_r)) / peso if valor_itens else pct_r

    m1, m2 = st.columns(2)
    m1.metric("Lucro total", brl(lucro))
    m2.metric("Média de margens", f"{media:.2f}%".replace(".", ","))
    st.divider()


def render_tabela_memoria(
    *,
    titulo: str,
    params: dict | None,
    calculo: dict | None,
    key_prefix: str,
) -> None:
    """Uma memória: título + tabela de parâmetros + tabela de cálculo."""
    del key_prefix  # HTML tables não precisam de key Streamlit
    st.markdown(
        f'<div class="mem-item-title">{html.escape(titulo)}</div>',
        unsafe_allow_html=True,
    )
    if params:
        _tabela_html(_dict_para_linhas(params, _LABELS_PARAM), caption="Parâmetros de entrada")
    if calculo:
        _tabela_html(_dict_para_linhas(calculo, _LABELS_CALC), caption="Resultado do cálculo")
    if not params and not calculo:
        st.info("Sem dados de memória para este item.")
    st.markdown('<div class="mem-sep"></div>', unsafe_allow_html=True)


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
