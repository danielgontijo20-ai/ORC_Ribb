"""
Importa a planilha Banco_RBT.xlsx para o banco SQLite.

Como usar (na pasta do projeto):
    python -m src.db.import_banco_rbt

O que este script faz, passo a passo:
1. Apaga o banco antigo (se existir) para reimportar limpo
2. Cria as tabelas (schema.sql)
3. Lê cada aba da planilha
4. Grava os dados nas tabelas correspondentes
5. Mostra um resumo no final
"""

from __future__ import annotations

import argparse
import re
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

from .database import DB_PATH, ROOT_DIR, connect, init_db

DEFAULT_XLSX = ROOT_DIR / "data" / "planilhas" / "Banco_RBT.xlsx"


def parse_br_number(value) -> float | None:
    """Converte números no formato brasileiro (1.234,56) para float."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip()
    if not text:
        return None

    text = text.replace("R$", "").strip()
    # Se tem vírgula, assume formato BR: milhar com ponto e decimal com vírgula
    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def parse_date(value) -> str | None:
    """Normaliza datas para texto ISO (YYYY-MM-DD HH:MM:SS) quando possível."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime().strftime("%Y-%m-%d %H:%M:%S")

    text = str(value).strip()
    if not text:
        return None

    for fmt in (
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ):
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
    return text


def clean_text(value) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    return text or None


def normalize_doc(value) -> str | None:
    """Mantém CNPJ/CPF legível, só tira espaços extras."""
    text = clean_text(value)
    if not text:
        return None
    return re.sub(r"\s+", "", text)


def reset_database(db_path: Path) -> None:
    if db_path.exists():
        db_path.unlink()
    init_db(db_path)


def import_materias_primas(conn: sqlite3.Connection, xlsx: Path) -> int:
    df = pd.read_excel(xlsx, sheet_name="Materia_Prima")
    rows = []
    for _, row in df.iterrows():
        codigo = clean_text(row.get("Código"))
        nome = clean_text(row.get("Matéria Prima"))
        if not codigo or not nome:
            continue
        rows.append(
            (
                codigo,
                nome,
                parse_br_number(row.get("Preço de compra")),
                parse_br_number(row.get("Custo")) or 0.0,
                parse_date(row.get("Última Atualização")),
                clean_text(row.get("Observações")),
            )
        )
    conn.executemany(
        """
        INSERT INTO materias_primas
            (codigo, nome, preco_compra, custo, ultima_atualizacao, observacoes)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    return len(rows)


def import_tubetes(conn: sqlite3.Connection, xlsx: Path) -> int:
    df = pd.read_excel(xlsx, sheet_name="Tubetes")
    # A coluna de custo pode vir como 'Custo ' (com espaço)
    custo_col = "Custo " if "Custo " in df.columns else "Custo"
    rows = []
    for _, row in df.iterrows():
        codigo = clean_text(row.get("Código"))
        nome = clean_text(row.get("Tubete"))
        if not codigo or not nome:
            continue
        rows.append(
            (
                codigo,
                nome,
                parse_br_number(row.get("Preço Compra")),
                parse_br_number(row.get(custo_col)) or 0.0,
            )
        )
    conn.executemany(
        """
        INSERT INTO tubetes (codigo, nome, preco_compra, custo)
        VALUES (?, ?, ?, ?)
        """,
        rows,
    )
    return len(rows)


def import_caixas(conn: sqlite3.Connection, xlsx: Path) -> int:
    df = pd.read_excel(xlsx, sheet_name="Caixas")
    rows = []
    for _, row in df.iterrows():
        codigo = clean_text(row.get("Código"))
        nome = clean_text(row.get("Caixa"))
        if not codigo or not nome:
            continue
        rows.append((codigo, nome, parse_br_number(row.get("Custo")) or 0.0))
    conn.executemany(
        """
        INSERT INTO caixas (codigo, nome, custo)
        VALUES (?, ?, ?)
        """,
        rows,
    )
    return len(rows)


def import_facas(conn: sqlite3.Connection, xlsx: Path) -> int:
    df = pd.read_excel(xlsx, sheet_name="Facas")
    # A planilha tem uma faca 100x100 duplicada; mantemos a primeira.
    df = df.drop_duplicates(subset=["Código"], keep="first")
    rows = []
    for _, row in df.iterrows():
        codigo = clean_text(row.get("Código"))
        tipo = clean_text(row.get("Tipo Faca"))
        if not codigo or not tipo:
            continue
        largura = parse_br_number(row.get("Largura")) or 0.0
        altura = parse_br_number(row.get("Altura")) or 0.0
        gap_lateral = parse_br_number(row.get("Gap Lateral")) or 0.0
        gap_vertical = parse_br_number(row.get("Gap vertical"))
        area = parse_br_number(row.get("área"))
        if area is None:
            gv = gap_vertical or 0.0
            area = (largura + gap_lateral) * (altura + gv)
        rows.append(
            (codigo, tipo, largura, altura, gap_lateral, gap_vertical, area)
        )
    conn.executemany(
        """
        INSERT INTO facas
            (codigo, tipo_faca, largura, altura, gap_lateral, gap_vertical, area)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    return len(rows)


def import_segmentos_e_produtos(conn: sqlite3.Connection, xlsx: Path) -> tuple[int, int]:
    df = pd.read_excel(xlsx, sheet_name="Segmento")
    segmentos = sorted(
        {
            clean_text(v)
            for v in df["Segmento"].tolist()
            if clean_text(v)
        }
    )
    conn.executemany(
        "INSERT INTO segmentos (nome) VALUES (?)",
        [(nome,) for nome in segmentos],
    )
    segmento_ids = {
        row["nome"]: row["id"]
        for row in conn.execute("SELECT id, nome FROM segmentos")
    }

    produtos = []
    for _, row in df.iterrows():
        codigo = clean_text(row.get("Código"))
        descricao = clean_text(row.get("Descrição"))
        segmento = clean_text(row.get("Segmento"))
        if not codigo or not descricao:
            continue
        produtos.append(
            (codigo, descricao, segmento_ids.get(segmento) if segmento else None)
        )

    conn.executemany(
        """
        INSERT OR IGNORE INTO produtos (codigo, descricao, segmento_id)
        VALUES (?, ?, ?)
        """,
        produtos,
    )
    return len(segmentos), len(produtos)


def import_faturamento_e_clientes(conn: sqlite3.Connection, xlsx: Path) -> tuple[int, int]:
    df = pd.read_excel(xlsx, sheet_name="Faturamento")
    df = df.dropna(subset=["Número", "CNPJ/CPF"], how="any")

    # 1) Clientes únicos por CNPJ/CPF (mantém o nome mais recente)
    clientes: dict[str, dict] = {}
    for _, row in df.iterrows():
        doc = normalize_doc(row.get("CNPJ/CPF"))
        nome = clean_text(row.get("Nome"))
        if not doc or not nome:
            continue
        clientes[doc] = {
            "cnpj_cpf": doc,
            "nome": nome,
            "uf": clean_text(row.get("UF")),
        }

    conn.executemany(
        """
        INSERT INTO clientes (cnpj_cpf, nome, uf)
        VALUES (?, ?, ?)
        """,
        [(c["cnpj_cpf"], c["nome"], c["uf"]) for c in clientes.values()],
    )
    cliente_ids = {
        row["cnpj_cpf"]: row["id"]
        for row in conn.execute("SELECT id, cnpj_cpf FROM clientes")
    }

    # 2) Linhas de faturamento
    fat_rows = []
    for _, row in df.iterrows():
        doc = normalize_doc(row.get("CNPJ/CPF"))
        if not doc:
            continue
        fat_rows.append(
            (
                clean_text(row.get("Número")),
                cliente_ids.get(doc),
                doc,
                clean_text(row.get("Nome")),
                parse_date(row.get("Data de emissão")),
                clean_text(row.get("Situação")),
                clean_text(row.get("UF")),
                clean_text(row.get("Natureza")),
                clean_text(row.get("Finalidade")),
                clean_text(row.get("Descrição")),
                clean_text(row.get("Código")),
                clean_text(row.get("Unidade")),
                parse_br_number(row.get("Quantidade")),
                parse_br_number(row.get("Valor unitário")),
                parse_br_number(row.get("Valor total")),
                clean_text(row.get("NCM")),
            )
        )

    conn.executemany(
        """
        INSERT INTO faturamento (
            numero_nota, cliente_id, cnpj_cpf, nome_cliente, data_emissao,
            situacao, uf, natureza, finalidade, descricao_item, codigo_item,
            unidade, quantidade, valor_unitario, valor_total, ncm
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        fat_rows,
    )
    return len(clientes), len(fat_rows)


def print_summary(conn: sqlite3.Connection) -> None:
    tables = [
        "clientes",
        "segmentos",
        "produtos",
        "materias_primas",
        "tubetes",
        "caixas",
        "facas",
        "faturamento",
    ]
    print("\n=== Resumo da importação ===")
    for table in tables:
        count = conn.execute(f"SELECT COUNT(*) AS c FROM {table}").fetchone()["c"]
        print(f"- {table}: {count}")


def run_import(xlsx: Path, db_path: Path) -> None:
    if not xlsx.exists():
        raise FileNotFoundError(
            f"Planilha não encontrada: {xlsx}\n"
            "Coloque o arquivo em data/planilhas/Banco_RBT.xlsx"
        )

    print(f"Planilha: {xlsx}")
    print(f"Banco:    {db_path}")
    print("Recriando banco...")
    reset_database(db_path)

    with connect(db_path) as conn:
        n_mp = import_materias_primas(conn, xlsx)
        n_tub = import_tubetes(conn, xlsx)
        n_cx = import_caixas(conn, xlsx)
        n_facas = import_facas(conn, xlsx)
        n_seg, n_prod = import_segmentos_e_produtos(conn, xlsx)
        n_cli, n_fat = import_faturamento_e_clientes(conn, xlsx)
        conn.commit()

        print("\nImportado com sucesso:")
        print(f"- materias_primas: {n_mp}")
        print(f"- tubetes: {n_tub}")
        print(f"- caixas: {n_cx}")
        print(f"- facas: {n_facas}")
        print(f"- segmentos: {n_seg}")
        print(f"- produtos: {n_prod}")
        print(f"- clientes: {n_cli}")
        print(f"- faturamento: {n_fat}")
        print_summary(conn)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Importa Banco_RBT.xlsx para o SQLite do ORC_Ribb"
    )
    parser.add_argument(
        "--xlsx",
        type=Path,
        default=DEFAULT_XLSX,
        help="Caminho da planilha (padrão: data/planilhas/Banco_RBT.xlsx)",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=DB_PATH,
        help="Caminho do banco SQLite (padrão: data/database/orc_ribb.db)",
    )
    args = parser.parse_args()
    run_import(args.xlsx, args.db)


if __name__ == "__main__":
    main()
