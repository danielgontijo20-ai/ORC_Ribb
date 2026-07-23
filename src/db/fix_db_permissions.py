"""
Recupera o SQLite quando aparece "unable to open database file".

Faz:
1. Ajusta permissões
2. Para de depender de WAL (checkpoint + journal DELETE)
3. Remove -shm stale (recriável)
4. Testa abertura

Uso na VPS (serviço parado):
    cd /var/www/ORC_Ribb
    systemctl stop orc-ribb
    source .venv/bin/activate
    python -m src.db.fix_db_permissions
    systemctl start orc-ribb
    curl -sS https://orc.gontijoensina.com/health
"""

from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path

from .database import (
    DB_PATH,
    consolidate_to_delete_journal,
    connect,
    db_fs_status,
    prepare_db_files,
    recover_wal_sidecars,
)


def fix_permissions(db_path: Path = DB_PATH) -> dict:
    path = Path(db_path)
    parent = path.parent
    parent.mkdir(parents=True, exist_ok=True)

    changed: list[str] = []
    for p in (
        parent,
        path,
        path.with_name(path.name + "-wal"),
        path.with_name(path.name + "-shm"),
    ):
        if not p.exists():
            continue
        mode = 0o755 if p.is_dir() else 0o664
        try:
            os.chmod(p, mode)
            changed.append(f"{p} -> {oct(mode)}")
        except OSError as exc:
            changed.append(f"{p} ERRO chmod: {exc}")

    prepare_db_files(path)
    changed.extend(recover_wal_sidecars(path))

    # Tenta consolidar WAL no arquivo principal e sair do modo WAL
    consolidated = consolidate_to_delete_journal(path)
    changed.append(f"consolidate_to_delete={consolidated}")

    # Se ainda existir -wal/-shm após DELETE, tenta limpar shm de novo
    changed.extend(recover_wal_sidecars(path))

    ok = False
    err = None
    integrity = None
    try:
        with connect(path) as conn:
            conn.execute("SELECT 1").fetchone()
            try:
                integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
            except sqlite3.Error as iex:
                integrity = f"erro: {iex}"
        ok = True
    except sqlite3.Error as exc:
        err = str(exc)

    return {
        "ok": ok,
        "error": err,
        "integrity": integrity,
        "changed": changed,
        "fs": db_fs_status(path),
        "uid": os.geteuid(),
        "user": os.environ.get("USER") or "",
    }


def main() -> int:
    print(f"DB: {DB_PATH}")
    print(f"UID: {os.geteuid()} USER={os.environ.get('USER')}")
    result = fix_permissions()
    for line in result["changed"]:
        print(" ", line)
    print("FS:", result["fs"])
    print("integrity:", result["integrity"])
    if result["ok"]:
        print("OK: banco abre normalmente (journal DELETE).")
        return 0
    print("FALHA:", result["error"])
    print(
        "\nSe ainda falhar, com o serviço parado execute:\n"
        "  fuser -v data/database/orc_ribb.db || true\n"
        "  killall -9 uvicorn || true\n"
        "  rm -f data/database/orc_ribb.db-shm\n"
        "  sqlite3 data/database/orc_ribb.db 'PRAGMA wal_checkpoint(TRUNCATE); PRAGMA journal_mode=DELETE;'\n"
        "  python -m src.db.fix_db_permissions\n"
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
