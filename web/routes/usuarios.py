from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from src.db.database import connect
from src.services.usuarios import (
    atualizar_usuario,
    criar_usuario,
    listar_papeis,
    listar_usuarios,
    obter_usuario,
    usuario_tem_permissao,
)
from web.deps import get_current_user
from web.templating import render

router = APIRouter(prefix="/usuarios")


def _require_admin(request: Request):
    user = get_current_user(request)
    if not user:
        return None, RedirectResponse("/login", status_code=303)
    if not usuario_tem_permissao(user, "usuarios.gerenciar"):
        return None, HTMLResponse("Sem permissão.", status_code=403)
    return user, None


@router.get("", response_class=HTMLResponse)
def lista(request: Request):
    user, err = _require_admin(request)
    if err:
        return err
    with connect() as conn:
        usuarios = listar_usuarios(conn)
    return render(
        request,
        "usuarios_lista.html",
        {
            "user": user,
            "usuarios": usuarios,
            "flash_ok": request.session.pop("usr_flash_ok", None),
            "flash_err": request.session.pop("usr_flash_err", None),
        },
    )


@router.get("/novo", response_class=HTMLResponse)
def novo(request: Request):
    user, err = _require_admin(request)
    if err:
        return err
    with connect() as conn:
        papeis = listar_papeis(conn)
    return render(
        request,
        "usuarios_form.html",
        {
            "user": user,
            "alvo": None,
            "papeis": papeis,
            "titulo": "Novo usuário",
            "flash_err": request.session.pop("usr_flash_err", None),
        },
    )


@router.get("/{usuario_id}", response_class=HTMLResponse)
def editar(request: Request, usuario_id: int):
    user, err = _require_admin(request)
    if err:
        return err
    with connect() as conn:
        alvo = obter_usuario(conn, usuario_id)
        papeis = listar_papeis(conn)
    if not alvo:
        return HTMLResponse("Usuário não encontrado.", status_code=404)
    return render(
        request,
        "usuarios_form.html",
        {
            "user": user,
            "alvo": alvo,
            "papeis": papeis,
            "titulo": f"Editar — {alvo['nome']}",
            "flash_err": request.session.pop("usr_flash_err", None),
        },
    )


@router.post("/salvar")
async def salvar(request: Request):
    user, err = _require_admin(request)
    if err:
        return err
    form = await request.form()
    usuario_id_raw = str(form.get("usuario_id") or "").strip()
    nome = str(form.get("nome") or "").strip()
    email = str(form.get("email") or "").strip()
    senha = str(form.get("senha") or "")
    papel_id = int(form.get("papel_id") or 0)
    ativo = str(form.get("ativo") or "") == "1"

    if not nome or not email or not papel_id:
        request.session["usr_flash_err"] = "Preencha nome, e-mail e papel."
        if usuario_id_raw:
            return RedirectResponse(f"/usuarios/{usuario_id_raw}", status_code=303)
        return RedirectResponse("/usuarios/novo", status_code=303)

    try:
        with connect() as conn:
            if usuario_id_raw:
                atualizar_usuario(
                    conn,
                    int(usuario_id_raw),
                    nome=nome,
                    email=email,
                    papel_id=papel_id,
                    ativo=ativo,
                    senha=senha or None,
                )
                request.session["usr_flash_ok"] = f"Usuário {nome} atualizado."
            else:
                if not senha.strip():
                    request.session["usr_flash_err"] = "Informe a senha do novo usuário."
                    return RedirectResponse("/usuarios/novo", status_code=303)
                criar_usuario(
                    conn,
                    nome=nome,
                    email=email,
                    senha=senha,
                    papel_id=papel_id,
                    ativo=ativo,
                )
                request.session["usr_flash_ok"] = f"Usuário {nome} criado."
    except ValueError as e:
        request.session["usr_flash_err"] = str(e)
        if usuario_id_raw:
            return RedirectResponse(f"/usuarios/{usuario_id_raw}", status_code=303)
        return RedirectResponse("/usuarios/novo", status_code=303)

    return RedirectResponse("/usuarios", status_code=303)
