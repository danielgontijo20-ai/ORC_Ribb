"""Testes da conversão lucro % → fator (20 → 0,2)."""

from __future__ import annotations

from src.services.calculos_orcamento import calcular_orcamento_suprimentos
from src.ui.formatters import fator_para_pct_input, pct_input_para_fator


def test_pct_input_para_fator_vinte_vira_zero_dois() -> None:
    assert pct_input_para_fator("20") == 0.2
    assert pct_input_para_fator("20%") == 0.2
    assert pct_input_para_fator("30") == 0.3
    assert pct_input_para_fator("0") == 0.0


def test_fator_para_pct_input_exibe_porcentagem() -> None:
    assert fator_para_pct_input(0.2) == "20"
    assert fator_para_pct_input(0.30) == "30"
    assert fator_para_pct_input("20") == "20"


def test_calculo_usa_fator_de_entrada_percentual() -> None:
    fator = pct_input_para_fator("20")
    assert fator == 0.2
    r = calcular_orcamento_suprimentos(
        custo=100.0,
        frete_total=0.0,
        quantidade=2,
        difal=False,
        lucro_percentual=float(fator),
    )
    assert abs(r.lucro_unitario - 20.0) < 1e-9
    assert abs(r.lucro_total - 40.0) < 1e-9


if __name__ == "__main__":
    test_pct_input_para_fator_vinte_vira_zero_dois()
    test_fator_para_pct_input_exibe_porcentagem()
    test_calculo_usa_fator_de_entrada_percentual()
    print("OK formatters lucro %")
