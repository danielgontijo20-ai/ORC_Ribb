"""Usuários, papéis e permissões para a camada web."""

from __future__ import annotations

import sqlite3
from typing import Any

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

PERMISSOES_SEED: list[tuple[str, str]] = [
    ("menu.ver", "Acessar menu principal"),
    ("orcamento.ver", "Ver orçamentos"),
    ("orcamento.criar", "Criar e editar orçamentos"),
    ("orcamento.aprovar", "Aprovar orçamentos"),
    ("orcamento.pdf", "Gerar PDF de orçamentos"),
    ("cadastros.ver", "Ver cadastros"),
    ("cadastros.editar", "Editar cadastros"),
    ("historico_vendas.ver", "Ver histórico de vendas"),
    ("usuarios.gerenciar", "Gerenciar usuários"),
]

PAPEIS_SEED: dict[str, list[str]] = {
    "admin": [p[0] for p in PERMISSOES_SEED],
    "orcamentista": [
        "menu.ver",
        "orcamento.ver",
        "orcamento.criar",
        "orcamento.pdf",
        "cadastros.ver",
        "cadastros.editar",
        "historico_vendas.ver",
    ],
    "aprovador": [
        "menu.ver",
        "orcamento.ver",
        "orcamento.aprovar",
        "orcamento.pdf",
        "historico_vendas.ver",
    ],
    "consulta": [
        "menu.ver",
        "orcamento.ver",
        "orcamento.pdf",
        "cadastros.ver",
        "historico_vendas.ver",
    ],
}

PAPEIS_NOMES = {
    "admin": "Administrador",
    "orcamentista": "Orçamentista",
    "aprovador": "Aprovador",
    "consulta": "Consulta",
}


def hash_senha(senha: str) -> str:
    return pwd_context.hash(senha)


def verificar_senha(senha: str, senha_hash: str) -> bool:
    try:
        return pwd_context.verify(senha, senha_hash)
    except Exception:
        return False


def ensure_auth_seed(conn: sqlite3.Connection) -> None:
    """Cria papéis/permissões e usuário admin padrão se não existirem."""
    for codigo, desc in PERMISSOES_SEED:
        conn.execute(
            "INSERT OR IGNORE INTO permissoes (codigo, descricao) VALUES (?, ?)",
            (codigo, desc),
        )

    for codigo, nome in PAPEIS_NOMES.items():
        conn.execute(
            "INSERT OR IGNORE INTO papeis (codigo, nome) VALUES (?, ?)",
            (codigo, nome),
        )

    for papel_codigo, perms in PAPEIS_SEED.items():
        papel = conn.execute(
            "SELECT id FROM papeis WHERE codigo = ?", (papel_codigo,)
        ).fetchone()
        if not papel:
            continue
        for perm_codigo in perms:
            perm = conn.execute(
                "SELECT id FROM permissoes WHERE codigo = ?", (perm_codigo,)
            ).fetchone()
            if not perm:
                continue
            conn.execute(
                """
                INSERT OR IGNORE INTO papel_permissoes (papel_id, permissao_id)
                VALUES (?, ?)
                """,
                (papel["id"], perm["id"]),
            )

    admin = conn.execute(
        "SELECT id FROM usuarios WHERE email = ?", ("admin@ribbontech.com",)
    ).fetchone()
    if not admin:
        papel_admin = conn.execute(
            "SELECT id FROM papeis WHERE codigo = 'admin'"
        ).fetchone()
        if papel_admin:
            conn.execute(
                """
                INSERT INTO usuarios (nome, email, senha_hash, papel_id, ativo)
                VALUES (?, ?, ?, ?, 1)
                """,
                (
                    "Administrador",
                    "admin@ribbontech.com",
                    hash_senha("admin123"),
                    papel_admin["id"],
                ),
            )
    conn.commit()


def autenticar(
    conn: sqlite3.Connection, email: str, senha: str
) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT u.id, u.nome, u.email, u.senha_hash, u.ativo,
               p.id AS papel_id, p.codigo AS papel_codigo, p.nome AS papel_nome
        FROM usuarios u
        JOIN papeis p ON p.id = u.papel_id
        WHERE lower(u.email) = lower(?)
        LIMIT 1
        """,
        (email.strip(),),
    ).fetchone()
    if not row or not row["ativo"]:
        return None
    if not verificar_senha(senha, row["senha_hash"]):
        return None
    user = dict(row)
    user.pop("senha_hash", None)
    user["permissoes"] = listar_permissoes_usuario(conn, int(user["id"]))
    return user


def listar_permissoes_usuario(conn: sqlite3.Connection, usuario_id: int) -> list[str]:
    rows = conn.execute(
        """
        SELECT DISTINCT pe.codigo
        FROM usuarios u
        JOIN papel_permissoes pp ON pp.papel_id = u.papel_id
        JOIN permissoes pe ON pe.id = pp.permissao_id
        WHERE u.id = ?
        ORDER BY pe.codigo
        """,
        (usuario_id,),
    ).fetchall()
    return [r["codigo"] for r in rows]


def obter_usuario(conn: sqlite3.Connection, usuario_id: int) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT u.id, u.nome, u.email, u.ativo,
               p.id AS papel_id, p.codigo AS papel_codigo, p.nome AS papel_nome
        FROM usuarios u
        JOIN papeis p ON p.id = u.papel_id
        WHERE u.id = ?
        """,
        (usuario_id,),
    ).fetchone()
    if not row:
        return None
    user = dict(row)
    user["permissoes"] = listar_permissoes_usuario(conn, int(user["id"]))
    return user


def usuario_tem_permissao(user: dict[str, Any] | None, codigo: str) -> bool:
    if not user:
        return False
    perms = user.get("permissoes") or []
    if user.get("papel_codigo") == "admin":
        return True
    return codigo in perms
