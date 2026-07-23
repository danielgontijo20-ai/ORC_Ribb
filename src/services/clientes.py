"""Consultas de clientes para a tela de orçamento."""

from __future__ import annotations

import sqlite3


def buscar_clientes(
    conn: sqlite3.Connection,
    termo: str | None = None,
    limite: int | None = None,
) -> list[sqlite3.Row]:
    """
    Busca clientes por nome ou CNPJ/CPF no banco inteiro.

    limite=None => sem limite (retorna todos os que batem com o filtro).
    """
    if termo and termo.strip():
        like = f"%{termo.strip()}%"
        sql = """
            SELECT id, nome, cnpj_cpf, uf
            FROM clientes
            WHERE nome LIKE ? OR cnpj_cpf LIKE ?
            ORDER BY nome
        """
        params: list = [like, like]
    else:
        sql = """
            SELECT id, nome, cnpj_cpf, uf
            FROM clientes
            ORDER BY nome
        """
        params = []

    if limite is not None:
        sql += " LIMIT ?"
        params.append(limite)

    return list(conn.execute(sql, params))


def contar_clientes(conn: sqlite3.Connection, termo: str | None = None) -> int:
    if termo and termo.strip():
        like = f"%{termo.strip()}%"
        row = conn.execute(
            """
            SELECT COUNT(*) AS c FROM clientes
            WHERE nome LIKE ? OR cnpj_cpf LIKE ?
            """,
            (like, like),
        ).fetchone()
    else:
        row = conn.execute("SELECT COUNT(*) AS c FROM clientes").fetchone()
    return int(row["c"])


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
