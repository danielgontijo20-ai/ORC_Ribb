"""Funções pequenas para exibir valores na tela."""

from __future__ import annotations


def brl(valor: float | None) -> str:
    """Moeda BRL com exatamente 2 casas decimais."""
    if valor is None:
        return "-"
    return f"R$ {float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def pct(valor: float | None, *, casas: int = 2) -> str:
    """Percentual com casas fixas (padrão 2)."""
    if valor is None:
        return "-"
    return f"{float(valor):,.{casas}f}%".replace(",", "X").replace(".", ",").replace("X", ".")


def num2(valor: float | None) -> str:
    """Número genérico com 2 casas decimais (pt-BR)."""
    if valor is None:
        return "-"
    return f"{float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def texto_ou_traco(valor) -> str:
    if valor is None or valor == "":
        return "-"
    return str(valor)
