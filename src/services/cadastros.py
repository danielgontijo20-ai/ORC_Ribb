"""Cadastros usados nos cálculos e telas de manutenção."""

from __future__ import annotations

import sqlite3
from datetime import datetime


def listar_materias_primas(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return list(
        conn.execute(
            """
            SELECT id, codigo, nome, nome_exibicao_orc, preco_compra, custo,
                   ultima_atualizacao, observacoes
            FROM materias_primas
            ORDER BY nome
            """
        )
    )


def listar_tubetes(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return list(
        conn.execute(
            """
            SELECT id, codigo, nome, nome_exibicao_orc, preco_compra, custo
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
            SELECT id, codigo, tipo_faca, nome_exibicao_orc, largura, altura,
                   gap_lateral, gap_vertical, area
            FROM facas
            ORDER BY tipo_faca
            """
        )
    )


def obter_faca_por_tipo(conn: sqlite3.Connection, tipo_faca: str) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM facas WHERE tipo_faca = ? LIMIT 1",
        (tipo_faca,),
    ).fetchone()


def obter_materia_por_nome(conn: sqlite3.Connection, nome: str) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM materias_primas WHERE nome = ? LIMIT 1",
        (nome,),
    ).fetchone()


def obter_tubete_por_nome(conn: sqlite3.Connection, nome: str) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM tubetes WHERE nome = ? LIMIT 1",
        (nome,),
    ).fetchone()


def obter_caixa_por_nome(conn: sqlite3.Connection, nome: str) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM caixas WHERE nome = ? LIMIT 1",
        (nome,),
    ).fetchone()


def calcular_area_faca(
    largura: float, altura: float, gap_lateral: float, gap_vertical: float | None
) -> float:
    gv = gap_vertical or 0.0
    return (largura + gap_lateral) * (altura + gv)


# ---- CRUD Clientes ----

def upsert_cliente(
    conn: sqlite3.Connection,
    *,
    cnpj_cpf: str,
    nome: str,
    uf: str | None = None,
    cliente_id: int | None = None,
) -> int:
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if cliente_id:
        conn.execute(
            """
            UPDATE clientes
            SET cnpj_cpf=?, nome=?, uf=?, atualizado_em=?
            WHERE id=?
            """,
            (cnpj_cpf, nome, uf, agora, cliente_id),
        )
        conn.commit()
        return cliente_id
    cur = conn.execute(
        """
        INSERT INTO clientes (cnpj_cpf, nome, uf, criado_em, atualizado_em)
        VALUES (?, ?, ?, ?, ?)
        """,
        (cnpj_cpf, nome, uf, agora, agora),
    )
    conn.commit()
    return int(cur.lastrowid)


def excluir_cliente(conn: sqlite3.Connection, cliente_id: int) -> None:
    conn.execute("DELETE FROM clientes WHERE id = ?", (cliente_id,))
    conn.commit()


# ---- CRUD Matéria-prima ----

def salvar_materia(
    conn: sqlite3.Connection,
    *,
    codigo: str,
    nome: str,
    nome_exibicao_orc: str,
    preco_compra: float | None,
    custo: float,
    observacoes: str | None = None,
    materia_id: int | None = None,
) -> int:
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if materia_id:
        conn.execute(
            """
            UPDATE materias_primas
            SET codigo=?, nome=?, nome_exibicao_orc=?, preco_compra=?, custo=?,
                ultima_atualizacao=?, observacoes=?
            WHERE id=?
            """,
            (
                codigo,
                nome,
                nome_exibicao_orc,
                preco_compra,
                custo,
                agora,
                observacoes,
                materia_id,
            ),
        )
        conn.commit()
        return materia_id
    cur = conn.execute(
        """
        INSERT INTO materias_primas
            (codigo, nome, nome_exibicao_orc, preco_compra, custo,
             ultima_atualizacao, observacoes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (codigo, nome, nome_exibicao_orc, preco_compra, custo, agora, observacoes),
    )
    conn.commit()
    return int(cur.lastrowid)


def excluir_materia(conn: sqlite3.Connection, materia_id: int) -> None:
    conn.execute("DELETE FROM materias_primas WHERE id = ?", (materia_id,))
    conn.commit()


# ---- CRUD Tubetes ----

def salvar_tubete(
    conn: sqlite3.Connection,
    *,
    codigo: str,
    nome: str,
    nome_exibicao_orc: str,
    preco_compra: float | None,
    custo: float,
    tubete_id: int | None = None,
) -> int:
    if tubete_id:
        conn.execute(
            """
            UPDATE tubetes
            SET codigo=?, nome=?, nome_exibicao_orc=?, preco_compra=?, custo=?
            WHERE id=?
            """,
            (codigo, nome, nome_exibicao_orc, preco_compra, custo, tubete_id),
        )
        conn.commit()
        return tubete_id
    cur = conn.execute(
        """
        INSERT INTO tubetes (codigo, nome, nome_exibicao_orc, preco_compra, custo)
        VALUES (?, ?, ?, ?, ?)
        """,
        (codigo, nome, nome_exibicao_orc, preco_compra, custo),
    )
    conn.commit()
    return int(cur.lastrowid)


def excluir_tubete(conn: sqlite3.Connection, tubete_id: int) -> None:
    conn.execute("DELETE FROM tubetes WHERE id = ?", (tubete_id,))
    conn.commit()


# ---- CRUD Caixas ----

def salvar_caixa(
    conn: sqlite3.Connection,
    *,
    codigo: str,
    nome: str,
    custo: float,
    caixa_id: int | None = None,
) -> int:
    if caixa_id:
        conn.execute(
            "UPDATE caixas SET codigo=?, nome=?, custo=? WHERE id=?",
            (codigo, nome, custo, caixa_id),
        )
        conn.commit()
        return caixa_id
    cur = conn.execute(
        "INSERT INTO caixas (codigo, nome, custo) VALUES (?, ?, ?)",
        (codigo, nome, custo),
    )
    conn.commit()
    return int(cur.lastrowid)


def excluir_caixa(conn: sqlite3.Connection, caixa_id: int) -> None:
    conn.execute("DELETE FROM caixas WHERE id = ?", (caixa_id,))
    conn.commit()


# ---- CRUD Facas ----

def salvar_faca(
    conn: sqlite3.Connection,
    *,
    codigo: str,
    tipo_faca: str,
    nome_exibicao_orc: str,
    largura: float,
    altura: float,
    gap_lateral: float,
    gap_vertical: float | None,
    faca_id: int | None = None,
) -> int:
    area = calcular_area_faca(largura, altura, gap_lateral, gap_vertical)
    if faca_id:
        conn.execute(
            """
            UPDATE facas
            SET codigo=?, tipo_faca=?, nome_exibicao_orc=?, largura=?, altura=?,
                gap_lateral=?, gap_vertical=?, area=?
            WHERE id=?
            """,
            (
                codigo,
                tipo_faca,
                nome_exibicao_orc,
                largura,
                altura,
                gap_lateral,
                gap_vertical,
                area,
                faca_id,
            ),
        )
        conn.commit()
        return faca_id
    cur = conn.execute(
        """
        INSERT INTO facas
            (codigo, tipo_faca, nome_exibicao_orc, largura, altura,
             gap_lateral, gap_vertical, area)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            codigo,
            tipo_faca,
            nome_exibicao_orc,
            largura,
            altura,
            gap_lateral,
            gap_vertical,
            area,
        ),
    )
    conn.commit()
    return int(cur.lastrowid)


def excluir_faca(conn: sqlite3.Connection, faca_id: int) -> None:
    conn.execute("DELETE FROM facas WHERE id = ?", (faca_id,))
    conn.commit()
