"""
Conexão e criação do banco SQLite.

Didático:
- SQLite guarda tudo em UM arquivo (data/database/orc_ribb.db).
- WAL + busy_timeout reduz erro "database is locked" no Streamlit.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
DB_DIR = ROOT_DIR / "data" / "database"
DB_PATH = DB_DIR / "orc_ribb.db"
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


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


def db_fs_status(db_path: Path | str = DB_PATH) -> dict:
    """Diagnóstico de filesystem para /health e logs."""
    path = Path(db_path)
    parent = path.parent
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
        "wal_exists": path.with_name(path.name + "-wal").exists(),
        "shm_exists": path.with_name(path.name + "-shm").exists(),
    }


def connect(db_path: Path | str = DB_PATH) -> sqlite3.Connection:
    """Abre conexão com o SQLite (thread-safe para popups do Streamlit)."""
    path = ensure_db_dir(db_path)

    conn = sqlite3.connect(path, check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


def init_db(db_path: Path | str = DB_PATH) -> Path:
    """Cria (ou recria a estrutura de) tabelas usando schema.sql."""
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    with connect(db_path) as conn:
        conn.executescript(schema_sql)
        conn.commit()
    return Path(db_path)
