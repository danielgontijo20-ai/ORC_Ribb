"""Geração simples de PDF da proposta comercial."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
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
    small_center = ParagraphStyle(
        "SmallCenter", parent=normal, fontSize=9, leading=12, alignment=TA_CENTER
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

    # Logo cabeçalho — ~2x o tamanho anterior (70×36 → 140×72)
    logo_w, logo_h = 140.0, 72.0
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

    desc_style = ParagraphStyle(
        "ItemDesc",
        parent=normal,
        fontSize=8,
        leading=10,
        alignment=TA_LEFT,
        wordWrap="CJK",
    )
    head_style = ParagraphStyle(
        "ItemHead",
        parent=normal,
        fontSize=8,
        leading=10,
        textColor=colors.white,
        alignment=TA_LEFT,
    )
    cell_style = ParagraphStyle(
        "ItemCell",
        parent=normal,
        fontSize=8,
        leading=10,
        alignment=TA_LEFT,
    )
    cell_right = ParagraphStyle(
        "ItemCellR",
        parent=cell_style,
        alignment=TA_RIGHT,
    )

    def _esc(txt: str) -> str:
        return (
            str(txt or "")
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

    data = [
        [
            Paragraph("N°", head_style),
            Paragraph("Descrição", head_style),
            Paragraph("Und", head_style),
            Paragraph("Qtd", head_style),
            Paragraph("Preço Unit.", head_style),
            Paragraph("Valor total", head_style),
        ]
    ]
    valor_itens = 0.0
    for idx, item in enumerate(itens, start=1):
        linha_total = float(item.get("valor_venda_total", 0) or 0)
        valor_itens += linha_total
        data.append(
            [
                Paragraph(f"{idx:02d}", cell_style),
                # Paragraph quebra a descrição na linha de baixo (não invade Und/Qtd)
                Paragraph(_esc(item.get("descricao") or ""), desc_style),
                Paragraph(_esc(item.get("unidade") or ""), cell_style),
                Paragraph(f"{float(item.get('quantidade', 0) or 0):.0f}", cell_right),
                Paragraph(_brl(item.get("preco_unitario", 0)), cell_right),
                Paragraph(_brl(linha_total), cell_right),
            ]
        )

    data.append(
        [
            "",
            "",
            "",
            "",
            Paragraph("<b>TOTAL</b>", cell_right),
            Paragraph(f"<b>{_brl(valor_itens)}</b>", cell_right),
        ]
    )

    table = Table(data, colWidths=[12 * mm, 80 * mm, 12 * mm, 15 * mm, 28 * mm, 33 * mm])
    last = len(data) - 1
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f3b5b")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, last - 1), 0.4, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, last - 1),
                    [colors.white, colors.HexColor("#f5f7fa")],
                ),
                ("BACKGROUND", (0, last), (-1, last), colors.HexColor("#EAF1F6")),
                ("ALIGN", (3, 1), (-1, last), "RIGHT"),
                ("LINEABOVE", (0, last), (-1, last), 1, colors.HexColor("#0A3358")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (1, 0), (1, -1), 3),
                ("RIGHTPADDING", (1, 0), (1, -1), 3),
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

    # Orçamentista centralizado; logo do rodapé abaixo, no meio da página.
    rodape_logo_w, rodape_logo_h = 70.0, 36.0
    orcamentista_txt = Paragraph(
        f"{orcamento.get('orcamentista_nome') or '-'}<br/>"
        f"{orcamento.get('orcamentista_cargo') or '-'}<br/>"
        f"{orcamento.get('orcamentista_telefone') or '-'}<br/>"
        f"{orcamento.get('orcamentista_email') or '-'}",
        small_center,
    )
    footer_parts = [orcamentista_txt, Spacer(1, 4 * mm)]
    if logo_rodape and Path(logo_rodape).exists():
        logo_cell = _logo_cell(logo_rodape, rodape_logo_w, rodape_logo_h)
        logo_table = Table([[logo_cell]], colWidths=[180 * mm])
        logo_table.setStyle(
            TableStyle(
                [
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ]
            )
        )
        footer_parts.append(logo_table)
    story.append(KeepTogether(footer_parts))

    doc.build(story)
    return buffer.getvalue()
