import io

import docx
from fpdf import FPDF

from pathlib import Path

import re

from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

# right to left unicode ranges for Arabic
RTL = re.compile(r"[\u0590-\u08FF\uFB1D-\uFDFF\uFE70-\uFEFF]")

def _set_rtl(paragraph) -> None:
    """Mark a paragraph right-to-left so Word lays it out from the right margin."""
    pPr = paragraph._p.get_or_add_pPr()
    bidi = OxmlElement("w:bidi")
    bidi.set(qn("w:val"), "1")
    pPr.append(bidi)
    paragraph.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    for run in paragraph.runs:
        rPr = run._r.get_or_add_rPr()
        rtl = OxmlElement("w:rtl")
        rtl.set(qn("w:val"), "1")
        rPr.append(rtl)


# Write cleaned text out as a document.

FONT_DIR = Path(__file__).parent.parent / "assets"
FONTS = {
    "Noto": "NotoSans-Regular.ttf",
    "NotoArabic": "NotoSansArabic-Regular.ttf",
    "NotoSC": "NotoSansSC-Regular.ttf",
    "NotoKR": "NotoSansKR-Regular.ttf",
}



def write_docx(content: str) -> bytes:
    """Wrap cleaned text in a .docx, one paragraph per line."""
    document = docx.Document()
    for line in content.split("\n"):
        paragraph = document.add_paragraph(line)
        if RTL.search(line):
            _set_rtl(paragraph)
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def write_pdf(content: str) -> bytes:
    """Wrap cleaned text in a .pdf, with fallback fonts for non-Latin scripts."""
    document = FPDF()
    for family, filename in FONTS.items():
        document.add_font(family, "", str(FONT_DIR / filename))
    document.set_font("Noto", size=11)
    document.set_fallback_fonts(["NotoArabic", "NotoSC", "NotoKR"])
    document.set_text_shaping(True)
    document.add_page()
    for line in content.split("\n"):
        align = "R" if RTL.search(line) else "L"
        document.multi_cell(0, 6, line, new_x="LMARGIN", new_y="NEXT", align=align)
    return bytes(document.output())
