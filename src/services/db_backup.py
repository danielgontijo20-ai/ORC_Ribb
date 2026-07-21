"""
Backup rotativo do SQLite ao salvar orçamento.

Estratégia (pouco espaço, recuperação útil):
- Sempre atualiza `orc_ribb.db.bak-latest` (sobrescreve o anterior).
- Mantém também os últimos N backups com data/hora.
- Remove os mais antigos automaticamente.

Não faz backup a cada inserção de item (rascunho) — só no "Salvar orçamento".
"""

from __future__ import annotations

import logging
import os
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

from src.db.database import DB_PATH, ROOT_DIR

log = logging.getLogger(__name__)

# Pasta padrão no projeto (portável). Na VPS pode apontar via env ORC_BACKUP_DIR.
DEFAULT_BACKUP_DIR = ROOT_DIR / "data" / "database" / "backups"
KEEP_LAST = int(os.environ.get("ORC_BACKUP_KEEP", "10"))
LATEST_NAME = "orc_ribb.db.bak-latest"


def backup_dir() -> Path:
    raw = (os.environ.get("ORC_BACKUP_DIR") or "").strip()
    return Path(raw) if raw else DEFAULT_BACKUP_DIR


def _safe_checkpoint(db_path: Path) -> None:
    """Tenta consolidar WAL no arquivo principal antes de copiar."""
    try:
        with sqlite3.connect(str(db_path), timeout=30) as conn:
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    except sqlite3.Error as exc:
        log.warning("Backup: checkpoint WAL falhou (%s); copiando mesmo assim.", exc)


def backup_on_salvar_orcamento(
    db_path: Path | str = DB_PATH,
    *,
    keep_last: int = KEEP_LAST,
) -> Path | None:
    """
    Cria backup rotativo. Retorna o caminho do backup com timestamp, ou None.
    """
    src = Path(db_path)
    if not src.is_file():
        log.error("Backup: banco não encontrado em %s", src)
        return None

    dest_dir = backup_dir()
    dest_dir.mkdir(parents=True, exist_ok=True)

    _safe_checkpoint(src)

    stamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
    stamped = dest_dir / f"orc_ribb.db.bak-{stamp}"
    latest = dest_dir / LATEST_NAME

    shutil.copy2(src, stamped)
    shutil.copy2(src, latest)

    _prune_old_backups(dest_dir, keep_last=max(1, int(keep_last)))
    log.info("Backup salvo: %s (latest + últimos %s)", stamped.name, keep_last)
    return stamped


def _prune_old_backups(dest_dir: Path, *, keep_last: int) -> None:
    """Remove backups datados antigos; nunca apaga o bak-latest aqui."""
    dated = sorted(
        dest_dir.glob("orc_ribb.db.bak-????-??-??-??????"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for old in dated[keep_last:]:
        try:
            old.unlink(missing_ok=True)
        except OSError as exc:
            log.warning("Backup: não removeu %s (%s)", old, exc)
