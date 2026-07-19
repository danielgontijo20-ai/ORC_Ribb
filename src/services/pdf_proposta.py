"""Geração simples de PDF da proposta comercial."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
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
    normal = styles["Normal"]
    small_left = ParagraphStyle(
        "SmallLeft", parent=normal, fontSize=9, leading=12, alignment=TA_LEFT
    )
    small_right = ParagraphStyle(
        "SmallRight", parent=normal, fontSize=9, leading=12, alignment=TA_RIGHT
    )
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

    # Logo cabeçalho — margem esquerda
    logo_w, logo_h = 70.0, 36.0
    if logo_cabecalho and Path(logo_cabecalho).exists():
        story.append(_logo_cell(logo_cabecalho, logo_w, logo_h))
        story.append(Spacer(1, 3 * mm))

    # Empresa (esquerda) | Orçamento/Cliente (direita) — mesma altura
    empresa_txt = Paragraph(
        f"<b>Nome da empresa:</b> {empresa.get('empresa_nome') or '-'}<br/>"
        f"<b>CNPJ da empresa:</b> {empresa.get('empresa_cnpj') or '-'}<br/>"
        f"<b>Telefone da empresa:</b> {empresa.get('empresa_telefone') or '-'}<br/>"
        f"<b>E-mail da empresa:</b> {empresa.get('empresa_email') or '-'}",
        small_left,
    )
    cliente_txt = Paragraph(
        f"<b>Número do Orçamento:</b> {orcamento.get('numero') or '-'}<br/>"
        f"<b>Nome do Cliente:</b> {orcamento.get('cliente_nome') or '-'}<br/>"
        f"<b>CNPJ do Cliente:</b> {orcamento.get('cliente_doc') or '-'}<br/>"
        f"<b>Aos cuidados do(a) Sr.(a):</b> {orcamento.get('solicitante') or '-'}",
        small_right,
    )
    header_info = Table(
        [[empresa_txt, cliente_txt]],
        colWidths=[90 * mm, 90 * mm],
    )
    header_info.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (0, 0), (0, 0), "LEFT"),
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                ("LEFTPADDING", (0, 0), (0, 0), 0),
                ("RIGHTPADDING", (1, 0), (1, 0), 0),
            ]
        )
    )
    story.append(header_info)
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
            small_left,
        )
    )
    story.append(Spacer(1, 4 * mm))
    story.append(
        Paragraph(
            f"<b>Observações Adicionais:</b><br/>{orcamento.get('informacoes_adicionais') or '-'}",
            small_left,
        )
    )
    story.append(Spacer(1, 8 * mm))

    # Rodapé: orçamentista à esquerda, logo alinhada à margem direita
    rodape_logo_w, rodape_logo_h = 60.0, 30.0
    orcamentista_txt = Paragraph(
        f"{orcamento.get('orcamentista_nome') or '-'}<br/>"
        f"{orcamento.get('orcamentista_cargo') or '-'}<br/>"
        f"{orcamento.get('orcamentista_telefone') or '-'}<br/>"
        f"{orcamento.get('orcamentista_email') or '-'}",
        small_left,
    )
    footer = Table(
        [[orcamentista_txt, _logo_cell(logo_rodape, rodape_logo_w, rodape_logo_h)]],
        colWidths=[112 * mm, 68 * mm],
    )
    footer.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (0, 0), "LEFT"),
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                ("LEFTPADDING", (0, 0), (0, 0), 0),
                ("RIGHTPADDING", (1, 0), (1, 0), 0),
            ]
        )
    )
    story.append(KeepTogether([footer]))

    doc.build(story)
    return buffer.getvalue()
