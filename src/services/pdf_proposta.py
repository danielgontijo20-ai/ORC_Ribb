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
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def _brl(valor: float) -> str:
    return (
        f"R$ {float(valor or 0):,.2f}".replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )


def _logo_cell(path: str | None, width_mm: float, height_mm: float):
    if path and Path(path).exists():
        return Image(path, width=width_mm * mm, height=height_mm * mm)
    return Paragraph("", getSampleStyleSheet()["Normal"])


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
    title = ParagraphStyle(
        "TitleBR", parent=styles["Heading1"], fontSize=14, spaceAfter=2, spaceBefore=0
    )
    normal = styles["Normal"]
    small = ParagraphStyle("Small", parent=normal, fontSize=9, leading=12)
    total_style = ParagraphStyle(
        "TotalBR",
        parent=normal,
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#0A3358"),
        spaceBefore=4,
        spaceAfter=4,
    )

    story = []

    # Cabeçalho: logo 2x maior, margem esquerda, mesma linha das informações
    logo_w, logo_h = 70.0, 36.0
    empresa_txt = Paragraph(
        f"<b>{empresa.get('empresa_nome') or 'Empresa'}</b><br/>"
        f"CNPJ: {empresa.get('empresa_cnpj') or '-'}<br/>"
        f"Tel: {empresa.get('empresa_telefone') or '-'}<br/>"
        f"E-mail: {empresa.get('empresa_email') or '-'}",
        small,
    )
    header = Table(
        [[_logo_cell(logo_cabecalho, logo_w, logo_h), empresa_txt]],
        colWidths=[78 * mm, 102 * mm],
    )
    header.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (0, 0), 0),
                ("RIGHTPADDING", (0, 0), (0, 0), 4),
                ("LEFTPADDING", (1, 0), (1, 0), 6),
                ("ALIGN", (0, 0), (0, 0), "LEFT"),
            ]
        )
    )
    story.append(header)
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
    valor_itens = 0.0
    for idx, item in enumerate(itens, start=1):
        linha_total = float(item.get("valor_venda_total", 0) or 0)
        valor_itens += linha_total
        data.append(
            [
                f"{idx:02d}",
                item.get("descricao") or "",
                item.get("unidade") or "",
                f"{item.get('quantidade', 0):.0f}",
                _brl(item.get("preco_unitario", 0)),
                _brl(linha_total),
            ]
        )

    # Linha de total dos itens
    data.append(["", "", "", "", "TOTAL", _brl(valor_itens)])

    table = Table(data, colWidths=[12 * mm, 80 * mm, 12 * mm, 15 * mm, 28 * mm, 33 * mm])
    last = len(data) - 1
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f3b5b")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, last - 1), 0.4, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, last - 1),
                    [colors.white, colors.HexColor("#f5f7fa")],
                ),
                ("BACKGROUND", (0, last), (-1, last), colors.HexColor("#EAF1F6")),
                ("FONTNAME", (4, last), (-1, last), "Helvetica-Bold"),
                ("FONTSIZE", (4, last), (-1, last), 9),
                ("ALIGN", (4, last), (-1, last), "RIGHT"),
                ("LINEABOVE", (0, last), (-1, last), 1, colors.HexColor("#0A3358")),
                ("TOPPADDING", (0, last), (-1, last), 6),
                ("BOTTOMPADDING", (0, last), (-1, last), 6),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 3 * mm))
    story.append(
        Paragraph(
            f"<b>Valor total dos itens: {_brl(orcamento.get('valor_total', valor_itens))}</b>",
            total_style,
        )
    )
    story.append(Spacer(1, 5 * mm))

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

    # Rodapé: logo 2x maior à esquerda, mesma linha do orçamentista
    rodape_logo_w, rodape_logo_h = 60.0, 30.0
    orcamentista_txt = Paragraph(
        f"{orcamento.get('orcamentista_nome') or '-'}<br/>"
        f"{orcamento.get('orcamentista_cargo') or '-'}<br/>"
        f"{orcamento.get('orcamentista_telefone') or '-'}<br/>"
        f"{orcamento.get('orcamentista_email') or '-'}",
        small,
    )
    footer = Table(
        [[_logo_cell(logo_rodape, rodape_logo_w, rodape_logo_h), orcamentista_txt]],
        colWidths=[68 * mm, 112 * mm],
    )
    footer.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (0, 0), 0),
                ("LEFTPADDING", (1, 0), (1, 0), 6),
                ("ALIGN", (0, 0), (0, 0), "LEFT"),
            ]
        )
    )
    story.append(KeepTogether([footer]))

    # title unused but kept for compatibility if styles change
    _ = title

    doc.build(story)
    return buffer.getvalue()
