import re
from pathlib import Path

from charset_normalizer import from_bytes
import io
import docx
import pymupdf
import pytesseract
from PIL import Image

from concurrent.futures import ThreadPoolExecutor

# Constants for OCR and text extraction
OCR_MAX_PAGES = 150
OCR_WORKERS = 4


# Regular expression for detecting Arabic characters in text.
ARABIC = re.compile(r"[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]")
OCR_DPI = 300

# Pull plain text out of an uploaded document.

def _decode(data: bytes) -> str:
    """Decode raw bytes, falling back to detection if it isn't UTF-8."""
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        match = from_bytes(data).best()
        return str(match) if match else data.decode("utf-8", errors="replace")

def _strip_control_chars(text: str) -> str:
    """Drop glyph-ID leakage from PDFs with no usable ToUnicode map."""
    return "".join(ch for ch in text if ch.isprintable() or ch in "\n\t")

def _ocr_pdf(doc) -> str:
    """Read the pages as images — used when the text layer can't be trusted."""

    def _render(page) -> Image.Image:
        pix = page.get_pixmap(dpi=OCR_DPI)
        return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)

    def _read(image: Image.Image) -> str:
        return pytesseract.image_to_string(image, lang="ara+eng")

    pages = list(doc)[:OCR_MAX_PAGES]
    texts = []
    with ThreadPoolExecutor(max_workers=OCR_WORKERS) as pool:
        for start in range(0, len(pages), OCR_WORKERS):
            batch = [_render(page) for page in pages[start : start + OCR_WORKERS]]
            texts.extend(pool.map(_read, batch))
    return "\n".join(texts)

def extract(data: bytes, filename: str) -> str:
    """Return the document's text content."""
    suffix = Path(filename).suffix.lower()
    if suffix in (".txt", ".md"):
        return _decode(data)
    
    elif suffix == ".pdf":
        with pymupdf.open(stream=data, filetype="pdf") as doc:
            cleaned = _strip_control_chars("\n".join(page.get_text() for page in doc))
            if ARABIC.search(cleaned):
                try:
                    cleaned = _strip_control_chars(_ocr_pdf(doc))
                except pytesseract.TesseractNotFoundError:
                    pass
        if not cleaned.strip():
            raise ValueError("This PDF has no readable text layer.")
        return cleaned

    elif suffix in (".docx"):
        doc = docx.Document(io.BytesIO(data))
        return "\n".join(paragraph.text for paragraph in doc.paragraphs)
    
    raise ValueError(f"No extractor for {suffix}")