"""
Apaga todo o histórico de orçamentos e zera o contador (próximo = ORC-00001).

Uso na VPS:
    cd /var/www/ORC_Ribb
    systemctl stop orc-ribb
    source .venv/bin/activate
    cp -a data/database/orc_ribb.db /root/orc-backups/orc_ribb.db.bak-$(date +%F-%H%M%S)
    python -m src.db.limpar_historico_orcamentos
    systemctl start orc-ribb
"""

from __future__ import annotations

import sys

from .database import DB_PATH, connect


def limpar_historico(db_path=DB_PATH) -> dict[str, int]:
    with connect(db_path) as conn:
        n_itens = conn.execute("SELECT COUNT(*) AS c FROM orcamento_itens").fetchone()["c"]
        n_orc = conn.execute("SELECT COUNT(*) AS c FROM orcamentos").fetchone()["c"]

        conn.execute("DELETE FROM orcamento_itens")
        conn.execute("DELETE FROM orcamentos")

        # Reinicia AUTOINCREMENT das tabelas
        conn.execute(
            "DELETE FROM sqlite_sequence WHERE name IN ('orcamentos', 'orcamento_itens')"
        )

        # Próximo número volta para ORC-00001
        conn.execute(
            """
            INSERT INTO configuracoes (chave, valor) VALUES (?, ?)
            ON CONFLICT(chave) DO UPDATE SET valor = excluded.valor
            """,
            ("proximo_numero_orcamento", "1"),
        )
        conn.commit()

        resto_orc = conn.execute("SELECT COUNT(*) AS c FROM orcamentos").fetchone()["c"]
        resto_itens = conn.execute(
            "SELECT COUNT(*) AS c FROM orcamento_itens"
        ).fetchone()["c"]
        prox = conn.execute(
            "SELECT valor FROM configuracoes WHERE chave = ?",
            ("proximo_numero_orcamento",),
        ).fetchone()
        prox_val = (prox["valor"] if prox else None) or "?"

    return {
        "orcamentos_apagados": int(n_orc),
        "itens_apagados": int(n_itens),
        "orcamentos_restantes": int(resto_orc),
        "itens_restantes": int(resto_itens),
        "proximo_numero": int(prox_val) if str(prox_val).isdigit() else -1,
    }


def main() -> int:
    print(f"Banco: {DB_PATH}")
    stats = limpar_historico()
    print(
        f"Apagados: {stats['orcamentos_apagados']} orçamento(s), "
        f"{stats['itens_apagados']} item(ns)."
    )
    print(
        f"Restantes: {stats['orcamentos_restantes']} orçamento(s), "
        f"{stats['itens_restantes']} item(ns)."
    )
    print(f"Próximo número: ORC-{stats['proximo_numero']:05d}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
