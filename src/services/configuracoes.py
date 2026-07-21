"""Leitura e gravação dos valores nativos / configurações."""

from __future__ import annotations

import sqlite3

from src.db.defaults_config import DEFAULT_CONFIG, ensure_config_defaults

_defaults_ok = False


def carregar_config(conn: sqlite3.Connection) -> dict[str, str]:
    """Lê configurações. Só grava defaults uma vez por processo."""
    global _defaults_ok
    if not _defaults_ok:
        ensure_config_defaults(conn)
        conn.commit()
        _defaults_ok = True

    rows = conn.execute("SELECT chave, valor FROM configuracoes").fetchall()
    cfg = dict(DEFAULT_CONFIG)
    cfg.update(
        {r["chave"]: (r["valor"] if r["valor"] is not None else "") for r in rows}
    )
    return cfg


def salvar_config(conn: sqlite3.Connection, dados: dict[str, str]) -> None:
    for chave, valor in dados.items():
        conn.execute(
            """
            INSERT INTO configuracoes (chave, valor) VALUES (?, ?)
            ON CONFLICT(chave) DO UPDATE SET valor = excluded.valor
            """,
            (chave, "" if valor is None else str(valor)),
        )
    conn.commit()


def get_float(cfg: dict[str, str], chave: str, default: float = 0.0) -> float:
    raw = cfg.get(chave, str(default))
    try:
        return float(str(raw).replace(",", "."))
    except ValueError:
        return default


def proximo_numero_orcamento(conn: sqlite3.Connection) -> str:
    """Gera próximo número usando a MESMA conexão (evita database is locked)."""
    row = conn.execute(
        "SELECT valor FROM configuracoes WHERE chave = ?",
        ("proximo_numero_orcamento",),
    ).fetchone()
    atual = int((row["valor"] if row and row["valor"] else None) or "1")
    numero = f"ORC-{atual:05d}"
    conn.execute(
        """
        INSERT INTO configuracoes (chave, valor) VALUES (?, ?)
        ON CONFLICT(chave) DO UPDATE SET valor = excluded.valor
        """,
        ("proximo_numero_orcamento", str(atual + 1)),
    )
    conn.commit()
    return numero
