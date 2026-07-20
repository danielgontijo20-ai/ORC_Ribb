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
from src.services.custo_log import ensure_custo_log_table
from src.services.usuarios import ensure_auth_seed


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
            ("empresa_cnpj", "TEXT"),
            ("reprovacao_observacao", "TEXT"),
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

        # Auth web: usuários / papéis / permissões
        auth_sql = Path(__file__).resolve().parent / "auth_schema.sql"
        if auth_sql.exists():
            conn.executescript(auth_sql.read_text(encoding="utf-8"))
            ensure_auth_seed(conn)
            print("+ auth: tabelas e seed de usuários/papéis")

        ensure_custo_log_table(conn)
        print("+ custo_alteracoes_log")

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
    """Amplia CHECK de status e normaliza 'finalizado' → 'gerado'.

    Importante: PRAGMA foreign_keys=OFF é no-op dentro de transação. Sem commit
    prévio, o DROP de orcamentos dispara ON DELETE CASCADE e apaga os itens.
    """
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='orcamentos'"
    ).fetchone()
    ddl = (row["sql"] if row else "") or ""
    precisa_rebuild = (
        "gerado" not in ddl or "aprovado" not in ddl or "reprovado" not in ddl
    )

    if precisa_rebuild:
        print("+ orcamentos.status: ampliando CHECK (gerado/aprovado/reprovado)")
        # Fecha transação aberta (UPDATEs anteriores) — senão FK OFF não vale.
        conn.commit()
        conn.execute("PRAGMA foreign_keys=OFF")
        if conn.execute("PRAGMA foreign_keys").fetchone()[0]:
            raise sqlite3.OperationalError(
                "Não foi possível desligar foreign_keys antes do rebuild de orcamentos"
            )

        # Backup dos itens para restaurar se o CASCADE ainda apagar algo
        conn.execute("DROP TABLE IF EXISTS _orcamento_itens_bak")
        conn.execute(
            "CREATE TABLE _orcamento_itens_bak AS SELECT * FROM orcamento_itens"
        )
        n_itens_bak = conn.execute(
            "SELECT COUNT(*) AS c FROM _orcamento_itens_bak"
        ).fetchone()["c"]

        cols_info = list(conn.execute("PRAGMA table_info(orcamentos)").fetchall())
        col_defs: list[str] = []
        for c in cols_info:
            name = c["name"]
            if name == "id":
                col_defs.append("id INTEGER PRIMARY KEY AUTOINCREMENT")
            elif name == "status":
                col_defs.append(
                    "status TEXT NOT NULL DEFAULT 'rascunho' "
                    "CHECK (status IN ("
                    "'rascunho', 'gerado', 'aprovado', 'reprovado', "
                    "'finalizado', 'cancelado'))"
                )
            else:
                typ = (c["type"] or "TEXT").strip() or "TEXT"
                notnull = " NOT NULL" if c["notnull"] else ""
                dflt = c["dflt_value"]
                if dflt is None:
                    dflt_sql = ""
                else:
                    dflt_s = str(dflt)
                    # Expressões (ex.: datetime('now')) precisam de parênteses no DEFAULT
                    if "(" in dflt_s and not dflt_s.startswith("("):
                        dflt_s = f"({dflt_s})"
                    dflt_sql = f" DEFAULT {dflt_s}"
                col_defs.append(f"{name} {typ}{notnull}{dflt_sql}")
        if "reprovacao_observacao" not in {c["name"] for c in cols_info}:
            col_defs.append("reprovacao_observacao TEXT")

        conn.execute("DROP TABLE IF EXISTS orcamentos_new")
        create_sql = (
            "CREATE TABLE orcamentos_new (\n  "
            + ",\n  ".join(col_defs)
            + ",\n  FOREIGN KEY (cliente_id) REFERENCES clientes(id)\n)"
        )
        conn.execute(create_sql)
        cols_old = _columns(conn, "orcamentos")
        cols_new = _columns(conn, "orcamentos_new")
        comuns = [c for c in cols_new if c in cols_old]
        cols_sql = ", ".join(comuns)
        conn.execute(
            f"INSERT INTO orcamentos_new ({cols_sql}) SELECT {cols_sql} FROM orcamentos"
        )
        conn.execute("DROP TABLE orcamentos")
        conn.execute("ALTER TABLE orcamentos_new RENAME TO orcamentos")

        n_itens = conn.execute(
            "SELECT COUNT(*) AS c FROM orcamento_itens"
        ).fetchone()["c"]
        if n_itens_bak and n_itens < n_itens_bak:
            print(
                f"! orcamento_itens perdeu linhas no rebuild "
                f"({n_itens}/{n_itens_bak}). Restaurando backup…"
            )
            conn.execute("DELETE FROM orcamento_itens")
            bak_cols = [
                r["name"]
                for r in conn.execute("PRAGMA table_info(_orcamento_itens_bak)")
            ]
            live_cols = _columns(conn, "orcamento_itens")
            comuns_itens = [c for c in bak_cols if c in live_cols]
            cols_i = ", ".join(comuns_itens)
            conn.execute(
                f"INSERT INTO orcamento_itens ({cols_i}) "
                f"SELECT {cols_i} FROM _orcamento_itens_bak"
            )
            n_itens = conn.execute(
                "SELECT COUNT(*) AS c FROM orcamento_itens"
            ).fetchone()["c"]
            print(f"+ orcamento_itens restaurados: {n_itens}")

        conn.execute("DROP TABLE IF EXISTS _orcamento_itens_bak")
        conn.commit()
        conn.execute("PRAGMA foreign_keys=ON")

    # Legado: finalizado passa a ser tratado como gerado
    cur = conn.execute(
        "UPDATE orcamentos SET status = 'gerado' WHERE status = 'finalizado'"
    )
    if cur.rowcount:
        print(f"+ orcamentos: {cur.rowcount} status finalizado → gerado")


if __name__ == "__main__":
    migrate()
