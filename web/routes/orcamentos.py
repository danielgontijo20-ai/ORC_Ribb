from __future__ import annotations

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from src.db.database import connect
from src.services.configuracoes import carregar_config
from src.services.orcamentos import (
    STATUS_APROVADO,
    atualizar_status_orcamento,
    buscar_orcamentos,
    label_status,
    obter_orcamento,
    orcamento_para_proposta,
)
from src.services.pdf_proposta import gerar_pdf_proposta
from src.services.usuarios import usuario_tem_permissao
from web.deps import get_current_user
from web.templating import render

router = APIRouter(prefix="/orcamentos")


@router.get("", response_class=HTMLResponse)
def lista(
    request: Request,
    termo: str = Query(""),
    cliente: str = Query(""),
    status: str = Query(""),
):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    if not usuario_tem_permissao(user, "orcamento.ver"):
        return HTMLResponse("Sem permissão.", status_code=403)

    with connect() as conn:
        rows = buscar_orcamentos(
            conn,
            termo=termo or None,
            cliente=cliente or None,
            status=status or None,
            limite=200,
        )
        lista = [dict(r) for r in rows]
        for r in lista:
            r["status_label"] = label_status(r.get("status"))

    return render(
        request,
        "orcamentos_lista.html",
        {
            "user": user,
            "lista": lista,
            "termo": termo,
            "cliente": cliente,
            "status": status,
            "pode_aprovar": usuario_tem_permissao(user, "orcamento.aprovar"),
            "pode_pdf": usuario_tem_permissao(user, "orcamento.pdf"),
        },
    )


@router.get("/novo", response_class=HTMLResponse)
def novo_placeholder(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    if not usuario_tem_permissao(user, "orcamento.criar"):
        return HTMLResponse("Sem permissão.", status_code=403)
    return render(request, "orcamento_novo.html", {"user": user})


@router.get("/{orcamento_id}", response_class=HTMLResponse)
def detalhe(request: Request, orcamento_id: int):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    if not usuario_tem_permissao(user, "orcamento.ver"):
        return HTMLResponse("Sem permissão.", status_code=403)

    with connect() as conn:
        orc = obter_orcamento(conn, orcamento_id)
    if not orc:
        return HTMLResponse("Orçamento não encontrado.", status_code=404)

    return render(
        request,
        "orcamento_detalhe.html",
        {
            "user": user,
            "orc": orc,
            "status_label": label_status(orc.get("status")),
            "pode_aprovar": usuario_tem_permissao(user, "orcamento.aprovar")
            and (orc.get("status") or "").lower() in ("gerado", "finalizado"),
            "pode_pdf": usuario_tem_permissao(user, "orcamento.pdf"),
        },
    )


@router.post("/{orcamento_id}/aprovar")
def aprovar(request: Request, orcamento_id: int):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    if not usuario_tem_permissao(user, "orcamento.aprovar"):
        return HTMLResponse("Sem permissão.", status_code=403)
    with connect() as conn:
        atualizar_status_orcamento(conn, orcamento_id, STATUS_APROVADO)
    return RedirectResponse(f"/orcamentos/{orcamento_id}", status_code=303)


@router.get("/{orcamento_id}/pdf")
def pdf(request: Request, orcamento_id: int):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    if not usuario_tem_permissao(user, "orcamento.pdf"):
        return HTMLResponse("Sem permissão.", status_code=403)

    with connect() as conn:
        orc = obter_orcamento(conn, orcamento_id)
        cfg = carregar_config(conn)
    if not orc:
        return HTMLResponse("Orçamento não encontrado.", status_code=404)

    prop = orcamento_para_proposta(orc)
    cliente = prop.get("cliente") or {}
    frete_exibicao = prop.get("frete_tipo", "CIF")
    if frete_exibicao == "Taxa" and prop.get("frete_taxa"):
        frete_exibicao = f"Taxa: {prop.get('frete_taxa')}"

    pdf_bytes = gerar_pdf_proposta(
        empresa=cfg,
        orcamento={
            "numero": prop.get("numero"),
            "cliente_nome": cliente.get("nome"),
            "cliente_doc": cliente.get("cnpj_cpf"),
            "solicitante": prop.get("solicitante"),
            "validade_proposta": prop.get("validade_proposta"),
            "prazo_pagamento": prop.get("prazo_pagamento"),
            "prazo_entrega": prop.get("prazo_entrega"),
            "frete_tipo": frete_exibicao,
            "impostos": prop.get("impostos"),
            "informacoes_adicionais": prop.get("informacoes_adicionais"),
            "orcamentista_nome": prop.get("orcamentista_nome"),
            "orcamentista_cargo": prop.get("orcamentista_cargo"),
            "orcamentista_telefone": prop.get("orcamentista_telefone"),
            "orcamentista_email": prop.get("orcamentista_email"),
            "valor_total": orc.get("valor_total") or 0,
        },
        itens=prop.get("itens") or [],
        logo_cabecalho=cfg.get("logo_cabecalho") or None,
        logo_rodape=cfg.get("logo_rodape") or None,
    )
    nome = f"{prop.get('numero') or orcamento_id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{nome}"'},
    )
