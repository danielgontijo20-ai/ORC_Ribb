"""Log de alterações de custo nos cadastros."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Any


def ensure_custo_log_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS custo_alteracoes_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tabela TEXT NOT NULL,
            registro_id INTEGER NOT NULL,
            campo TEXT NOT NULL DEFAULT 'custo',
            codigo TEXT,
            nome TEXT,
            valor_anterior REAL,
            valor_novo REAL,
            usuario_id INTEGER,
            usuario_nome TEXT,
            criado_em TEXT NOT NULL
        )
        """
    )
    conn.commit()


def registrar_custo(
    conn: sqlite3.Connection,
    *,
    tabela: str,
    registro_id: int,
    valor_anterior: float | None,
    valor_novo: float | None,
    codigo: str | None = None,
    nome: str | None = None,
    usuario: dict | None = None,
    campo: str = "custo",
) -> None:
    if valor_anterior is None and valor_novo is None:
        return
    try:
        ant = float(valor_anterior) if valor_anterior is not None else None
        novo = float(valor_novo) if valor_novo is not None else None
    except (TypeError, ValueError):
        return
    if ant is not None and novo is not None and abs(ant - novo) < 1e-9:
        return
    ensure_custo_log_table(conn)
    conn.execute(
        """
        INSERT INTO custo_alteracoes_log (
            tabela, registro_id, campo, codigo, nome,
            valor_anterior, valor_novo, usuario_id, usuario_nome, criado_em
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            tabela,
            registro_id,
            campo,
            codigo,
            nome,
            ant,
            novo,
            (usuario or {}).get("id"),
            (usuario or {}).get("nome"),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ),
    )
    conn.commit()


def listar_log(
    conn: sqlite3.Connection,
    *,
    tabela: str | None = None,
    registro_id: int | None = None,
    limite: int = 50,
) -> list[dict[str, Any]]:
    ensure_custo_log_table(conn)
    sql = "SELECT * FROM custo_alteracoes_log WHERE 1=1"
    params: list[Any] = []
    if tabela:
        sql += " AND tabela = ?"
        params.append(tabela)
    if registro_id is not None:
        sql += " AND registro_id = ?"
        params.append(registro_id)
    sql += " ORDER BY id DESC LIMIT ?"
    params.append(limite)
    return [dict(r) for r in conn.execute(sql, params)]
