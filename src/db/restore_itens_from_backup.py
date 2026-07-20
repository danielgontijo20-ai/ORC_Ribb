"""
Restaura orcamento_itens a partir de um backup .db (quando o CASCADE apagou os itens).

Uso na VPS:
    cd /var/www/ORC_Ribb
    source .venv/bin/activate
    python -m src.db.restore_itens_from_backup /root/orc-backups/orc_ribb.db.bak-AAAA-MM-DD-HHMMSS

Só reinsere itens cujo orcamento_id ainda existe e que estão ausentes no banco atual.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

from .database import DB_PATH, connect


def restaurar_itens(backup_path: Path, db_path: Path = DB_PATH) -> int:
    if not backup_path.is_file():
        raise FileNotFoundError(f"Backup não encontrado: {backup_path}")

    bak = sqlite3.connect(str(backup_path))
    bak.row_factory = sqlite3.Row
    try:
        itens = list(bak.execute("SELECT * FROM orcamento_itens ORDER BY id"))
    finally:
        bak.close()

    if not itens:
        print("Backup sem itens.")
        return 0

    inseridos = 0
    with connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys=ON")
        live_cols = {
            r["name"] for r in conn.execute("PRAGMA table_info(orcamento_itens)")
        }
        orc_ids = {
            r["id"]
            for r in conn.execute("SELECT id FROM orcamentos").fetchall()
        }
        for row in itens:
            d = dict(row)
            oid = d.get("orcamento_id")
            if oid not in orc_ids:
                continue
            existe = conn.execute(
                "SELECT 1 FROM orcamento_itens WHERE id = ?",
                (d.get("id"),),
            ).fetchone()
            if existe:
                continue
            # Evita duplicar o mesmo item lógico se o id mudou
            mesma = conn.execute(
                """
                SELECT 1 FROM orcamento_itens
                WHERE orcamento_id = ? AND descricao = ?
                  AND IFNULL(quantidade, -1) = IFNULL(?, -1)
                  AND IFNULL(preco_total, -1) = IFNULL(?, -1)
                LIMIT 1
                """,
                (
                    oid,
                    d.get("descricao"),
                    d.get("quantidade"),
                    d.get("preco_total"),
                ),
            ).fetchone()
            if mesma:
                continue
            cols = [c for c in d.keys() if c in live_cols]
            placeholders = ", ".join("?" for _ in cols)
            conn.execute(
                f"INSERT INTO orcamento_itens ({', '.join(cols)}) "
                f"VALUES ({placeholders})",
                [d[c] for c in cols],
            )
            inseridos += 1
        conn.commit()

        vazios = conn.execute(
            """
            SELECT o.id, o.numero, o.valor_total
            FROM orcamentos o
            LEFT JOIN orcamento_itens i ON i.orcamento_id = o.id
            GROUP BY o.id
            HAVING COUNT(i.id) = 0 AND IFNULL(o.valor_total, 0) > 0
            ORDER BY o.id
            """
        ).fetchall()
        if vazios:
            print(
                f"Atenção: ainda há {len(vazios)} orçamento(s) com valor e sem itens."
            )
            for r in vazios[:20]:
                print(f"  - id={r['id']} {r['numero']} valor={r['valor_total']}")

    print(f"Itens restaurados: {inseridos}")
    return inseridos


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print(
            "Uso: python -m src.db.restore_itens_from_backup "
            "/caminho/do/backup.db"
        )
        return 2
    n = restaurar_itens(Path(args[0]))
    return 0 if n >= 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
