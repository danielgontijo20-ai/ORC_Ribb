"""
ORC_Ribb Web — FastAPI + autenticação + permissões.

Rodar local:
    python -m uvicorn web.main:app --reload --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from src.db.database import DB_PATH, ROOT_DIR, connect, db_fs_status, ensure_db_dir
from src.db.migrate import migrate
from src.services.usuarios import autenticar
from web.config import APP_NAME, SECRET_KEY, SESSION_MAX_AGE
from web.deps import get_current_user
from web.logos import ensure_logo_dir
from web.routes import cadastros, historico_vendas, menu, orcamentos, usuarios
from web.templating import render

BASE_DIR = Path(__file__).resolve().parent

_DB_FIX_HINT = (
    "Erro no banco de dados (não abre o SQLite). Na VPS execute: "
    "cd /var/www/ORC_Ribb && "
    "mkdir -p data/database data/logos && "
    "id=$(systemctl show -p User --value orc-ribb); "
    "id=${id:-www-data}; "
    "chown -R \"$id:$id\" data && "
    "chmod 755 data data/database data/logos && "
    "source .venv/bin/activate && python -m src.db.migrate && "
    "systemctl restart orc-ribb && curl -s http://127.0.0.1:8000/health"
)

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
    try:
        ensure_db_dir()
        migrate()
    except Exception:
        logging.exception(
            "Startup: falha ao preparar/abrir o banco em %s. Status FS: %s",
            DB_PATH,
            db_fs_status(),
        )


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
    try:
        with connect() as conn:
            user = autenticar(conn, email, senha)
    except sqlite3.OperationalError as exc:
        # Banco sem tabelas / pasta / permissão — tenta recuperar com migrate.
        logging.exception(
            "Login: erro de schema/banco (%s). FS=%s. Rodando migrate…",
            exc,
            db_fs_status(),
        )
        try:
            ensure_db_dir()
            migrate()
            with connect() as conn:
                user = autenticar(conn, email, senha)
        except Exception:
            logging.exception("Login: falha após migrate. FS=%s", db_fs_status())
            return render(
                request,
                "login.html",
                {"erro": f"{_DB_FIX_HINT} Detalhe: {exc}"},
                status_code=500,
            )
    except Exception:
        logging.exception("Login: falha inesperada na autenticação")
        return render(
            request,
            "login.html",
            {
                "erro": (
                    "Erro interno ao autenticar. Verifique os logs: "
                    "journalctl -u orc-ribb -n 80 --no-pager"
                )
            },
            status_code=500,
        )

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


@app.get("/health")
def health():
    """Checagem rápida para diagnóstico (sem autenticação)."""
    fs = db_fs_status()
    try:
        with connect() as conn:
            conn.execute("SELECT 1").fetchone()
            tabelas = {
                r[0]
                for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            tem_auth = "usuarios" in tabelas and "papeis" in tabelas
            n_users = 0
            if tem_auth:
                n_users = conn.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0]
        return {
            "ok": True,
            "db": str(DB_PATH),
            "auth_tables": tem_auth,
            "usuarios": n_users,
            "fs": fs,
        }
    except sqlite3.Error as exc:
        return {"ok": False, "error": str(exc), "db": str(DB_PATH), "fs": fs}
    except OSError as exc:
        return {"ok": False, "error": str(exc), "db": str(DB_PATH), "fs": fs}


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)
