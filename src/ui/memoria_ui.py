"""Exibição da memória de cálculo em tabelas."""

from __future__ import annotations

from typing import Any

import pandas as pd
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


def _dict_para_tabela(dados: dict, labels: dict[str, str]) -> pd.DataFrame:
    linhas = []
    for k, v in (dados or {}).items():
        label = labels.get(k, k.replace("_", " ").capitalize())
        linhas.append({"Campo": label, "Valor": _fmt_valor(k, v)})
    return pd.DataFrame(linhas)


def _resultado_para_dict(resultado) -> dict:
    if isinstance(resultado, (ResultadoEtiqueta, ResultadoSuprimentos)):
        return resultado.to_dict()
    if isinstance(resultado, dict):
        return resultado
    return {}


def render_tabela_memoria(
    *,
    titulo: str,
    params: dict | None,
    calculo: dict | None,
    key_prefix: str,
) -> None:
    """Uma memória: título + tabela de parâmetros + tabela de cálculo."""
    st.markdown(f"##### {titulo}")
    if params:
        st.caption("Parâmetros de entrada")
        st.dataframe(
            _dict_para_tabela(params, _LABELS_PARAM),
            use_container_width=True,
            hide_index=True,
            key=f"{key_prefix}_params",
        )
    if calculo:
        st.caption("Resultado do cálculo")
        st.dataframe(
            _dict_para_tabela(calculo, _LABELS_CALC),
            use_container_width=True,
            hide_index=True,
            key=f"{key_prefix}_calc",
        )
    if not params and not calculo:
        st.info("Sem dados de memória para este item.")
    st.divider()


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
        # normaliza chaves de params vindas do formulário
        if not any(k in params for k in ("Dimensão", "Descrição", "Matéria-prima")):
            # params internos (faca, materia...) — ok, labels cobrem
            pass
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
    Exibe memória completa: cálculo atual (se houver) + um bloco por item inserido.
    """
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
