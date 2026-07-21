from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from src.services.usuarios import usuario_tem_permissao
from web.deps import get_current_user
from web.templating import render

router = APIRouter()


@router.get("/menu", response_class=HTMLResponse)
def menu(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    if not usuario_tem_permissao(user, "menu.ver"):
        return HTMLResponse("Sem permissão.", status_code=403)
    return render(request, "menu.html", {"user": user})
