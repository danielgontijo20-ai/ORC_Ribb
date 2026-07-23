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
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from src.db.database import (
    DB_PATH,
    ROOT_DIR,
    connect,
    db_fs_status,
    ensure_db_dir,
    prepare_db_files,
)
from src.db.migrate import migrate
from src.services.usuarios import autenticar
from web.config import APP_NAME, SECRET_KEY, SESSION_MAX_AGE
from web.deps import get_current_user
from web.logos import ensure_logo_dir
from web.routes import cadastros, historico_vendas, menu, orcamentos, usuarios
from web.templating import render

BASE_DIR = Path(__file__).resolve().parent
log = logging.getLogger(__name__)

_DB_FIX_HINT = (
    "Banco temporariamente indisponível. Na VPS execute (cole tudo): "
    "cd /var/www/ORC_Ribb && systemctl stop orc-ribb; "
    "killall -9 uvicorn 2>/dev/null; sleep 1; "
    "SVC=$(systemctl show -p User --value orc-ribb); SVC=${SVC:-root}; "
    "chown -R \"$SVC:$SVC\" data; chmod 755 data data/database; "
    "chmod 664 data/database/orc_ribb.db 2>/dev/null; "
    "rm -f data/database/orc_ribb.db-shm; "
    "source .venv/bin/activate && python -m src.db.fix_db_permissions && "
    "systemctl start orc-ribb && curl -sS https://orc.gontijoensina.com/health"
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


@app.exception_handler(sqlite3.Error)
async def _sqlite_error_handler(request: Request, exc: sqlite3.Error):
    """Evita Internal Server Error genérico quando o SQLite falha."""
    log.exception("SQLite error em %s: %s | FS=%s", request.url.path, exc, db_fs_status())
    wants_json = "application/json" in (request.headers.get("accept") or "")
    if wants_json or request.url.path.startswith("/health"):
        return JSONResponse(
            {
                "ok": False,
                "error": str(exc),
                "db": str(DB_PATH),
                "fs": db_fs_status(),
                "hint": _DB_FIX_HINT,
            },
            status_code=503,
        )
    # Login: mostra o formulário com aviso (não página branca 500)
    if request.url.path.startswith("/login"):
        return render(
            request,
            "login.html",
            {"erro": f"{_DB_FIX_HINT} Detalhe: {exc}"},
            status_code=503,
        )
    return HTMLResponse(
        "<!DOCTYPE html><html><head><meta charset='utf-8'/>"
        "<title>Indisponível</title></head><body style='font-family:sans-serif;"
        "max-width:720px;margin:3rem auto;padding:0 1rem'>"
        "<h1>Sistema temporariamente indisponível</h1>"
        f"<p>{_DB_FIX_HINT}</p>"
        f"<p><small>Detalhe técnico: {exc}</small></p>"
        "<p><a href='/login'>Voltar ao login</a></p>"
        "</body></html>",
        status_code=503,
    )


@app.exception_handler(PermissionError)
async def _permission_error_handler(request: Request, exc: PermissionError):
    log.warning("PermissionError em %s: %s", request.url.path, exc)
    return RedirectResponse("/orcamentos/novo", status_code=303)


@app.on_event("startup")
def _startup() -> None:
    try:
        ensure_logo_dir()
        (ROOT_DIR / "data" / "database" / "backups").mkdir(parents=True, exist_ok=True)
        prepare_db_files()
        from src.db.database import consolidate_to_delete_journal, recover_wal_sidecars

        recover_wal_sidecars()
        migrate()
        consolidate_to_delete_journal()
        # Smoke test — se falhar, loga com diagnóstico completo
        with connect() as conn:
            conn.execute("SELECT 1").fetchone()
        log.info("Startup OK. DB=%s FS=%s", DB_PATH, db_fs_status())
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
    user = None
    try:
        prepare_db_files()
        with connect() as conn:
            user = autenticar(conn, email, senha)
    except sqlite3.OperationalError as exc:
        # NÃO roda migrate sob tráfego — só tenta reabrir após corrigir arquivos.
        log.exception(
            "Login: erro de banco (%s). FS=%s",
            exc,
            db_fs_status(),
        )
        try:
            prepare_db_files()
            with connect() as conn:
                user = autenticar(conn, email, senha)
        except Exception as exc2:
            log.exception("Login: falha após retry. FS=%s", db_fs_status())
            return render(
                request,
                "login.html",
                {"erro": f"{_DB_FIX_HINT} Detalhe: {exc2}"},
                status_code=503,
            )
    except Exception:
        log.exception("Login: falha inesperada na autenticação")
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
    """Checagem rápida para diagnóstico (sem autenticação). Nunca lança 500."""
    try:
        fs = db_fs_status()
    except Exception as exc:
        return JSONResponse(
            {"ok": False, "error": f"fs_status: {exc}", "db": str(DB_PATH)},
            status_code=503,
        )
    try:
        prepare_db_files()
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
    except (sqlite3.Error, OSError) as exc:
        return JSONResponse(
            {
                "ok": False,
                "error": str(exc),
                "db": str(DB_PATH),
                "fs": fs,
                "hint": _DB_FIX_HINT,
            },
            status_code=503,
        )


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)
