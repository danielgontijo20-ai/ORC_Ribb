"""Funções pequenas para exibir valores na tela."""

from __future__ import annotations


def brl(valor: float | None) -> str:
    if valor is None:
        return "-"
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def texto_ou_traco(valor) -> str:
    if valor is None or valor == "":
        return "-"
    return str(valor)
