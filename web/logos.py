"""Helpers de logos (caminhos no disco → URL web)."""

from __future__ import annotations

from pathlib import Path

from src.db.database import ROOT_DIR

LOGO_DIR = ROOT_DIR / "data" / "logos"


def ensure_logo_dir() -> Path:
    LOGO_DIR.mkdir(parents=True, exist_ok=True)
    return LOGO_DIR


def logo_url(path: str | None) -> str | None:
    if not path:
        return None
    p = Path(str(path))
    if p.is_file():
        return f"/media/logos/{p.name}"
    candidate = LOGO_DIR / p.name
    if candidate.is_file():
        return f"/media/logos/{candidate.name}"
    # tenta nomes padrão
    for name in (p.name, str(path)):
        for ext in ("png", "jpg", "jpeg", "webp"):
            c = LOGO_DIR / f"{Path(name).stem}.{ext}"
            if c.is_file():
                return f"/media/logos/{c.name}"
    return None


def save_upload(upload, stem: str) -> str | None:
    """Salva UploadFile e retorna caminho absoluto como string."""
    if upload is None:
        return None
    filename = (getattr(upload, "filename", None) or "").strip()
    if not filename:
        return None
    ensure_logo_dir()
    ext = Path(filename).suffix.lower().lstrip(".") or "png"
    if ext not in ("png", "jpg", "jpeg", "webp"):
        ext = "png"
    dest = LOGO_DIR / f"{stem}.{ext}"
    content = upload.file.read()
    if not content:
        return None
    dest.write_bytes(content)
    return str(dest)
