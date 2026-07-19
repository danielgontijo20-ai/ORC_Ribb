from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from src.db.database import connect
from src.services.cadastros import (
    listar_caixas,
    listar_facas,
    listar_materias_primas,
    listar_suprimentos,
    listar_tubetes,
)
from src.services.clientes import buscar_clientes, contar_clientes
from src.services.configuracoes import carregar_config, salvar_config
from src.services.usuarios import usuario_tem_permissao
from web.deps import get_current_user
from web.templating import render

router = APIRouter(prefix="/cadastros")

_NATIVOS_KEYS = (
    "empresa_nome",
    "empresa_cnpj",
    "empresa_telefone",
    "empresa_email",
    "frete_padrao",
    "perda_padrao",
    "lucro_etiqueta_padrao",
    "lucro_suprimentos_padrao",
    "difal_padrao",
    "unidade_etiqueta",
    "unidade_suprimentos",
    "validade_proposta",
    "prazo_pagamento",
    "prazo_entrega",
    "frete_tipo",
    "impostos",
    "informacoes_adicionais",
    "orcamentista_nome",
    "orcamentista_cargo",
    "orcamentista_telefone",
    "orcamentista_email",
)


@router.get("", response_class=HTMLResponse)
def hub(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    if not usuario_tem_permissao(user, "cadastros.ver"):
        return HTMLResponse("Sem permissão.", status_code=403)
    return render(
        request,
        "cadastros_hub.html",
        {
            "user": user,
            "pode_editar": usuario_tem_permissao(user, "cadastros.editar"),
        },
    )


@router.get("/nativos", response_class=HTMLResponse)
def nativos_get(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    if not usuario_tem_permissao(user, "cadastros.ver"):
        return HTMLResponse("Sem permissão.", status_code=403)
    with connect() as conn:
        cfg = carregar_config(conn)
    flash_ok = request.session.pop("cad_flash_ok", None)
    flash_err = request.session.pop("cad_flash_err", None)
    return render(
        request,
        "cadastros_nativos.html",
        {
            "user": user,
            "cfg": cfg,
            "pode_editar": usuario_tem_permissao(user, "cadastros.editar"),
            "flash_ok": flash_ok,
            "flash_err": flash_err,
        },
    )


@router.post("/nativos")
async def nativos_post(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    if not usuario_tem_permissao(user, "cadastros.editar"):
        return HTMLResponse("Sem permissão.", status_code=403)
    form = await request.form()
    dados = {k: str(form.get(k) or "").strip() for k in _NATIVOS_KEYS}
    with connect() as conn:
        salvar_config(conn, dados)
    request.session["cad_flash_ok"] = "Valores nativos salvos com sucesso."
    return RedirectResponse("/cadastros/nativos", status_code=303)


@router.get("/clientes", response_class=HTMLResponse)
def clientes(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    if not usuario_tem_permissao(user, "cadastros.ver"):
        return HTMLResponse("Sem permissão.", status_code=403)
    with connect() as conn:
        total = contar_clientes(conn)
        rows = [dict(r) for r in buscar_clientes(conn, limite=500)]
    return render(
        request,
        "cadastros_lista.html",
        {
            "user": user,
            "titulo": "Clientes",
            "total": total,
            "colunas": ["id", "cnpj_cpf", "nome", "uf"],
            "linhas": rows,
        },
    )


@router.get("/materias", response_class=HTMLResponse)
def materias(request: Request):
    return _lista_generica(request, "Matérias-primas", listar_materias_primas)


@router.get("/tubetes", response_class=HTMLResponse)
def tubetes(request: Request):
    return _lista_generica(request, "Tubetes", listar_tubetes)


@router.get("/facas", response_class=HTMLResponse)
def facas(request: Request):
    return _lista_generica(request, "Facas", listar_facas)


@router.get("/caixas", response_class=HTMLResponse)
def caixas(request: Request):
    return _lista_generica(request, "Caixas", listar_caixas)


@router.get("/suprimentos", response_class=HTMLResponse)
def suprimentos(request: Request):
    return _lista_generica(request, "Suprimentos", listar_suprimentos)


def _lista_generica(request: Request, titulo: str, list_fn):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    if not usuario_tem_permissao(user, "cadastros.ver"):
        return HTMLResponse("Sem permissão.", status_code=403)
    with connect() as conn:
        rows = [dict(r) for r in list_fn(conn)]
    colunas = list(rows[0].keys()) if rows else ["id"]
    return render(
        request,
        "cadastros_lista.html",
        {
            "user": user,
            "titulo": titulo,
            "total": len(rows),
            "colunas": colunas,
            "linhas": rows,
        },
    )
