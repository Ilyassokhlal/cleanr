import io

import docx
from fpdf import FPDF

from pathlib import Path

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
        document.add_paragraph(line)
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
        document.multi_cell(0, 6, line, new_x="LMARGIN", new_y="NEXT")
    return bytes(document.output())
