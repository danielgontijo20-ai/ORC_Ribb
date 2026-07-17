"""Consultas de clientes para a tela de orçamento."""

from __future__ import annotations

import sqlite3
from typing import Any


def buscar_clientes(
    conn: sqlite3.Connection,
    termo: str | None = None,
    limite: int = 100,
) -> list[sqlite3.Row]:
    """Busca clientes por nome ou CNPJ/CPF."""
    if termo:
        like = f"%{termo.strip()}%"
        return list(
            conn.execute(
                """
                SELECT id, nome, cnpj_cpf, uf
                FROM clientes
                WHERE nome LIKE ? OR cnpj_cpf LIKE ?
                ORDER BY nome
                LIMIT ?
                """,
                (like, like, limite),
            )
        )

    return list(
        conn.execute(
            """
            SELECT id, nome, cnpj_cpf, uf
            FROM clientes
            ORDER BY nome
            LIMIT ?
            """,
            (limite,),
        )
    )


def obter_cliente(conn: sqlite3.Connection, cliente_id: int) -> sqlite3.Row | None:
    return conn.execute(
        """
        SELECT id, nome, cnpj_cpf, uf
        FROM clientes
        WHERE id = ?
        """,
        (cliente_id,),
    ).fetchone()


def listar_segmentos(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        "SELECT nome FROM segmentos ORDER BY nome"
    ).fetchall()
    return [r["nome"] for r in rows]
