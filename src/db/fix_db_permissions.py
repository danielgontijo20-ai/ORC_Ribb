"""
Corrige permissões do SQLite (.db, -wal, -shm) e testa abertura.

Uso na VPS (como root ou dono do serviço):
    cd /var/www/ORC_Ribb
    source .venv/bin/activate
    python -m src.db.fix_db_permissions
"""

from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path

from .database import DB_PATH, connect, db_fs_status, prepare_db_files


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
    ok = False
    err = None
    try:
        with connect(path) as conn:
            conn.execute("SELECT 1").fetchone()
        ok = True
    except sqlite3.Error as exc:
        err = str(exc)

    return {
        "ok": ok,
        "error": err,
        "changed": changed,
        "fs": db_fs_status(path),
        "uid": os.geteuid(),
        "user": os.environ.get("USER") or "",
    }


def main() -> int:
    print(f"DB: {DB_PATH}")
    result = fix_permissions()
    for line in result["changed"]:
        print(" ", line)
    print("FS:", result["fs"])
    if result["ok"]:
        print("OK: banco abre normalmente.")
        return 0
    print("FALHA:", result["error"])
    print(
        "Dica: rode como o mesmo usuário do serviço, ou:\n"
        "  chown -R $(systemctl show -p User --value orc-ribb): "
        "data/database"
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
