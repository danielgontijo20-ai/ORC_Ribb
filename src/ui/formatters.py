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


def fator_para_pct_input(fator) -> str:
    """Converte fator (0,30) para valor de formulário em % (30)."""
    if fator is None or fator == "":
        return ""
    try:
        f = float(fator)
    except (TypeError, ValueError):
        return ""
    # Valores já em % (legado / digitação antiga) — não multiplica de novo
    if abs(f) > 5:
        pct_v = f
    else:
        pct_v = f * 100.0
    if abs(pct_v - round(pct_v)) < 1e-9:
        return str(int(round(pct_v)))
    return f"{pct_v:.4f}".rstrip("0").rstrip(".")


def pct_input_para_fator(valor) -> float | None:
    """Converte entrada do formulário em % (30) para fator (0,30)."""
    if valor is None:
        return None
    t = str(valor).strip().replace("%", "").replace(",", ".")
    if not t:
        return None
    try:
        n = float(t)
    except ValueError:
        return None
    return n / 100.0


def num2(valor: float | None) -> str:
    """Número genérico com 2 casas decimais (pt-BR)."""
    if valor is None:
        return "-"
    return f"{float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def texto_ou_traco(valor) -> str:
    if valor is None or valor == "":
        return "-"
    return str(valor)
