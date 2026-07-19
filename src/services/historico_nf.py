"""Histórico de vendas agrupado por número de NF."""

from __future__ import annotations

import sqlite3
from typing import Any


def listar_vendas_por_cliente(
    conn: sqlite3.Connection,
    cliente_id: int | None = None,
    termo_cliente: str | None = None,
    limite_notas: int = 100,
) -> list[dict[str, Any]]:
    """
    Retorna notas (mais recentes primeiro), cada uma com seus itens.
    """
    params: list[Any] = []
    where = ["1=1"]
    if cliente_id:
        where.append("f.cliente_id = ?")
        params.append(cliente_id)
    if termo_cliente:
        where.append("(f.nome_cliente LIKE ? OR f.cnpj_cpf LIKE ?)")
        like = f"%{termo_cliente}%"
        params.extend([like, like])

    sql_notas = f"""
        SELECT
            f.numero_nota,
            f.cliente_id,
            f.nome_cliente,
            f.cnpj_cpf,
            MAX(f.data_emissao) AS data_emissao,
            SUM(COALESCE(f.valor_total, 0)) AS valor_nota
        FROM faturamento f
        WHERE {' AND '.join(where)}
          AND f.numero_nota IS NOT NULL
        GROUP BY f.numero_nota, f.cliente_id, f.nome_cliente, f.cnpj_cpf
        ORDER BY data_emissao DESC, f.numero_nota DESC
        LIMIT ?
    """
    params.append(limite_notas)
    notas = [dict(r) for r in conn.execute(sql_notas, params)]

    for nota in notas:
        itens = conn.execute(
            """
            SELECT codigo_item, descricao_item, unidade, quantidade,
                   valor_unitario, valor_total, data_emissao
            FROM faturamento
            WHERE numero_nota = ?
              AND COALESCE(cliente_id, -1) = COALESCE(?, -1)
            ORDER BY id
            """,
            (nota["numero_nota"], nota["cliente_id"]),
        ).fetchall()
        nota["itens"] = [dict(i) for i in itens]
    return notas
