from __future__ import annotations

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from src.db.database import connect
from src.services.historico_nf import listar_vendas_por_cliente
from src.services.usuarios import usuario_tem_permissao
from web.deps import get_current_user
from web.templating import render

router = APIRouter(prefix="/historico-vendas")


@router.get("", response_class=HTMLResponse)
def historico(request: Request, cliente_id: int | None = Query(None)):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    if not usuario_tem_permissao(user, "historico_vendas.ver"):
        return HTMLResponse("Sem permissão.", status_code=403)

    with connect() as conn:
        notas = listar_vendas_por_cliente(
            conn, cliente_id=cliente_id, limite_notas=100
        )

    return render(
        request,
        "historico_vendas.html",
        {
            "user": user,
            "notas": notas,
            "cliente_id": cliente_id,
        },
    )
