"""Valores nativos padrão (conforme LAYOUT_ORC_RBT.pptx)."""

from __future__ import annotations

import sqlite3

DEFAULT_CONFIG: dict[str, str] = {
    # Empresa (cabeçalho da proposta) — editar em Cadastros > Valores Nativos
    "empresa_nome": "",
    "empresa_cnpj": "",
    "empresa_telefone": "",
    "empresa_email": "",
    # Cálculo
    "frete_padrao": "0",
    "perda_padrao": "0",
    "lucro_etiqueta_padrao": "0.30",
    "lucro_suprimentos_padrao": "0.20",
    "difal_padrao": "SIM",
    "unidade_etiqueta": "Rol",
    "unidade_suprimentos": "UN",
    # Condições gerais
    "validade_proposta": "15 dias",
    "prazo_pagamento": "21 dias",
    "prazo_entrega": "5 dias",
    "frete_tipo": "CIF",
    "impostos": "Inclusos",
    "informacoes_adicionais": (
        "As quantidades podem sofrer alterações de 10% para mais ou para menos"
    ),
    # Orçamentista
    "orcamentista_nome": "Daniel",
    "orcamentista_cargo": "Diretor",
    "orcamentista_telefone": "+55 31 99830-8560",
    "orcamentista_email": "daniel@ribbontechbrasil.com",
    # Logos (caminhos relativos ao projeto)
    "logo_master": "",
    "logo_cabecalho": "",
    "logo_rodape": "",
    # Sequência de orçamento
    "proximo_numero_orcamento": "1",
}


def ensure_config_defaults(conn: sqlite3.Connection) -> None:
    for chave, valor in DEFAULT_CONFIG.items():
        conn.execute(
            """
            INSERT OR IGNORE INTO configuracoes (chave, valor)
            VALUES (?, ?)
            """,
            (chave, valor),
        )
