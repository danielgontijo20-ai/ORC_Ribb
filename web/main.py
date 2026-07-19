"""
ORC_Ribb Web — FastAPI + autenticação + permissões.

Rodar local:
    python -m uvicorn web.main:app --reload --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from src.db.database import ROOT_DIR, connect
from src.db.migrate import migrate
from src.services.usuarios import autenticar
from web.config import APP_NAME, SECRET_KEY, SESSION_MAX_AGE
from web.deps import get_current_user
from web.logos import ensure_logo_dir
from web.routes import cadastros, historico_vendas, menu, orcamentos, usuarios
from web.templating import render

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title=APP_NAME)
app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    max_age=SESSION_MAX_AGE,
    same_site="lax",
    https_only=False,
)

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
ensure_logo_dir()
app.mount(
    "/media/logos",
    StaticFiles(directory=str(ROOT_DIR / "data" / "logos")),
    name="logos",
)

app.include_router(menu.router)
app.include_router(orcamentos.router)
app.include_router(cadastros.router)
app.include_router(historico_vendas.router)
app.include_router(usuarios.router)


@app.on_event("startup")
def _startup() -> None:
    migrate()


@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    if get_current_user(request):
        return RedirectResponse("/menu", status_code=303)
    return RedirectResponse("/login", status_code=303)


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    if get_current_user(request):
        return RedirectResponse("/menu", status_code=303)
    return render(request, "login.html", {"erro": None})


@app.post("/login", response_class=HTMLResponse)
def login_submit(
    request: Request,
    email: str = Form(...),
    senha: str = Form(...),
):
    with connect() as conn:
        user = autenticar(conn, email, senha)
    if not user:
        return render(
            request,
            "login.html",
            {"erro": "E-mail ou senha inválidos."},
            status_code=401,
        )
    request.session.clear()
    request.session["user_id"] = user["id"]
    request.session["user_nome"] = user["nome"]
    return RedirectResponse("/menu", status_code=303)


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)
