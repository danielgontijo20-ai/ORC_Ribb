"""Cadastros usados nos cálculos de orçamento."""

from __future__ import annotations

import sqlite3


def listar_materias_primas(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return list(
        conn.execute(
            """
            SELECT id, codigo, nome, preco_compra, custo, ultima_atualizacao, observacoes
            FROM materias_primas
            ORDER BY nome
            """
        )
    )


def listar_tubetes(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return list(
        conn.execute(
            """
            SELECT id, codigo, nome, preco_compra, custo
            FROM tubetes
            ORDER BY nome
            """
        )
    )


def listar_caixas(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return list(
        conn.execute(
            """
            SELECT id, codigo, nome, custo
            FROM caixas
            ORDER BY nome
            """
        )
    )


def listar_facas(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return list(
        conn.execute(
            """
            SELECT id, codigo, tipo_faca, largura, altura, gap_lateral, gap_vertical, area
            FROM facas
            ORDER BY tipo_faca
            """
        )
    )


def obter_faca_por_tipo(conn: sqlite3.Connection, tipo_faca: str) -> sqlite3.Row | None:
    return conn.execute(
        """
        SELECT id, codigo, tipo_faca, largura, altura, gap_lateral, gap_vertical, area
        FROM facas
        WHERE tipo_faca = ?
        LIMIT 1
        """,
        (tipo_faca,),
    ).fetchone()


def obter_materia_por_nome(conn: sqlite3.Connection, nome: str) -> sqlite3.Row | None:
    return conn.execute(
        """
        SELECT id, codigo, nome, preco_compra, custo
        FROM materias_primas
        WHERE nome = ?
        LIMIT 1
        """,
        (nome,),
    ).fetchone()


def obter_tubete_por_nome(conn: sqlite3.Connection, nome: str) -> sqlite3.Row | None:
    return conn.execute(
        """
        SELECT id, codigo, nome, preco_compra, custo
        FROM tubetes
        WHERE nome = ?
        LIMIT 1
        """,
        (nome,),
    ).fetchone()


def obter_caixa_por_nome(conn: sqlite3.Connection, nome: str) -> sqlite3.Row | None:
    return conn.execute(
        """
        SELECT id, codigo, nome, custo
        FROM caixas
        WHERE nome = ?
        LIMIT 1
        """,
        (nome,),
    ).fetchone()
