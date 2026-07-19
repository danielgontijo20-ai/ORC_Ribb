"""Helper de templates compatível com Starlette moderno."""

from __future__ import annotations

from pathlib import Path

from fastapi import Request
from fastapi.templating import Jinja2Templates

from src.services.usuarios import usuario_tem_permissao
from web.config import APP_NAME

TEMPLATES = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))
TEMPLATES.env.globals["has_perm"] = usuario_tem_permissao
TEMPLATES.env.globals["app_name"] = APP_NAME


def render(request: Request, name: str, context: dict | None = None, status_code: int = 200):
    return TEMPLATES.TemplateResponse(
        request, name, context or {}, status_code=status_code
    )
