"""Testes simples dos cálculos (podem ser rodados com: python -m src.services.test_calculos)."""

from __future__ import annotations

from .calculos_orcamento import (
    calcular_orcamento_etiqueta,
    calcular_orcamento_suprimentos,
)


def quase_igual(a: float, b: float, tol: float = 1e-6) -> bool:
    return abs(a - b) <= tol


def test_etiqueta_planilha() -> None:
    # Valores de exemplo da aba ORC_Etiqueta
    r = calcular_orcamento_etiqueta(
        area_faca=0.0054969798,
        qtd_etiquetas_por_rolo=1500,
        numero_rolos=120,
        custo_m2_materia=3.3,
        custo_tubete=0.31,
        custo_caixa=5,
        qtd_caixas=12,
        perda_processo=0,
        frete_total=120,
        lucro_percentual=0.3,
    )
    assert quase_igual(r.custo_sem_frete, 28.02005001)
    assert quase_igual(r.preco_com_imposto, 40.68050544891304)
    assert quase_igual(r.valor_venda_total, 4881.660653869565)
    assert quase_igual(r.lucro_total, 1008.7218003600001)


def test_suprimentos_planilha() -> None:
    r = calcular_orcamento_suprimentos(
        custo=2.9,
        frete_total=120,
        quantidade=300,
        difal=True,
        lucro_percentual=0.2,
    )
    assert quase_igual(r.preco_com_imposto, 4.496373626373626)
    assert quase_igual(r.valor_venda_total, 1348.9120879120878)
    assert quase_igual(r.lucro_total, 174.0)


if __name__ == "__main__":
    test_etiqueta_planilha()
    test_suprimentos_planilha()
    print("OK: cálculos batem com a planilha.")
