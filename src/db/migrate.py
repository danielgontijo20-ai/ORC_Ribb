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

        # Status: rascunho | gerado | aprovado (+ legado finalizado)
        _migrate_orcamentos_status(conn)

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


def _migrate_orcamentos_status(conn: sqlite3.Connection) -> None:
    """Amplia CHECK de status e normaliza 'finalizado' → 'gerado'."""
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='orcamentos'"
    ).fetchone()
    ddl = (row["sql"] if row else "") or ""
    precisa_rebuild = "gerado" not in ddl or "aprovado" not in ddl

    if precisa_rebuild:
        print("+ orcamentos.status: ampliando CHECK (gerado/aprovado)")
        conn.execute("PRAGMA foreign_keys=OFF")
        conn.execute("DROP TABLE IF EXISTS orcamentos_new")
        conn.execute(
            """
            CREATE TABLE orcamentos_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                numero TEXT,
                cliente_id INTEGER,
                cliente_avulso_nome TEXT,
                cliente_avulso_documento TEXT,
                solicitante TEXT,
                status TEXT NOT NULL DEFAULT 'rascunho'
                    CHECK (status IN ('rascunho', 'gerado', 'aprovado', 'finalizado', 'cancelado')),
                validade_proposta TEXT,
                prazo_pagamento TEXT,
                prazo_entrega TEXT,
                frete_tipo TEXT,
                frete_taxa REAL,
                impostos TEXT,
                informacoes_adicionais TEXT,
                orcamentista_nome TEXT,
                orcamentista_cargo TEXT,
                orcamentista_telefone TEXT,
                orcamentista_email TEXT,
                lucro_total REAL DEFAULT 0,
                valor_total REAL DEFAULT 0,
                frete_total REAL DEFAULT 0,
                criado_em TEXT NOT NULL DEFAULT (datetime('now')),
                atualizado_em TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (cliente_id) REFERENCES clientes(id)
            )
            """
        )
        cols_old = _columns(conn, "orcamentos")
        cols_new = _columns(conn, "orcamentos_new")
        comuns = [c for c in cols_new if c in cols_old]
        cols_sql = ", ".join(comuns)
        conn.execute(
            f"INSERT INTO orcamentos_new ({cols_sql}) SELECT {cols_sql} FROM orcamentos"
        )
        conn.execute("DROP TABLE orcamentos")
        conn.execute("ALTER TABLE orcamentos_new RENAME TO orcamentos")
        conn.execute("PRAGMA foreign_keys=ON")

    # Legado: finalizado passa a ser tratado como gerado
    cur = conn.execute(
        "UPDATE orcamentos SET status = 'gerado' WHERE status = 'finalizado'"
    )
    if cur.rowcount:
        print(f"+ orcamentos: {cur.rowcount} status finalizado → gerado")


if __name__ == "__main__":
    migrate()
