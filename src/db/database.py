"""
Conexão e criação do banco SQLite.

Didático:
- SQLite guarda tudo em UM arquivo (data/database/orc_ribb.db).
- Em modo WAL também usa .db-wal e .db-shm — se esses arquivos ficarem
  com dono/permissão errados (ex.: deploy como root), o app quebra com
  "unable to open database file" mesmo com o .db "ok".
"""

from __future__ import annotations

import logging
import os
import sqlite3
from pathlib import Path

log = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).resolve().parents[2]
DB_DIR = ROOT_DIR / "data" / "database"
DB_PATH = DB_DIR / "orc_ribb.db"
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def _sidecar_paths(db_path: Path) -> tuple[Path, Path]:
    return (
        db_path.with_name(db_path.name + "-wal"),
        db_path.with_name(db_path.name + "-shm"),
    )


def _file_access(path: Path) -> dict:
    exists = path.exists()
    return {
        "exists": exists,
        "readable": exists and os.access(path, os.R_OK),
        "writable": exists and os.access(path, os.W_OK),
        "size_bytes": path.stat().st_size if exists and path.is_file() else None,
    }


def ensure_db_dir(db_path: Path | str = DB_PATH) -> Path:
    """Garante que a pasta do banco exista e seja gravável."""
    path = Path(db_path)
    parent = path.parent
    try:
        parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise sqlite3.OperationalError(
            f"Não foi possível criar a pasta do banco ({parent}): {exc}"
        ) from exc
    if not os.access(parent, os.W_OK | os.X_OK):
        raise sqlite3.OperationalError(
            f"Pasta do banco sem permissão de escrita: {parent}"
        )
    if path.exists() and not os.access(path, os.R_OK | os.W_OK):
        raise sqlite3.OperationalError(
            f"Arquivo do banco sem permissão de leitura/escrita: {path}"
        )
    return path


def prepare_db_files(db_path: Path | str = DB_PATH) -> Path:
    """
    Prepara pasta/arquivos do SQLite e tenta corrigir permissões dos sidecars WAL.
    Não apaga dados — só chmod quando o processo tiver permissão.
    """
    path = ensure_db_dir(db_path)
    candidates = [path, *_sidecar_paths(path)]
    for p in candidates:
        if not p.exists():
            continue
        try:
            os.chmod(p, 0o664)
        except OSError as exc:
            log.warning("DB: não ajustou permissão de %s (%s)", p, exc)
    try:
        os.chmod(path.parent, 0o755)
    except OSError:
        pass
    return path


def db_fs_status(db_path: Path | str = DB_PATH) -> dict:
    """Diagnóstico de filesystem para /health e logs."""
    path = Path(db_path)
    parent = path.parent
    wal, shm = _sidecar_paths(path)
    return {
        "db": str(path),
        "parent": str(parent),
        "parent_exists": parent.exists(),
        "parent_writable": parent.exists() and os.access(parent, os.W_OK | os.X_OK),
        "db_exists": path.exists(),
        "db_is_file": path.is_file() if path.exists() else False,
        "db_readable": path.exists() and os.access(path, os.R_OK),
        "db_writable": path.exists() and os.access(path, os.W_OK),
        "db_size_bytes": path.stat().st_size if path.is_file() else None,
        "wal": _file_access(wal),
        "shm": _file_access(shm),
        # compat com health antigo
        "wal_exists": wal.exists(),
        "shm_exists": shm.exists(),
    }


def _open_connection(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path), check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout=30000")
    # WAL precisa gravar -wal/-shm; se falhar, cai para DELETE (app continua).
    try:
        mode = conn.execute("PRAGMA journal_mode=WAL").fetchone()
        if mode and str(mode[0]).lower() != "wal":
            log.warning("DB: journal_mode=%s (esperado wal)", mode[0])
    except sqlite3.Error as exc:
        log.warning("DB: WAL indisponível (%s); usando journal DELETE", exc)
        try:
            conn.execute("PRAGMA journal_mode=DELETE")
        except sqlite3.Error:
            pass
    return conn


def connect(db_path: Path | str = DB_PATH) -> sqlite3.Connection:
    """Abre conexão com o SQLite, com retry leve após corrigir permissões."""
    path = prepare_db_files(db_path)
    try:
        return _open_connection(path)
    except sqlite3.OperationalError as exc:
        msg = str(exc).lower()
        if "unable to open" not in msg and "readonly" not in msg and "locked" not in msg:
            raise
        log.warning(
            "DB: falha ao abrir (%s). FS=%s — tentando recuperar…",
            exc,
            db_fs_status(path),
        )
        prepare_db_files(path)
        # Segunda tentativa: às vezes -shm stale impede abertura
        wal, shm = _sidecar_paths(path)
        for side in (shm,):
            if side.exists() and not os.access(side, os.W_OK):
                try:
                    # Só remove shm se não for gravável e pudermos recriar na pasta
                    if os.access(path.parent, os.W_OK):
                        side.unlink(missing_ok=True)
                        log.warning("DB: removeu sidecar sem escrita: %s", side.name)
                except OSError as rm_exc:
                    log.warning("DB: não removeu %s (%s)", side, rm_exc)
        try:
            return _open_connection(path)
        except sqlite3.OperationalError:
            log.exception("DB: segunda abertura falhou. FS=%s", db_fs_status(path))
            raise


def init_db(db_path: Path | str = DB_PATH) -> Path:
    """Cria (ou recria a estrutura de) tabelas usando schema.sql."""
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    with connect(db_path) as conn:
        conn.executescript(schema_sql)
        conn.commit()
    return Path(db_path)
