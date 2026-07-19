from __future__ import annotations

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from src.db.database import connect
from src.services.cadastros import (
    excluir_caixa,
    excluir_cliente,
    excluir_faca,
    excluir_materia,
    excluir_suprimento,
    excluir_tubete,
    listar_caixas,
    listar_facas,
    listar_materias_primas,
    listar_suprimentos,
    listar_tubetes,
    obter_suprimento,
    salvar_caixa,
    salvar_faca,
    salvar_materia,
    salvar_suprimento,
    salvar_tubete,
    upsert_cliente,
)
from src.services.clientes import buscar_clientes, contar_clientes, obter_cliente
from src.services.configuracoes import carregar_config, salvar_config
from src.services.usuarios import usuario_tem_permissao
from web.deps import get_current_user
from web.proposta_session import parse_float
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


def _auth(request: Request, *, editar: bool = False):
    user = get_current_user(request)
    if not user:
        return None, RedirectResponse("/login", status_code=303)
    if not usuario_tem_permissao(user, "cadastros.ver"):
        return None, HTMLResponse("Sem permissão.", status_code=403)
    if editar and not usuario_tem_permissao(user, "cadastros.editar"):
        return None, HTMLResponse("Sem permissão para editar.", status_code=403)
    return user, None


def _flash(request: Request):
    return (
        request.session.pop("cad_flash_ok", None),
        request.session.pop("cad_flash_err", None),
    )


def _ctx_base(request: Request, user) -> dict:
    ok, err = _flash(request)
    return {
        "user": user,
        "pode_editar": usuario_tem_permissao(user, "cadastros.editar"),
        "flash_ok": ok,
        "flash_err": err,
    }


def _obter_por_id(conn, table: str, item_id: int):
    return conn.execute(
        f"SELECT * FROM {table} WHERE id = ? LIMIT 1", (item_id,)
    ).fetchone()


@router.get("", response_class=HTMLResponse)
def hub(request: Request):
    user, err = _auth(request)
    if err:
        return err
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
    user, err = _auth(request)
    if err:
        return err
    with connect() as conn:
        cfg = carregar_config(conn)
    ctx = _ctx_base(request, user)
    ctx["cfg"] = cfg
    return render(request, "cadastros_nativos.html", ctx)


@router.post("/nativos")
async def nativos_post(request: Request):
    user, err = _auth(request, editar=True)
    if err:
        return err
    form = await request.form()
    dados = {k: str(form.get(k) or "").strip() for k in _NATIVOS_KEYS}
    with connect() as conn:
        salvar_config(conn, dados)
    request.session["cad_flash_ok"] = "Valores nativos salvos com sucesso."
    return RedirectResponse("/cadastros/nativos", status_code=303)


# ---- Clientes ----


@router.get("/clientes", response_class=HTMLResponse)
def clientes_lista(request: Request, termo: str = Query("")):
    user, err = _auth(request)
    if err:
        return err
    with connect() as conn:
        rows = [dict(r) for r in buscar_clientes(conn, termo=termo or None, limite=500)]
        total = contar_clientes(conn, termo=termo or None)
    ctx = _ctx_base(request, user)
    ctx.update(
        {
            "titulo": "Clientes",
            "slug": "clientes",
            "total": total,
            "termo": termo,
            "linhas": rows,
            "colunas": [
                ("id", "ID"),
                ("cnpj_cpf", "CNPJ/CPF"),
                ("nome", "Nome"),
                ("uf", "UF"),
            ],
        }
    )
    return render(request, "cadastros_crud_lista.html", ctx)


@router.get("/clientes/novo", response_class=HTMLResponse)
def clientes_novo(request: Request):
    user, err = _auth(request, editar=True)
    if err:
        return err
    ctx = _ctx_base(request, user)
    ctx.update({"titulo": "Novo cliente", "slug": "clientes", "item": None})
    return render(request, "cadastros_form_cliente.html", ctx)


@router.get("/clientes/{item_id}", response_class=HTMLResponse)
def clientes_editar(request: Request, item_id: int):
    user, err = _auth(request)
    if err:
        return err
    with connect() as conn:
        row = obter_cliente(conn, item_id)
    if not row:
        return HTMLResponse("Cliente não encontrado.", status_code=404)
    ctx = _ctx_base(request, user)
    ctx.update(
        {
            "titulo": "Editar cliente",
            "slug": "clientes",
            "item": dict(row),
        }
    )
    return render(request, "cadastros_form_cliente.html", ctx)


@router.post("/clientes/salvar")
async def clientes_salvar(request: Request):
    user, err = _auth(request, editar=True)
    if err:
        return err
    form = await request.form()
    item_id = str(form.get("id") or "").strip()
    nome = str(form.get("nome") or "").strip()
    cnpj = str(form.get("cnpj_cpf") or "").strip()
    uf = str(form.get("uf") or "").strip() or None
    if not nome or not cnpj:
        request.session["cad_flash_err"] = "Informe nome e CNPJ/CPF."
        return RedirectResponse(
            f"/cadastros/clientes/{item_id}" if item_id else "/cadastros/clientes/novo",
            status_code=303,
        )
    with connect() as conn:
        upsert_cliente(
            conn,
            cnpj_cpf=cnpj,
            nome=nome,
            uf=uf,
            cliente_id=int(item_id) if item_id else None,
        )
    request.session["cad_flash_ok"] = "Cliente salvo com sucesso."
    return RedirectResponse("/cadastros/clientes", status_code=303)


@router.post("/clientes/{item_id}/excluir")
def clientes_excluir(request: Request, item_id: int):
    user, err = _auth(request, editar=True)
    if err:
        return err
    with connect() as conn:
        excluir_cliente(conn, item_id)
    request.session["cad_flash_ok"] = "Cliente excluído."
    return RedirectResponse("/cadastros/clientes", status_code=303)


# ---- Matérias ----


@router.get("/materias", response_class=HTMLResponse)
def materias_lista(request: Request):
    user, err = _auth(request)
    if err:
        return err
    with connect() as conn:
        rows = [dict(r) for r in listar_materias_primas(conn)]
    ctx = _ctx_base(request, user)
    ctx.update(
        {
            "titulo": "Matérias-primas",
            "slug": "materias",
            "total": len(rows),
            "termo": "",
            "linhas": rows,
            "colunas": [
                ("codigo", "Código"),
                ("nome", "Nome"),
                ("nome_exibicao_orc", "Nome ORC"),
                ("custo", "Custo"),
            ],
        }
    )
    return render(request, "cadastros_crud_lista.html", ctx)


@router.get("/materias/novo", response_class=HTMLResponse)
def materias_novo(request: Request):
    user, err = _auth(request, editar=True)
    if err:
        return err
    ctx = _ctx_base(request, user)
    ctx.update({"titulo": "Nova matéria-prima", "slug": "materias", "item": None})
    return render(request, "cadastros_form_materia.html", ctx)


@router.get("/materias/{item_id}", response_class=HTMLResponse)
def materias_editar(request: Request, item_id: int):
    user, err = _auth(request)
    if err:
        return err
    with connect() as conn:
        row = _obter_por_id(conn, "materias_primas", item_id)
    if not row:
        return HTMLResponse("Registro não encontrado.", status_code=404)
    ctx = _ctx_base(request, user)
    ctx.update({"titulo": "Editar matéria-prima", "slug": "materias", "item": dict(row)})
    return render(request, "cadastros_form_materia.html", ctx)


@router.post("/materias/salvar")
async def materias_salvar(request: Request):
    user, err = _auth(request, editar=True)
    if err:
        return err
    form = await request.form()
    item_id = str(form.get("id") or "").strip()
    codigo = str(form.get("codigo") or "").strip()
    nome = str(form.get("nome") or "").strip()
    nome_orc = str(form.get("nome_exibicao_orc") or "").strip()
    custo = parse_float(form.get("custo"))
    preco = parse_float(form.get("preco_compra"))
    obs = str(form.get("observacoes") or "").strip() or None
    if not codigo or not nome or custo is None:
        request.session["cad_flash_err"] = "Informe código, nome e custo."
        return RedirectResponse(
            f"/cadastros/materias/{item_id}" if item_id else "/cadastros/materias/novo",
            status_code=303,
        )
    with connect() as conn:
        salvar_materia(
            conn,
            codigo=codigo,
            nome=nome,
            nome_exibicao_orc=nome_orc or nome,
            preco_compra=preco,
            custo=float(custo),
            observacoes=obs,
            materia_id=int(item_id) if item_id else None,
        )
    request.session["cad_flash_ok"] = "Matéria-prima salva."
    return RedirectResponse("/cadastros/materias", status_code=303)


@router.post("/materias/{item_id}/excluir")
def materias_excluir(request: Request, item_id: int):
    user, err = _auth(request, editar=True)
    if err:
        return err
    with connect() as conn:
        excluir_materia(conn, item_id)
    request.session["cad_flash_ok"] = "Matéria-prima excluída."
    return RedirectResponse("/cadastros/materias", status_code=303)


# ---- Tubetes ----


@router.get("/tubetes", response_class=HTMLResponse)
def tubetes_lista(request: Request):
    user, err = _auth(request)
    if err:
        return err
    with connect() as conn:
        rows = [dict(r) for r in listar_tubetes(conn)]
    ctx = _ctx_base(request, user)
    ctx.update(
        {
            "titulo": "Tubetes",
            "slug": "tubetes",
            "total": len(rows),
            "termo": "",
            "linhas": rows,
            "colunas": [
                ("codigo", "Código"),
                ("nome", "Nome"),
                ("nome_exibicao_orc", "Nome ORC"),
                ("custo", "Custo"),
            ],
        }
    )
    return render(request, "cadastros_crud_lista.html", ctx)


@router.get("/tubetes/novo", response_class=HTMLResponse)
def tubetes_novo(request: Request):
    user, err = _auth(request, editar=True)
    if err:
        return err
    ctx = _ctx_base(request, user)
    ctx.update({"titulo": "Novo tubete", "slug": "tubetes", "item": None})
    return render(request, "cadastros_form_tubete.html", ctx)


@router.get("/tubetes/{item_id}", response_class=HTMLResponse)
def tubetes_editar(request: Request, item_id: int):
    user, err = _auth(request)
    if err:
        return err
    with connect() as conn:
        row = _obter_por_id(conn, "tubetes", item_id)
    if not row:
        return HTMLResponse("Registro não encontrado.", status_code=404)
    ctx = _ctx_base(request, user)
    ctx.update({"titulo": "Editar tubete", "slug": "tubetes", "item": dict(row)})
    return render(request, "cadastros_form_tubete.html", ctx)


@router.post("/tubetes/salvar")
async def tubetes_salvar(request: Request):
    user, err = _auth(request, editar=True)
    if err:
        return err
    form = await request.form()
    item_id = str(form.get("id") or "").strip()
    codigo = str(form.get("codigo") or "").strip()
    nome = str(form.get("nome") or "").strip()
    nome_orc = str(form.get("nome_exibicao_orc") or "").strip()
    custo = parse_float(form.get("custo"))
    preco = parse_float(form.get("preco_compra"))
    if not codigo or not nome or custo is None:
        request.session["cad_flash_err"] = "Informe código, nome e custo."
        return RedirectResponse(
            f"/cadastros/tubetes/{item_id}" if item_id else "/cadastros/tubetes/novo",
            status_code=303,
        )
    with connect() as conn:
        salvar_tubete(
            conn,
            codigo=codigo,
            nome=nome,
            nome_exibicao_orc=nome_orc or nome,
            preco_compra=preco,
            custo=float(custo),
            tubete_id=int(item_id) if item_id else None,
        )
    request.session["cad_flash_ok"] = "Tubete salvo."
    return RedirectResponse("/cadastros/tubetes", status_code=303)


@router.post("/tubetes/{item_id}/excluir")
def tubetes_excluir(request: Request, item_id: int):
    user, err = _auth(request, editar=True)
    if err:
        return err
    with connect() as conn:
        excluir_tubete(conn, item_id)
    request.session["cad_flash_ok"] = "Tubete excluído."
    return RedirectResponse("/cadastros/tubetes", status_code=303)


# ---- Caixas ----


@router.get("/caixas", response_class=HTMLResponse)
def caixas_lista(request: Request):
    user, err = _auth(request)
    if err:
        return err
    with connect() as conn:
        rows = [dict(r) for r in listar_caixas(conn)]
    ctx = _ctx_base(request, user)
    ctx.update(
        {
            "titulo": "Caixas",
            "slug": "caixas",
            "total": len(rows),
            "termo": "",
            "linhas": rows,
            "colunas": [
                ("codigo", "Código"),
                ("nome", "Nome"),
                ("custo", "Custo"),
            ],
        }
    )
    return render(request, "cadastros_crud_lista.html", ctx)


@router.get("/caixas/novo", response_class=HTMLResponse)
def caixas_novo(request: Request):
    user, err = _auth(request, editar=True)
    if err:
        return err
    ctx = _ctx_base(request, user)
    ctx.update({"titulo": "Nova caixa", "slug": "caixas", "item": None})
    return render(request, "cadastros_form_caixa.html", ctx)


@router.get("/caixas/{item_id}", response_class=HTMLResponse)
def caixas_editar(request: Request, item_id: int):
    user, err = _auth(request)
    if err:
        return err
    with connect() as conn:
        row = _obter_por_id(conn, "caixas", item_id)
    if not row:
        return HTMLResponse("Registro não encontrado.", status_code=404)
    ctx = _ctx_base(request, user)
    ctx.update({"titulo": "Editar caixa", "slug": "caixas", "item": dict(row)})
    return render(request, "cadastros_form_caixa.html", ctx)


@router.post("/caixas/salvar")
async def caixas_salvar(request: Request):
    user, err = _auth(request, editar=True)
    if err:
        return err
    form = await request.form()
    item_id = str(form.get("id") or "").strip()
    codigo = str(form.get("codigo") or "").strip()
    nome = str(form.get("nome") or "").strip()
    custo = parse_float(form.get("custo"))
    if not codigo or not nome or custo is None:
        request.session["cad_flash_err"] = "Informe código, nome e custo."
        return RedirectResponse(
            f"/cadastros/caixas/{item_id}" if item_id else "/cadastros/caixas/novo",
            status_code=303,
        )
    with connect() as conn:
        salvar_caixa(
            conn,
            codigo=codigo,
            nome=nome,
            custo=float(custo),
            caixa_id=int(item_id) if item_id else None,
        )
    request.session["cad_flash_ok"] = "Caixa salva."
    return RedirectResponse("/cadastros/caixas", status_code=303)


@router.post("/caixas/{item_id}/excluir")
def caixas_excluir(request: Request, item_id: int):
    user, err = _auth(request, editar=True)
    if err:
        return err
    with connect() as conn:
        excluir_caixa(conn, item_id)
    request.session["cad_flash_ok"] = "Caixa excluída."
    return RedirectResponse("/cadastros/caixas", status_code=303)


# ---- Facas ----


@router.get("/facas", response_class=HTMLResponse)
def facas_lista(request: Request):
    user, err = _auth(request)
    if err:
        return err
    with connect() as conn:
        rows = [dict(r) for r in listar_facas(conn)]
    ctx = _ctx_base(request, user)
    ctx.update(
        {
            "titulo": "Facas",
            "slug": "facas",
            "total": len(rows),
            "termo": "",
            "linhas": rows,
            "colunas": [
                ("codigo", "Código"),
                ("tipo_faca", "Tipo / dimensão"),
                ("nome_exibicao_orc", "Nome ORC"),
                ("area", "Área"),
            ],
        }
    )
    return render(request, "cadastros_crud_lista.html", ctx)


@router.get("/facas/novo", response_class=HTMLResponse)
def facas_novo(request: Request):
    user, err = _auth(request, editar=True)
    if err:
        return err
    ctx = _ctx_base(request, user)
    ctx.update({"titulo": "Nova faca", "slug": "facas", "item": None})
    return render(request, "cadastros_form_faca.html", ctx)


@router.get("/facas/{item_id}", response_class=HTMLResponse)
def facas_editar(request: Request, item_id: int):
    user, err = _auth(request)
    if err:
        return err
    with connect() as conn:
        row = _obter_por_id(conn, "facas", item_id)
    if not row:
        return HTMLResponse("Registro não encontrado.", status_code=404)
    ctx = _ctx_base(request, user)
    ctx.update({"titulo": "Editar faca", "slug": "facas", "item": dict(row)})
    return render(request, "cadastros_form_faca.html", ctx)


@router.post("/facas/salvar")
async def facas_salvar(request: Request):
    user, err = _auth(request, editar=True)
    if err:
        return err
    form = await request.form()
    item_id = str(form.get("id") or "").strip()
    codigo = str(form.get("codigo") or "").strip()
    tipo = str(form.get("tipo_faca") or "").strip()
    nome_orc = str(form.get("nome_exibicao_orc") or "").strip()
    largura = parse_float(form.get("largura"))
    altura = parse_float(form.get("altura"))
    gap_l = parse_float(form.get("gap_lateral"))
    gap_v = parse_float(form.get("gap_vertical"))
    if not codigo or not tipo or largura is None or altura is None or gap_l is None:
        request.session["cad_flash_err"] = "Informe código, tipo, largura, altura e gap lateral."
        return RedirectResponse(
            f"/cadastros/facas/{item_id}" if item_id else "/cadastros/facas/novo",
            status_code=303,
        )
    with connect() as conn:
        salvar_faca(
            conn,
            codigo=codigo,
            tipo_faca=tipo,
            nome_exibicao_orc=nome_orc or tipo,
            largura=float(largura),
            altura=float(altura),
            gap_lateral=float(gap_l),
            gap_vertical=float(gap_v) if gap_v is not None else 0.0,
            faca_id=int(item_id) if item_id else None,
        )
    request.session["cad_flash_ok"] = "Faca salva."
    return RedirectResponse("/cadastros/facas", status_code=303)


@router.post("/facas/{item_id}/excluir")
def facas_excluir(request: Request, item_id: int):
    user, err = _auth(request, editar=True)
    if err:
        return err
    with connect() as conn:
        excluir_faca(conn, item_id)
    request.session["cad_flash_ok"] = "Faca excluída."
    return RedirectResponse("/cadastros/facas", status_code=303)


# ---- Suprimentos ----


@router.get("/suprimentos", response_class=HTMLResponse)
def suprimentos_lista(request: Request):
    user, err = _auth(request)
    if err:
        return err
    with connect() as conn:
        rows = [dict(r) for r in listar_suprimentos(conn, ativos_only=False)]
    ctx = _ctx_base(request, user)
    ctx.update(
        {
            "titulo": "Suprimentos",
            "slug": "suprimentos",
            "total": len(rows),
            "termo": "",
            "linhas": rows,
            "colunas": [
                ("codigo", "Código"),
                ("nome_exibicao", "Exibição"),
                ("descricao", "Descrição"),
                ("custo", "Custo"),
                ("ativo", "Ativo"),
            ],
        }
    )
    return render(request, "cadastros_crud_lista.html", ctx)


@router.get("/suprimentos/novo", response_class=HTMLResponse)
def suprimentos_novo(request: Request):
    user, err = _auth(request, editar=True)
    if err:
        return err
    ctx = _ctx_base(request, user)
    ctx.update({"titulo": "Novo suprimento", "slug": "suprimentos", "item": None})
    return render(request, "cadastros_form_suprimento.html", ctx)


@router.get("/suprimentos/{item_id}", response_class=HTMLResponse)
def suprimentos_editar(request: Request, item_id: int):
    user, err = _auth(request)
    if err:
        return err
    with connect() as conn:
        row = obter_suprimento(conn, item_id)
    if not row:
        return HTMLResponse("Registro não encontrado.", status_code=404)
    ctx = _ctx_base(request, user)
    ctx.update(
        {"titulo": "Editar suprimento", "slug": "suprimentos", "item": dict(row)}
    )
    return render(request, "cadastros_form_suprimento.html", ctx)


@router.post("/suprimentos/salvar")
async def suprimentos_salvar(request: Request):
    user, err = _auth(request, editar=True)
    if err:
        return err
    form = await request.form()
    item_id = str(form.get("id") or "").strip()
    codigo = str(form.get("codigo") or "").strip()
    marca = str(form.get("marca") or "").strip() or None
    descricao = str(form.get("descricao") or "").strip()
    nome_exib = str(form.get("nome_exibicao") or "").strip()
    custo = parse_float(form.get("custo"))
    preco = parse_float(form.get("preco_compra"))
    ativo = str(form.get("ativo") or "") == "1"
    if not codigo or not descricao or custo is None:
        request.session["cad_flash_err"] = "Informe código, descrição e custo."
        return RedirectResponse(
            f"/cadastros/suprimentos/{item_id}"
            if item_id
            else "/cadastros/suprimentos/novo",
            status_code=303,
        )
    with connect() as conn:
        salvar_suprimento(
            conn,
            codigo=codigo,
            marca=marca,
            descricao=descricao,
            nome_exibicao=nome_exib or descricao,
            preco_compra=preco,
            custo=float(custo),
            ativo=ativo,
            suprimento_id=int(item_id) if item_id else None,
        )
    request.session["cad_flash_ok"] = "Suprimento salvo."
    return RedirectResponse("/cadastros/suprimentos", status_code=303)


@router.post("/suprimentos/{item_id}/excluir")
def suprimentos_excluir(request: Request, item_id: int):
    user, err = _auth(request, editar=True)
    if err:
        return err
    with connect() as conn:
        excluir_suprimento(conn, item_id)
    request.session["cad_flash_ok"] = "Suprimento excluído."
    return RedirectResponse("/cadastros/suprimentos", status_code=303)
