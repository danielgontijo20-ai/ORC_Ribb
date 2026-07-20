"""Geração de PDF da memória de cálculo."""

from __future__ import annotations

from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from src.ui.formatters import brl, pct
from src.services.memoria_format import coletar_secoes_memoria, resumo_memoria


def _esc(texto: str) -> str:
    return (
        str(texto or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def gerar_pdf_memoria(
    *,
    itens: list[dict],
    rascunho: dict | None = None,
    orcamento: dict | None = None,
    empresa: dict | None = None,
) -> bytes:
    """PDF com resumo (lucro/média) + tabelas por item da memória de cálculo."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
    )
    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "MemTitle",
        parent=styles["Heading1"],
        fontSize=14,
        leading=18,
        textColor=colors.HexColor("#0A3358"),
        spaceAfter=4,
    )
    subtitle = ParagraphStyle(
        "MemSub",
        parent=styles["Normal"],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#4E667A"),
        spaceAfter=6,
    )
    section = ParagraphStyle(
        "MemSection",
        parent=styles["Heading2"],
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#0A3358"),
        spaceBefore=8,
        spaceAfter=4,
    )
    caption = ParagraphStyle(
        "MemCap",
        parent=styles["Normal"],
        fontSize=8,
        leading=10,
        textColor=colors.white,
        alignment=TA_LEFT,
    )
    cell = ParagraphStyle(
        "MemCell",
        parent=styles["Normal"],
        fontSize=8,
        leading=10,
        alignment=TA_LEFT,
    )
    cell_r = ParagraphStyle(
        "MemCellR",
        parent=cell,
        alignment=TA_RIGHT,
    )
    summary = ParagraphStyle(
        "MemSum",
        parent=styles["Normal"],
        fontSize=10,
        leading=13,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#10283D"),
    )

    story = []
    empresa = empresa or {}
    orcamento = orcamento or {}

    story.append(Paragraph("Memória de Cálculo", title))
    meta_parts = []
    if empresa.get("empresa_nome"):
        meta_parts.append(_esc(empresa.get("empresa_nome")))
    if orcamento.get("numero"):
        meta_parts.append(f"Orçamento {_esc(orcamento.get('numero'))}")
    if orcamento.get("cliente_nome"):
        meta_parts.append(f"Cliente: {_esc(orcamento.get('cliente_nome'))}")
    if meta_parts:
        story.append(Paragraph(" • ".join(meta_parts), subtitle))

    lucro, media = resumo_memoria(itens or [], rascunho)
    resumo_tbl = Table(
        [
            [
                Paragraph(f"<b>Lucro total</b><br/>{brl(lucro)}", summary),
                Paragraph(f"<b>Média de margens</b><br/>{pct(media)}", summary),
            ]
        ],
        colWidths=[90 * mm, 90 * mm],
    )
    resumo_tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EAF1F6")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#0A3358")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#9FB4C7")),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    story.append(resumo_tbl)
    story.append(Spacer(1, 4 * mm))

    def _mini_tabela(rotulo: str, linhas: list[tuple[str, str]], largura: float):
        data = [
            [
                Paragraph(f"<b>{_esc(rotulo)}</b>", caption),
                Paragraph("<b>Valor</b>", caption),
            ]
        ]
        if not linhas:
            data.append(
                [
                    Paragraph("—", cell),
                    Paragraph("—", cell_r),
                ]
            )
        else:
            for campo, valor in linhas:
                data.append(
                    [
                        Paragraph(_esc(campo), cell),
                        Paragraph(_esc(valor), cell_r),
                    ]
                )
        col_a = largura * 0.55
        col_b = largura * 0.45
        tbl = Table(data, colWidths=[col_a, col_b])
        tbl.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0A3358")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTSIZE", (0, 0), (-1, -1), 7),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#6F8AA3")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, -1), 2),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                    ("LEFTPADDING", (0, 0), (-1, -1), 3),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.white, colors.HexColor("#e8f0f7")],
                    ),
                ]
            )
        )
        return tbl

    secoes = coletar_secoes_memoria(itens or [], rascunho)
    if not secoes:
        story.append(Paragraph("Sem dados de memória de cálculo.", cell))
    else:
        for sec in secoes:
            story.append(Paragraph(_esc(sec["titulo"]), section))
            # Parâmetros à esquerda | Resultado à direita
            half = 88 * mm
            left = _mini_tabela(
                "Parâmetros de entrada", sec.get("params") or [], half
            )
            right = _mini_tabela(
                "Resultado do cálculo", sec.get("calculo") or [], half
            )
            pair = Table([[left, right]], colWidths=[half + 2 * mm, half + 2 * mm])
            pair.setStyle(
                TableStyle(
                    [
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 0),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                        ("TOPPADDING", (0, 0), (-1, -1), 0),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                    ]
                )
            )
            story.append(pair)
            story.append(Spacer(1, 3 * mm))

    doc.build(story)
    return buffer.getvalue()
