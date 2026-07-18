"""
Regra de descrição do item orçado (slide 17 do LAYOUT_ORC_RBT).

Etiqueta:
  Etiqueta {mp ORC} {faca ORC} - Rolo com {qtd/rolo} - {tubete ORC}

Suprimentos:
  {descrição digitada}
"""

from __future__ import annotations


def montar_descricao_etiqueta(
    nome_mp_orc: str,
    nome_faca_orc: str,
    qtd_etiquetas_por_rolo: int | float,
    nome_tubete_orc: str,
) -> str:
    qtd = int(qtd_etiquetas_por_rolo)
    qtd_fmt = f"{qtd:,}".replace(",", ".")
    return (
        f"Etiqueta {nome_mp_orc.strip()} {nome_faca_orc.strip()} "
        f"- Rolo com {qtd_fmt} - {nome_tubete_orc.strip()}"
    )


def montar_descricao_suprimento(descricao: str) -> str:
    return (descricao or "").strip()
