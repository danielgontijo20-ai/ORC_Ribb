"""
Consultas de histórico de vendas.

Regra de negócio (combinada com o usuário):
- A "última venda" é a última venda daquele PRODUTO para aquele CLIENTE.
- Se o item não tiver código na nota, usamos a descrição como chave.
"""

from __future__ import annotations

import sqlite3
from typing import Any


def listar_itens_vendidos_ao_cliente(
    conn: sqlite3.Connection,
    cliente_id: int,
    termo: str | None = None,
    segmento: str | None = None,
) -> list[sqlite3.Row]:
    """
    Grid de itens já vendidos para o cliente.

    Retorna 1 linha por produto, com dados da última venda
    e quantas vezes aquele item foi vendido ao cliente.

    Chave do produto:
    - código do item, se existir
    - senão, a descrição (para notas antigas sem código)
    """
    sql = """
        WITH base AS (
            SELECT
                f.codigo_item,
                f.descricao_item,
                f.data_emissao,
                f.quantidade,
                f.valor_unitario,
                f.valor_total,
                s.nome AS segmento,
                COALESCE(f.codigo_item, f.descricao_item) AS chave_produto,
                ROW_NUMBER() OVER (
                    PARTITION BY COALESCE(f.codigo_item, f.descricao_item)
                    ORDER BY f.data_emissao DESC, f.id DESC
                ) AS rn,
                COUNT(*) OVER (
                    PARTITION BY COALESCE(f.codigo_item, f.descricao_item)
                ) AS vezes_vendido
            FROM faturamento f
            LEFT JOIN produtos p ON p.codigo = f.codigo_item
            LEFT JOIN segmentos s ON s.id = p.segmento_id
            WHERE f.cliente_id = ?
              AND (
                    f.codigo_item IS NOT NULL
                    OR f.descricao_item IS NOT NULL
                  )
        )
        SELECT
            codigo_item,
            descricao_item,
            segmento,
            data_emissao AS data_ultima_venda,
            quantidade AS qtd_ultima_venda,
            valor_unitario AS preco_ultima_venda,
            valor_total AS valor_total_ultima_venda,
            vezes_vendido
        FROM base
        WHERE rn = 1
    """
    params: list[Any] = [cliente_id]

    filters = []
    if termo:
        filters.append("(codigo_item LIKE ? OR descricao_item LIKE ?)")
        like = f"%{termo}%"
        params.extend([like, like])
    if segmento:
        filters.append("segmento = ?")
        params.append(segmento)

    if filters:
        sql += " AND " + " AND ".join(filters)

    sql += " ORDER BY data_ultima_venda DESC, descricao_item ASC"
    return list(conn.execute(sql, params))


def ultima_venda_produto_cliente(
    conn: sqlite3.Connection,
    cliente_id: int,
    codigo_item: str | None = None,
    descricao_item: str | None = None,
) -> sqlite3.Row | None:
    """Retorna a última venda do produto para o cliente informado."""
    if codigo_item:
        row = conn.execute(
            """
            SELECT
                codigo_item,
                descricao_item,
                data_emissao,
                quantidade,
                valor_unitario,
                valor_total,
                numero_nota
            FROM faturamento
            WHERE cliente_id = ?
              AND codigo_item = ?
            ORDER BY data_emissao DESC, id DESC
            LIMIT 1
            """,
            (cliente_id, codigo_item),
        ).fetchone()
        return row

    if descricao_item:
        row = conn.execute(
            """
            SELECT
                codigo_item,
                descricao_item,
                data_emissao,
                quantidade,
                valor_unitario,
                valor_total,
                numero_nota
            FROM faturamento
            WHERE cliente_id = ?
              AND descricao_item = ?
            ORDER BY data_emissao DESC, id DESC
            LIMIT 1
            """,
            (cliente_id, descricao_item),
        ).fetchone()
        return row

    return None
