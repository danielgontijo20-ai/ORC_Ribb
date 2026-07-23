"""Valores nativos padrão (conforme LAYOUT_ORC_RBT.pptx)."""

from __future__ import annotations

import sqlite3

DEFAULT_CONFIG: dict[str, str] = {
    # Empresa (cabeçalho da proposta)
    "empresa_nome": "Ribbontech",
    "empresa_cnpj": "51.832.369/0001-00",
    "empresa_cnpj_2": "31.382.218/0001-81",
    "empresa_telefone": "31 99830-8560",
    "empresa_email": "ribbontech@ribbontech.com",
    # Cálculo (lucro/perda internos em fator: 0.30 = 30%)
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

# Chaves de empresa: se vazias no banco, aplicamos o padrão Ribbontech
_EMPRESA_KEYS = (
    "empresa_nome",
    "empresa_cnpj",
    "empresa_cnpj_2",
    "empresa_telefone",
    "empresa_email",
)

_CNPJ_PLACEHOLDERS = {
    "",
    "00.000.000/00-00",
    "00.000.000/0000-00",
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

    # Preenche dados da empresa quando estiverem vazios / placeholder
    for chave in _EMPRESA_KEYS:
        row = conn.execute(
            "SELECT valor FROM configuracoes WHERE chave = ?", (chave,)
        ).fetchone()
        atual = (row["valor"] if row else "") or ""
        if not str(atual).strip() or (
            chave.startswith("empresa_cnpj") and str(atual).strip() in _CNPJ_PLACEHOLDERS
        ):
            conn.execute(
                "UPDATE configuracoes SET valor = ? WHERE chave = ?",
                (DEFAULT_CONFIG[chave], chave),
            )
