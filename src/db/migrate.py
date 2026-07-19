"""
Aplica migrações em banco já existente (sem apagar o histórico).

Uso:
    python -m src.db.migrate
"""

from __future__ import annotations

import sqlite3

from pathlib import Path

from .database import DB_PATH, ROOT_DIR, connect, init_db
from .defaults_config import DEFAULT_CONFIG, ensure_config_defaults
from .import_banco_rbt import import_suprimentos


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {r["name"] for r in rows}


def _add_column_if_missing(
    conn: sqlite3.Connection, table: str, column: str, decl: str
) -> None:
    if column not in _columns(conn, table):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")
        print(f"+ {table}.{column}")


def migrate(db_path=DB_PATH) -> None:
    init_db(db_path)  # cria tabelas novas se não existirem

    with connect(db_path) as conn:
        # Campos de nome de exibição no ORC
        _add_column_if_missing(conn, "materias_primas", "nome_exibicao_orc", "TEXT")
        _add_column_if_missing(conn, "tubetes", "nome_exibicao_orc", "TEXT")
        _add_column_if_missing(conn, "facas", "nome_exibicao_orc", "TEXT")

        # Orçamentos — colunas do fluxo de proposta/histórico
        for col, decl in [
            ("numero", "TEXT"),
            ("solicitante", "TEXT"),
            ("validade_proposta", "TEXT"),
            ("prazo_pagamento", "TEXT"),
            ("prazo_entrega", "TEXT"),
            ("frete_tipo", "TEXT"),
            ("frete_taxa", "REAL"),
            ("impostos", "TEXT"),
            ("informacoes_adicionais", "TEXT"),
            ("orcamentista_nome", "TEXT"),
            ("orcamentista_cargo", "TEXT"),
            ("orcamentista_telefone", "TEXT"),
            ("orcamentista_email", "TEXT"),
            ("frete_total", "REAL DEFAULT 0"),
        ]:
            _add_column_if_missing(conn, "orcamentos", col, decl)

        _add_column_if_missing(conn, "orcamento_itens", "unidade", "TEXT")
        _add_column_if_missing(conn, "orcamento_itens", "frete_item", "REAL DEFAULT 0")

        # Preenche nomes de exibição vazios com o nome técnico atual
        conn.execute(
            """
            UPDATE materias_primas
            SET nome_exibicao_orc = nome
            WHERE nome_exibicao_orc IS NULL OR TRIM(nome_exibicao_orc) = ''
            """
        )
        conn.execute(
            """
            UPDATE tubetes
            SET nome_exibicao_orc = nome
            WHERE nome_exibicao_orc IS NULL OR TRIM(nome_exibicao_orc) = ''
            """
        )
        conn.execute(
            """
            UPDATE facas
            SET nome_exibicao_orc = tipo_faca
            WHERE nome_exibicao_orc IS NULL OR TRIM(nome_exibicao_orc) = ''
            """
        )

        ensure_config_defaults(conn)

        # Suprimentos: importa pré-cadastro se a tabela estiver vazia
        n_sup = conn.execute("SELECT COUNT(*) c FROM suprimentos").fetchone()["c"]
        if n_sup == 0:
            xlsx_sup = ROOT_DIR / "data" / "planilhas" / "Tabela_Suprimentos.xlsx"
            if xlsx_sup.exists():
                imported = import_suprimentos(conn, xlsx_sup)
                print(f"+ suprimentos importados: {imported}")
            else:
                print(f"! Arquivo não encontrado: {xlsx_sup}")

        conn.commit()

    print(f"Migração concluída: {db_path}")
    print(f"Valores nativos padrão carregados ({len(DEFAULT_CONFIG)} chaves).")


if __name__ == "__main__":
    migrate()
