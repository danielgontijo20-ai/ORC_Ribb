"""
Conexão e criação do banco SQLite.

Importante (VPS):
- Modo WAL cria orc_ribb.db-wal e .db-shm. Se ficarem travados/stale,
  o SQLite responde "unable to open database file" mesmo com permissões OK.
- Este módulo usa journal DELETE por padrão (um arquivo só) e, na falha,
  tenta recuperar sidecars WAL sem apagar o .db.
"""

from __future__ import annotations

import logging
import os
import sqlite3
import time
from pathlib import Path

log = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).resolve().parents[2]
DB_DIR = ROOT_DIR / "data" / "database"
DB_PATH = DB_DIR / "orc_ribb.db"
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"

# DELETE = sem -wal/-shm no dia a dia (bem mais estável na VPS Hostinger).
# Pode ser forçado via env: ORC_SQLITE_JOURNAL=WAL|DELETE
JOURNAL_MODE = (os.environ.get("ORC_SQLITE_JOURNAL") or "DELETE").strip().upper()
if JOURNAL_MODE not in ("DELETE", "WAL", "TRUNCATE", "PERSIST", "MEMORY", "OFF"):
    JOURNAL_MODE = "DELETE"


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
    """Ajusta permissões de .db / -wal / -shm quando possível."""
    path = ensure_db_dir(db_path)
    for p in (path, *_sidecar_paths(path)):
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


def recover_wal_sidecars(db_path: Path | str = DB_PATH) -> list[str]:
    """
    Recuperação segura quando o open falha com WAL stale.
    - Remove apenas o -shm (recriável).
    - NÃO apaga o -wal (contém commits pendentes).
    """
    path = Path(db_path)
    actions: list[str] = []
    wal, shm = _sidecar_paths(path)
    if shm.exists():
        try:
            shm.unlink()
            actions.append(f"removeu {shm.name}")
            log.warning("DB: removeu sidecar stale %s", shm.name)
        except OSError as exc:
            actions.append(f"falha ao remover {shm.name}: {exc}")
    return actions


def consolidate_to_delete_journal(db_path: Path | str = DB_PATH) -> bool:
    """
    Abre o banco, faz checkpoint do WAL e muda para journal DELETE.
    Assim -wal/-shm deixam de ser necessários no dia a dia.
    """
    path = prepare_db_files(db_path)
    try:
        conn = sqlite3.connect(str(path), timeout=60)
        try:
            conn.execute("PRAGMA busy_timeout=60000")
            try:
                conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            except sqlite3.Error as exc:
                log.warning("DB: checkpoint falhou (%s)", exc)
            mode = conn.execute("PRAGMA journal_mode=DELETE").fetchone()
            conn.commit()
            log.info("DB: journal_mode=%s", mode[0] if mode else "?")
            return True
        finally:
            conn.close()
    except sqlite3.Error as exc:
        log.warning("DB: consolidate falhou (%s)", exc)
        return False


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
        "journal_mode_pref": JOURNAL_MODE,
        "wal": _file_access(wal),
        "shm": _file_access(shm),
        "wal_exists": wal.exists(),
        "shm_exists": shm.exists(),
        "pid": os.getpid(),
        "uid": os.geteuid(),
    }


def _open_connection(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path), check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout=30000")
    try:
        mode = conn.execute(f"PRAGMA journal_mode={JOURNAL_MODE}").fetchone()
        log.debug("DB: journal_mode=%s", mode[0] if mode else "?")
    except sqlite3.Error as exc:
        log.warning("DB: journal_mode=%s falhou (%s); tentando DELETE", JOURNAL_MODE, exc)
        try:
            conn.execute("PRAGMA journal_mode=DELETE")
        except sqlite3.Error:
            pass
    return conn


def connect(db_path: Path | str = DB_PATH) -> sqlite3.Connection:
    """Abre conexão com retries e recuperação de sidecars WAL."""
    path = prepare_db_files(db_path)
    last_exc: Exception | None = None

    for attempt in range(1, 4):
        try:
            return _open_connection(path)
        except sqlite3.OperationalError as exc:
            last_exc = exc
            msg = str(exc).lower()
            log.warning(
                "DB: abertura falhou (tentativa %s): %s | FS=%s",
                attempt,
                exc,
                db_fs_status(path),
            )
            if "unable to open" not in msg and "readonly" not in msg and "locked" not in msg:
                raise
            prepare_db_files(path)
            if attempt == 1:
                recover_wal_sidecars(path)
            elif attempt == 2:
                # Tenta consolidar WAL → DELETE (requer open; se falhar, segue)
                consolidate_to_delete_journal(path)
            time.sleep(0.15 * attempt)

    assert last_exc is not None
    log.exception("DB: esgotaram tentativas de abertura. FS=%s", db_fs_status(path))
    raise last_exc


def init_db(db_path: Path | str = DB_PATH) -> Path:
    """Cria (ou recria a estrutura de) tabelas usando schema.sql."""
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    with connect(db_path) as conn:
        conn.executescript(schema_sql)
        conn.commit()
    return Path(db_path)
