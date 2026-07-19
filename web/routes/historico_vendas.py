from __future__ import annotations

from fastapi import APIRouter, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from src.db.database import connect
from src.services.clientes import buscar_clientes, contar_clientes, obter_cliente
from src.services.historico_nf import listar_vendas_por_cliente
from src.services.usuarios import usuario_tem_permissao
from src.ui.formatters import brl
from web.deps import get_current_user
from web.templating import render

router = APIRouter(prefix="/historico-vendas")

SESS_CLI = "hist_cliente"
SESS_DIALOG = "hist_dialog"
SESS_BUSCOU = "hist_buscou"


def _require(request: Request):
    user = get_current_user(request)
    if not user:
        return None, RedirectResponse("/login", status_code=303)
    if not usuario_tem_permissao(user, "historico_vendas.ver"):
        return None, HTMLResponse("Sem permissão.", status_code=403)
    return user, None


def _get_cli(request: Request) -> dict | None:
    cli = request.session.get(SESS_CLI)
    return cli if isinstance(cli, dict) else None


@router.get("", response_class=HTMLResponse)
def historico(request: Request, termo_cli: str = Query("")):
    user, err = _require(request)
    if err:
        return err

    dialog = request.session.get(SESS_DIALOG)
    cli = _get_cli(request)
    clientes = []
    total_clientes = 0
    if dialog == "cliente":
        with connect() as conn:
            clientes = [
                dict(r) for r in buscar_clientes(conn, termo=termo_cli or None)
            ]
            total_clientes = contar_clientes(conn, termo=termo_cli or None)

    notas = None
    label = None
    buscou = bool(request.session.get(SESS_BUSCOU))
    if buscou:
        cliente_id = int(cli["id"]) if cli and cli.get("id") else None
        with connect() as conn:
            notas = listar_vendas_por_cliente(
                conn,
                cliente_id=cliente_id,
                termo_cliente=None,
                limite_notas=500,
            )
        if cliente_id and cli:
            label = f"{cli.get('nome')} | {cli.get('cnpj_cpf') or '-'}"
        else:
            label = "todas as vendas (mais recente → antiga)"

    return render(
        request,
        "historico_vendas.html",
        {
            "user": user,
            "cli": cli,
            "dialog": dialog,
            "termo_cli": termo_cli,
            "clientes": clientes,
            "total_clientes": total_clientes,
            "notas": notas,
            "label": label,
            "brl": brl,
            "buscou": buscou,
        },
    )


@router.post("/dialog")
def dialog(request: Request, dialog: str = Form(...)):
    user, err = _require(request)
    if err:
        return err
    if dialog == "cliente":
        request.session[SESS_DIALOG] = "cliente"
    else:
        request.session.pop(SESS_DIALOG, None)
    return RedirectResponse("/historico-vendas", status_code=303)


@router.post("/cliente/selecionar")
def selecionar_cliente(request: Request, cliente_id: int = Form(...)):
    user, err = _require(request)
    if err:
        return err
    with connect() as conn:
        row = obter_cliente(conn, cliente_id)
    if not row:
        return RedirectResponse("/historico-vendas", status_code=303)
    request.session[SESS_CLI] = {
        "id": row["id"],
        "nome": row["nome"],
        "cnpj_cpf": row["cnpj_cpf"],
        "uf": row["uf"],
    }
    request.session.pop(SESS_DIALOG, None)
    request.session.pop(SESS_BUSCOU, None)
    return RedirectResponse("/historico-vendas", status_code=303)


@router.post("/cliente/limpar")
def limpar_cliente(request: Request):
    user, err = _require(request)
    if err:
        return err
    request.session.pop(SESS_CLI, None)
    request.session.pop(SESS_BUSCOU, None)
    return RedirectResponse("/historico-vendas", status_code=303)


@router.post("/buscar")
def buscar(request: Request):
    user, err = _require(request)
    if err:
        return err
    request.session[SESS_BUSCOU] = True
    return RedirectResponse("/historico-vendas", status_code=303)


@router.get("/nota/{numero_nota}", response_class=HTMLResponse)
def detalhe_nota(
    request: Request,
    numero_nota: str,
    cliente_id: int | None = Query(None),
):
    user, err = _require(request)
    if err:
        return err

    with connect() as conn:
        row = conn.execute(
            """
            SELECT numero_nota, cliente_id, nome_cliente, cnpj_cpf,
                   MAX(data_emissao) AS data_emissao,
                   SUM(COALESCE(valor_total, 0)) AS valor_nota
            FROM faturamento
            WHERE numero_nota = ?
              AND (? IS NULL OR cliente_id = ?)
            GROUP BY numero_nota, cliente_id, nome_cliente, cnpj_cpf
            LIMIT 1
            """,
            (numero_nota, cliente_id, cliente_id),
        ).fetchone()
        if not row:
            return HTMLResponse("Nota não encontrada.", status_code=404)
        nota = dict(row)
        itens = conn.execute(
            """
            SELECT codigo_item, descricao_item, unidade, quantidade,
                   valor_unitario, valor_total, data_emissao
            FROM faturamento
            WHERE numero_nota = ?
              AND COALESCE(cliente_id, -1) = COALESCE(?, -1)
            ORDER BY id
            """,
            (numero_nota, nota.get("cliente_id")),
        ).fetchall()
        nota["itens"] = [dict(i) for i in itens]

    return render(
        request,
        "historico_venda_detalhe.html",
        {
            "user": user,
            "nota": nota,
            "brl": brl,
        },
    )
