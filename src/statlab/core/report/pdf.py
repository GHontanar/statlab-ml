"""Informe PDF con reportlab, con la fuente Inter empaquetada (acentos y símbolos correctos)."""
from __future__ import annotations

import io
from importlib import resources
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from statlab.core.report.document import Bloque, Figura, Parrafo, SaltoPagina, Tabla, Titulo

TEXT = colors.HexColor("#1C1C1A")
MUTED = colors.HexColor("#55544F")
GRID = colors.HexColor("#E2E1DC")
HEAD = colors.HexColor("#F7F6F3")
ACCENT = colors.HexColor("#1F63BA")

_registered = False


def _fonts() -> tuple[str, str]:
    global _registered
    if not _registered:
        folder = resources.files("statlab.ui").joinpath("theme", "fonts")
        for name, file in (("Inter", "Inter-Regular.ttf"), ("Inter-SemiBold", "Inter-SemiBold.ttf")):
            pdfmetrics.registerFont(TTFont(name, io.BytesIO(folder.joinpath(file).read_bytes())))
        _registered = True
    return "Inter", "Inter-SemiBold"


def _styles():
    regular, bold = _fonts()
    return {
        0: ParagraphStyle("t0", fontName=bold, fontSize=20, leading=25, textColor=TEXT, spaceAfter=10),
        # keepWithNext: un título nunca se queda solo al final de una página
        1: ParagraphStyle("t1", fontName=bold, fontSize=14, leading=18, textColor=TEXT, spaceBefore=12, spaceAfter=6,
                          keepWithNext=1),
        2: ParagraphStyle("t2", fontName=bold, fontSize=11, leading=14, textColor=TEXT, spaceBefore=8, spaceAfter=4,
                          keepWithNext=1),
        "p": ParagraphStyle("p", fontName=regular, fontSize=9.5, leading=13.5, textColor=TEXT, spaceAfter=6),
        "nota": ParagraphStyle("n", fontName=regular, fontSize=8, leading=11, textColor=MUTED, spaceAfter=6),
        "celda": ParagraphStyle("c", fontName=regular, fontSize=8, leading=10, textColor=TEXT),
        "celda_der": ParagraphStyle("cd", fontName=regular, fontSize=8, leading=10, textColor=TEXT, alignment=2),
        "cab": ParagraphStyle("h", fontName=bold, fontSize=8, leading=10, textColor=MUTED),
    }


def _p(text: str, style) -> Paragraph:
    return Paragraph(escape(str(text)).replace("\n", "<br/>"), style)


def _table(t: Tabla, st) -> Table:
    data = [[_p(h, st["cab"]) for h in t.cabeceras]]
    for fila in t.filas:
        data.append([_p(v, st["celda"] if j in t.izquierda else st["celda_der"]) for j, v in enumerate(fila)])
    table = Table(data, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HEAD),
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, GRID),
        ("LINEBELOW", (0, 1), (-1, -1), 0.4, GRID),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return table


def render(bloques: list[Bloque], path: str | Path, titulo: str) -> Path:
    path = Path(path)
    st = _styles()
    regular, _ = _fonts()
    doc = SimpleDocTemplate(str(path), pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=2 * cm,
                            bottomMargin=2 * cm, title=titulo, author="StatLab")
    width = A4[0] - 4 * cm

    def footer(canvas, document) -> None:
        canvas.saveState()
        canvas.setFont(regular, 7.5)
        canvas.setFillColor(MUTED)
        canvas.drawString(2 * cm, 1.2 * cm, titulo)
        canvas.drawRightString(A4[0] - 2 * cm, 1.2 * cm, str(document.page))
        canvas.restoreState()

    story = []
    for b in bloques:
        if isinstance(b, Titulo):
            story.append(_p(b.texto, st[min(b.nivel, 2)]))
        elif isinstance(b, Parrafo):
            story.append(_p(b.texto, st["nota" if b.nota else "p"]))
        elif isinstance(b, Tabla):
            parts = [_table(b, st)]
            if b.pie:
                parts += [Spacer(1, 3), _p(b.pie, st["nota"])]
            story += [KeepTogether(parts), Spacer(1, 8)]
        elif isinstance(b, Figura):
            img = Image(io.BytesIO(b.png))
            ratio = img.imageHeight / img.imageWidth
            w = min(b.ancho_cm * cm, width)
            img.drawWidth, img.drawHeight = w, w * ratio
            parts = [img] + ([_p(b.pie, st["nota"])] if b.pie else [])
            story += [KeepTogether(parts), Spacer(1, 8)]
        elif isinstance(b, SaltoPagina):
            story.append(PageBreak())
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return path
