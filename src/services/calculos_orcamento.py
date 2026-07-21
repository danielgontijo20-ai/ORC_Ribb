"""
Cálculos de orçamento — mesmas regras da planilha Banco_RBT.xlsx.

ORC_Etiqueta:
- área da faca (m²)
- m² do rolo = qtd_etiquetas * área
- custo matéria = m²_rolo * custo_m2
- custo caixas por rolo = (qtd_caixas * custo_caixa) / n_rolos
- perda = (matéria + tubete + caixas_por_rolo) * percentual_perda
- custo_sem_frete = matéria + tubete + caixas_por_rolo + perda
- frete_por_rolo = frete_total / n_rolos
- custo_com_frete = custo_sem_frete + frete_por_rolo
- lucro_por_rolo = lucro_% * custo_sem_frete
- preço_sem_imposto = custo_com_frete + lucro_por_rolo
- preço_com_imposto = preço_sem_imposto / 0.92
- valor_venda_total = preço_com_imposto * n_rolos
- lucro_total = lucro_por_rolo * n_rolos

ORC_Suprimentos:
- frete_unit = frete_total / quantidade
- difal = custo * 0.073 se SIM, senão 0
- custo_unit = custo + frete_unit + difal
- lucro_unit = lucro_% * custo
- preço_sem_imposto = custo_unit + lucro_unit
- preço_com_imposto = preço_sem_imposto / 0.91
- valor_venda_total = preço_com_imposto * quantidade
- lucro_total = lucro_unit * quantidade
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


IMPOSTO_ETIQUETA = 0.92
IMPOSTO_SUPRIMENTOS = 0.91
ALIQUOTA_DIFAL = 0.073


@dataclass
class ResultadoEtiqueta:
    area_faca: float
    m2_rolo: float
    m2_total: float
    custo_materia_rolo: float
    custo_tubete: float
    custo_caixas_total: float
    custo_caixas_por_rolo: float
    custo_perda: float
    custo_sem_frete: float
    frete_por_rolo: float
    custo_com_frete: float
    lucro_por_rolo: float
    lucro_total: float
    preco_sem_imposto: float
    preco_com_imposto: float
    valor_venda_total: float

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ResultadoSuprimentos:
    frete_unitario: float
    difal_unitario: float
    custo_unitario: float
    lucro_unitario: float
    lucro_total: float
    preco_sem_imposto: float
    preco_com_imposto: float
    valor_venda_total: float

    def to_dict(self) -> dict:
        return asdict(self)


def calcular_orcamento_etiqueta(
    area_faca: float,
    qtd_etiquetas_por_rolo: float,
    numero_rolos: float,
    custo_m2_materia: float,
    custo_tubete: float,
    custo_caixa: float,
    qtd_caixas: float,
    perda_processo: float,
    frete_total: float,
    lucro_percentual: float,
) -> ResultadoEtiqueta:
    if numero_rolos <= 0:
        raise ValueError("Número de rolos deve ser maior que zero.")
    if qtd_etiquetas_por_rolo <= 0:
        raise ValueError("Quantidade de etiquetas por rolo deve ser maior que zero.")

    m2_rolo = qtd_etiquetas_por_rolo * area_faca
    m2_total = numero_rolos * m2_rolo
    custo_materia_rolo = m2_rolo * custo_m2_materia
    custo_caixas_total = qtd_caixas * custo_caixa
    custo_caixas_por_rolo = custo_caixas_total / numero_rolos
    custo_perda = (custo_materia_rolo + custo_tubete + custo_caixas_por_rolo) * perda_processo
    custo_sem_frete = (
        custo_materia_rolo + custo_tubete + custo_caixas_por_rolo + custo_perda
    )
    frete_por_rolo = frete_total / numero_rolos
    custo_com_frete = custo_sem_frete + frete_por_rolo
    lucro_por_rolo = lucro_percentual * custo_sem_frete
    lucro_total = lucro_por_rolo * numero_rolos
    preco_sem_imposto = custo_com_frete + lucro_por_rolo
    preco_com_imposto = preco_sem_imposto / IMPOSTO_ETIQUETA
    valor_venda_total = preco_com_imposto * numero_rolos

    return ResultadoEtiqueta(
        area_faca=area_faca,
        m2_rolo=m2_rolo,
        m2_total=m2_total,
        custo_materia_rolo=custo_materia_rolo,
        custo_tubete=custo_tubete,
        custo_caixas_total=custo_caixas_total,
        custo_caixas_por_rolo=custo_caixas_por_rolo,
        custo_perda=custo_perda,
        custo_sem_frete=custo_sem_frete,
        frete_por_rolo=frete_por_rolo,
        custo_com_frete=custo_com_frete,
        lucro_por_rolo=lucro_por_rolo,
        lucro_total=lucro_total,
        preco_sem_imposto=preco_sem_imposto,
        preco_com_imposto=preco_com_imposto,
        valor_venda_total=valor_venda_total,
    )


def calcular_orcamento_suprimentos(
    custo: float,
    frete_total: float,
    quantidade: float,
    difal: bool,
    lucro_percentual: float,
) -> ResultadoSuprimentos:
    if quantidade <= 0:
        raise ValueError("Quantidade deve ser maior que zero.")

    frete_unitario = frete_total / quantidade
    difal_unitario = custo * ALIQUOTA_DIFAL if difal else 0.0
    custo_unitario = custo + frete_unitario + difal_unitario
    lucro_unitario = lucro_percentual * custo
    lucro_total = lucro_unitario * quantidade
    preco_sem_imposto = custo_unitario + lucro_unitario
    preco_com_imposto = preco_sem_imposto / IMPOSTO_SUPRIMENTOS
    valor_venda_total = preco_com_imposto * quantidade

    return ResultadoSuprimentos(
        frete_unitario=frete_unitario,
        difal_unitario=difal_unitario,
        custo_unitario=custo_unitario,
        lucro_unitario=lucro_unitario,
        lucro_total=lucro_total,
        preco_sem_imposto=preco_sem_imposto,
        preco_com_imposto=preco_com_imposto,
        valor_venda_total=valor_venda_total,
    )
