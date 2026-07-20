"""Persistência e consulta de orçamentos (histórico)."""

from __future__ import annotations

import json
import sqlite3
from copy import deepcopy
from datetime import datetime
from typing import Any

# Códigos persistidos no banco
STATUS_RASCUNHO = "rascunho"
STATUS_GERADO = "gerado"
STATUS_APROVADO = "aprovado"
STATUS_CANCELADO = "cancelado"

STATUS_LABELS: dict[str, str] = {
    STATUS_RASCUNHO: "Rascunho",
    STATUS_GERADO: "Orçamento gerado",
    "finalizado": "Orçamento gerado",  # legado
    STATUS_APROVADO: "Aprovado",
    STATUS_CANCELADO: "Cancelado",
}


def label_status(status: str | None) -> str:
    if not status:
        return "-"
    return STATUS_LABELS.get(str(status), str(status))


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _row_to_dict(row: sqlite3.Row | None) -> dict | None:
    if row is None:
        return None
    return dict(row)


def _cols(conn: sqlite3.Connection, table: str) -> set[str]:
    return {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}


def salvar_orcamento(
    conn: sqlite3.Connection,
    proposta: dict,
    *,
    status: str = "rascunho",
) -> int:
    """Insere ou atualiza orçamento + itens. Retorna id."""
    cliente = proposta.get("cliente") or {}
    cliente_id = cliente.get("id")
    avulso_nome = None
    avulso_doc = None
    if not cliente_id:
        avulso_nome = cliente.get("nome")
        avulso_doc = cliente.get("cnpj_cpf")

    valor_total = sum(i.get("valor_venda_total", 0) or 0 for i in proposta.get("itens") or [])
    lucro_total = sum(i.get("lucro_total", 0) or 0 for i in proposta.get("itens") or [])
    frete_total = sum(i.get("frete_item", 0) or 0 for i in proposta.get("itens") or [])
    agora = _now()
    cols = _cols(conn, "orcamentos")

    # Coluna legada `tipo` em bancos antigos: CHECK só aceita etiqueta|suprimentos
    # (nunca "misto" — orçamentos mistos usam o tipo do 1º item).
    itens = proposta.get("itens") or []
    tipos_validos = [
        i.get("tipo_item")
        for i in itens
        if i.get("tipo_item") in ("etiqueta", "suprimentos")
    ]
    tipo_legado = tipos_validos[0] if tipos_validos else "etiqueta"

    orc_id = proposta.get("id")
    if orc_id:
        sets = [
            "numero=?",
            "cliente_id=?",
            "cliente_avulso_nome=?",
            "cliente_avulso_documento=?",
            "solicitante=?",
            "status=?",
            "validade_proposta=?",
            "prazo_pagamento=?",
            "prazo_entrega=?",
            "frete_tipo=?",
            "frete_taxa=?",
            "impostos=?",
            "informacoes_adicionais=?",
            "orcamentista_nome=?",
            "orcamentista_cargo=?",
            "orcamentista_telefone=?",
            "orcamentista_email=?",
            "lucro_total=?",
            "valor_total=?",
            "frete_total=?",
            "atualizado_em=?",
        ]
        vals: list[Any] = [
            proposta.get("numero"),
            cliente_id,
            avulso_nome,
            avulso_doc,
            proposta.get("solicitante"),
            status,
            proposta.get("validade_proposta"),
            proposta.get("prazo_pagamento"),
            proposta.get("prazo_entrega"),
            proposta.get("frete_tipo"),
            _parse_float(proposta.get("frete_taxa")),
            proposta.get("impostos"),
            proposta.get("informacoes_adicionais"),
            proposta.get("orcamentista_nome"),
            proposta.get("orcamentista_cargo"),
            proposta.get("orcamentista_telefone"),
            proposta.get("orcamentista_email"),
            lucro_total,
            valor_total,
            frete_total,
            agora,
        ]
        if "tipo" in cols:
            sets.insert(5, "tipo=?")
            vals.insert(5, tipo_legado)
        if "empresa_cnpj" in cols:
            # inserir antes de atualizado_em
            sets.insert(-1, "empresa_cnpj=?")
            vals.insert(-1, proposta.get("empresa_cnpj") or None)
        vals.append(orc_id)
        conn.execute(
            f"UPDATE orcamentos SET {', '.join(sets)} WHERE id=?",
            vals,
        )
        conn.execute("DELETE FROM orcamento_itens WHERE orcamento_id = ?", (orc_id,))
    else:
        fields = [
            "numero",
            "cliente_id",
            "cliente_avulso_nome",
            "cliente_avulso_documento",
            "solicitante",
            "status",
            "validade_proposta",
            "prazo_pagamento",
            "prazo_entrega",
            "frete_tipo",
            "frete_taxa",
            "impostos",
            "informacoes_adicionais",
            "orcamentista_nome",
            "orcamentista_cargo",
            "orcamentista_telefone",
            "orcamentista_email",
            "lucro_total",
            "valor_total",
            "frete_total",
            "criado_em",
            "atualizado_em",
        ]
        vals = [
            proposta.get("numero"),
            cliente_id,
            avulso_nome,
            avulso_doc,
            proposta.get("solicitante"),
            status,
            proposta.get("validade_proposta"),
            proposta.get("prazo_pagamento"),
            proposta.get("prazo_entrega"),
            proposta.get("frete_tipo"),
            _parse_float(proposta.get("frete_taxa")),
            proposta.get("impostos"),
            proposta.get("informacoes_adicionais"),
            proposta.get("orcamentista_nome"),
            proposta.get("orcamentista_cargo"),
            proposta.get("orcamentista_telefone"),
            proposta.get("orcamentista_email"),
            lucro_total,
            valor_total,
            frete_total,
            agora,
            agora,
        ]
        if "tipo" in cols:
            fields.insert(5, "tipo")
            vals.insert(5, tipo_legado)
        if "empresa_cnpj" in cols:
            # antes de criado_em / atualizado_em
            fields.insert(-2, "empresa_cnpj")
            vals.insert(-2, proposta.get("empresa_cnpj") or None)
        placeholders = ", ".join("?" for _ in fields)
        cur = conn.execute(
            f"INSERT INTO orcamentos ({', '.join(fields)}) VALUES ({placeholders})",
            vals,
        )
        orc_id = int(cur.lastrowid)

    for item in proposta.get("itens") or []:
        params = {
            "parametros": item.get("parametros"),
            "calculo": item.get("calculo"),
        }
        conn.execute(
            """
            INSERT INTO orcamento_itens (
                orcamento_id, tipo_item, codigo_item, descricao, segmento, unidade,
                quantidade, custo_unitario, preco_unitario, preco_total,
                lucro_unitario, lucro_total, frete_item, parametros_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                orc_id,
                item.get("tipo_item") or "etiqueta",
                item.get("codigo_item"),
                item.get("descricao") or "",
                item.get("segmento"),
                item.get("unidade"),
                float(item.get("quantidade") or 0),
                item.get("custo_unitario"),
                float(item.get("preco_unitario") or 0),
                float(item.get("valor_venda_total") or item.get("preco_total") or 0),
                item.get("lucro_unitario"),
                float(item.get("lucro_total") or 0),
                float(item.get("frete_item") or 0),
                json.dumps(params, ensure_ascii=False, default=str),
            ),
        )

    proposta["id"] = orc_id
    conn.commit()
    return orc_id


def buscar_orcamentos(
    conn: sqlite3.Connection,
    *,
    termo: str | None = None,
    cliente: str | None = None,
    status: str | None = None,
    dia: int | None = None,
    mes: int | None = None,
    ano: int | None = None,
    limite: int = 500,
) -> list[sqlite3.Row]:
    """
    Lista orçamentos com filtros opcionais.
    Dia/mês/ano usam a data de criação (criado_em).
    """
    termo = (termo or "").strip()
    cliente = (cliente or "").strip()
    status = (status or "").strip() or None
    if status == "gerado":
        # inclui legado finalizado
        status_filter = ("gerado", "finalizado")
    elif status:
        status_filter = (status,)
    else:
        status_filter = None

    sql = """
        SELECT
            o.id, o.numero, o.status, o.valor_total, o.lucro_total, o.frete_total,
            o.criado_em, o.atualizado_em, o.solicitante,
            COALESCE(c.nome, o.cliente_avulso_nome) AS cliente_nome,
            COALESCE(c.cnpj_cpf, o.cliente_avulso_documento) AS cliente_doc
        FROM orcamentos o
        LEFT JOIN clientes c ON c.id = o.cliente_id
        WHERE 1=1
    """
    params: list[Any] = []
    if termo:
        like = f"%{termo}%"
        sql += """
            AND (
                o.numero LIKE ?
                OR COALESCE(c.nome, o.cliente_avulso_nome, '') LIKE ?
                OR COALESCE(c.cnpj_cpf, o.cliente_avulso_documento, '') LIKE ?
            )
        """
        params.extend([like, like, like])
    if cliente:
        like_c = f"%{cliente}%"
        sql += """
            AND (
                COALESCE(c.nome, o.cliente_avulso_nome, '') LIKE ?
                OR COALESCE(c.cnpj_cpf, o.cliente_avulso_documento, '') LIKE ?
            )
        """
        params.extend([like_c, like_c])
    if status_filter:
        placeholders = ", ".join("?" for _ in status_filter)
        sql += f" AND o.status IN ({placeholders})"
        params.extend(status_filter)
    if ano:
        sql += " AND CAST(strftime('%Y', o.criado_em) AS INTEGER) = ?"
        params.append(int(ano))
    if mes:
        sql += " AND CAST(strftime('%m', o.criado_em) AS INTEGER) = ?"
        params.append(int(mes))
    if dia:
        sql += " AND CAST(strftime('%d', o.criado_em) AS INTEGER) = ?"
        params.append(int(dia))

    sql += " ORDER BY o.atualizado_em DESC, o.id DESC LIMIT ?"
    params.append(limite)
    return list(conn.execute(sql, params))


def atualizar_status_orcamento(
    conn: sqlite3.Connection, orcamento_id: int, status: str
) -> None:
    conn.execute(
        """
        UPDATE orcamentos
        SET status = ?, atualizado_em = ?
        WHERE id = ?
        """,
        (status, _now(), orcamento_id),
    )
    conn.commit()


def anos_orcamentos(conn: sqlite3.Connection) -> list[int]:
    rows = conn.execute(
        """
        SELECT DISTINCT CAST(strftime('%Y', criado_em) AS INTEGER) AS ano
        FROM orcamentos
        WHERE criado_em IS NOT NULL AND TRIM(criado_em) != ''
        ORDER BY ano DESC
        """
    ).fetchall()
    return [int(r["ano"]) for r in rows if r["ano"]]


def obter_orcamento(conn: sqlite3.Connection, orcamento_id: int) -> dict | None:
    row = conn.execute(
        """
        SELECT o.*,
               COALESCE(c.nome, o.cliente_avulso_nome) AS cliente_nome,
               COALESCE(c.cnpj_cpf, o.cliente_avulso_documento) AS cliente_doc,
               c.id AS cliente_id_resolvido,
               c.uf AS cliente_uf
        FROM orcamentos o
        LEFT JOIN clientes c ON c.id = o.cliente_id
        WHERE o.id = ?
        """,
        (orcamento_id,),
    ).fetchone()
    if not row:
        return None
    orc = dict(row)
    itens = list(
        conn.execute(
            """
            SELECT * FROM orcamento_itens
            WHERE orcamento_id = ?
            ORDER BY id
            """,
            (orcamento_id,),
        )
    )
    orc["itens"] = [dict(i) for i in itens]
    return orc


def orcamento_para_proposta(orc: dict) -> dict:
    """Converte registro do banco para o dict usado na tela Novo Orçamento."""
    cliente = None
    if orc.get("cliente_id") or orc.get("cliente_id_resolvido"):
        cliente = {
            "id": orc.get("cliente_id") or orc.get("cliente_id_resolvido"),
            "nome": orc.get("cliente_nome"),
            "cnpj_cpf": orc.get("cliente_doc"),
            "uf": orc.get("cliente_uf"),
        }
    elif orc.get("cliente_avulso_nome") or orc.get("cliente_nome"):
        cliente = {
            "id": None,
            "nome": orc.get("cliente_avulso_nome") or orc.get("cliente_nome"),
            "cnpj_cpf": orc.get("cliente_avulso_documento") or orc.get("cliente_doc"),
            "uf": None,
        }

    itens = []
    for it in orc.get("itens") or []:
        extra: dict = {}
        raw = it.get("parametros_json")
        if raw:
            try:
                extra = json.loads(raw)
            except (TypeError, json.JSONDecodeError):
                extra = {}
        itens.append(
            {
                "tipo_item": it.get("tipo_item"),
                "codigo_item": it.get("codigo_item"),
                "descricao": it.get("descricao"),
                "segmento": it.get("segmento"),
                "unidade": it.get("unidade"),
                "quantidade": it.get("quantidade"),
                "custo_unitario": it.get("custo_unitario"),
                "preco_unitario": it.get("preco_unitario"),
                "valor_venda_total": it.get("preco_total"),
                "lucro_unitario": it.get("lucro_unitario"),
                "lucro_total": it.get("lucro_total"),
                "frete_item": it.get("frete_item") or 0,
                "parametros": extra.get("parametros"),
                "calculo": extra.get("calculo"),
            }
        )

    return {
        "id": orc.get("id"),
        "numero": orc.get("numero"),
        "cliente": cliente,
        "solicitante": orc.get("solicitante") or "",
        "itens": itens,
        "validade_proposta": orc.get("validade_proposta"),
        "prazo_pagamento": orc.get("prazo_pagamento"),
        "prazo_entrega": orc.get("prazo_entrega"),
        "frete_tipo": orc.get("frete_tipo"),
        "frete_taxa": orc.get("frete_taxa") if orc.get("frete_taxa") is not None else "",
        "impostos": orc.get("impostos"),
        "informacoes_adicionais": orc.get("informacoes_adicionais"),
        "orcamentista_nome": orc.get("orcamentista_nome") or "",
        "orcamentista_cargo": orc.get("orcamentista_cargo") or "",
        "orcamentista_telefone": orc.get("orcamentista_telefone") or "",
        "orcamentista_email": orc.get("orcamentista_email") or "",
        "empresa_cnpj": orc.get("empresa_cnpj") or "",
        "status": orc.get("status"),
    }


def clonar_para_novo(orc: dict) -> dict:
    """Cópia editável sem id/número (vira novo orçamento)."""
    proposta = orcamento_para_proposta(orc)
    proposta["id"] = None
    proposta["numero"] = None
    proposta["status"] = None
    proposta["itens"] = deepcopy(proposta.get("itens") or [])
    return proposta


def _parse_float(valor) -> float | None:
    if valor is None or valor == "":
        return None
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None
