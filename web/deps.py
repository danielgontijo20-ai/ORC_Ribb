"""Dependências FastAPI (sessão, usuário, permissões)."""

from __future__ import annotations

from typing import Callable

from fastapi import Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse

from src.db.database import connect
from src.services.usuarios import obter_usuario, usuario_tem_permissao


def get_db():
    with connect() as conn:
        yield conn


def get_current_user(request: Request) -> dict | None:
    uid = request.session.get("user_id")
    if not uid:
        return None
    with connect() as conn:
        return obter_usuario(conn, int(uid))


def require_login(request: Request) -> dict:
    user = get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/login"},
        )
    return user


def require_perm(codigo: str) -> Callable:
    def _inner(request: Request) -> dict:
        user = get_current_user(request)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_303_SEE_OTHER,
                headers={"Location": "/login"},
            )
        if not usuario_tem_permissao(user, codigo):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Sem permissão para esta ação.",
            )
        return user

    return _inner


def login_redirect_if_needed(request: Request):
    if not get_current_user(request):
        return RedirectResponse("/login", status_code=303)
    return None
