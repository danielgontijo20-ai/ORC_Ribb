"""
Conexão e criação do banco SQLite.

Didático:
- SQLite guarda tudo em UM arquivo (data/database/orc_ribb.db).
- WAL + busy_timeout reduz erro "database is locked" no Streamlit.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
DB_DIR = ROOT_DIR / "data" / "database"
DB_PATH = DB_DIR / "orc_ribb.db"
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def connect(db_path: Path | str = DB_PATH) -> sqlite3.Connection:
    """Abre conexão com o SQLite (thread-safe para popups do Streamlit)."""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

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
