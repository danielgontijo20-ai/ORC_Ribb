"""Geração simples de PDF da proposta comercial."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def gerar_pdf_proposta(
    *,
    empresa: dict,
    orcamento: dict,
    itens: list[dict],
    logo_cabecalho: str | None = None,
    logo_rodape: str | None = None,
) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
    )
    styles = getSampleStyleSheet()
    title = ParagraphStyle("TitleBR", parent=styles["Heading1"], fontSize=14, spaceAfter=8)
    normal = styles["Normal"]
    small = ParagraphStyle("Small", parent=normal, fontSize=9, leading=12)

    story = []

    if logo_cabecalho and Path(logo_cabecalho).exists():
        story.append(Image(logo_cabecalho, width=35 * mm, height=18 * mm))
        story.append(Spacer(1, 4 * mm))

    story.append(Paragraph(empresa.get("empresa_nome") or "Empresa", title))
    story.append(
        Paragraph(
            f"CNPJ: {empresa.get('empresa_cnpj') or '-'}<br/>"
            f"Tel: {empresa.get('empresa_telefone') or '-'}<br/>"
            f"E-mail: {empresa.get('empresa_email') or '-'}",
            small,
        )
    )
    story.append(Spacer(1, 6 * mm))

    story.append(
        Paragraph(
            f"<b>Orçamento:</b> {orcamento.get('numero') or '-'}<br/>"
            f"<b>Cliente:</b> {orcamento.get('cliente_nome') or '-'}<br/>"
            f"<b>CNPJ:</b> {orcamento.get('cliente_doc') or '-'}<br/>"
            f"<b>Aos cuidados do(a) Sr.(a):</b> {orcamento.get('solicitante') or '-'}",
            small,
        )
    )
    story.append(Spacer(1, 6 * mm))

    data = [["N°", "Descrição", "Und", "Qtd", "Preço Unit.", "Valor total"]]
    for idx, item in enumerate(itens, start=1):
        data.append(
            [
                f"{idx:02d}",
                item.get("descricao") or "",
                item.get("unidade") or "",
                f"{item.get('quantidade', 0):.0f}",
                f"R$ {item.get('preco_unitario', 0):,.2f}".replace(",", "X")
                .replace(".", ",")
                .replace("X", "."),
                f"R$ {item.get('valor_venda_total', 0):,.2f}".replace(",", "X")
                .replace(".", ",")
                .replace("X", "."),
            ]
        )

    table = Table(data, colWidths=[12 * mm, 85 * mm, 12 * mm, 15 * mm, 28 * mm, 28 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f3b5b")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f7fa")]),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 6 * mm))

    story.append(
        Paragraph(
            "<b>Condições Gerais de Fornecimento</b><br/>"
            f"Validade da Proposta: {orcamento.get('validade_proposta')}<br/>"
            f"Prazo de pagamento: {orcamento.get('prazo_pagamento')}<br/>"
            f"Prazo de entrega: {orcamento.get('prazo_entrega')}<br/>"
            f"Frete: {orcamento.get('frete_tipo')}<br/>"
            f"Impostos: {orcamento.get('impostos')}",
            small,
        )
    )
    story.append(Spacer(1, 4 * mm))
    story.append(
        Paragraph(
            f"<b>Observações Adicionais:</b><br/>{orcamento.get('informacoes_adicionais') or '-'}",
            small,
        )
    )
    story.append(Spacer(1, 8 * mm))
    story.append(
        Paragraph(
            f"{orcamento.get('orcamentista_nome') or '-'}<br/>"
            f"{orcamento.get('orcamentista_cargo') or '-'}<br/>"
            f"{orcamento.get('orcamentista_telefone') or '-'}<br/>"
            f"{orcamento.get('orcamentista_email') or '-'}",
            small,
        )
    )

    if logo_rodape and Path(logo_rodape).exists():
        story.append(Spacer(1, 6 * mm))
        story.append(Image(logo_rodape, width=30 * mm, height=15 * mm))

    doc.build(story)
    return buffer.getvalue()
