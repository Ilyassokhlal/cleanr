from pathlib import Path

from charset_normalizer import from_bytes
import io
import docx
import pymupdf

# Pull plain text out of an uploaded document.

def _decode(data: bytes) -> str:
    """Decode raw bytes, falling back to detection if it isn't UTF-8."""
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        match = from_bytes(data).best()
        return str(match) if match else data.decode("utf-8", errors="replace")


def extract(data: bytes, filename: str) -> str:
    """Return the document's text content."""
    suffix = Path(filename).suffix.lower()
    if suffix in (".txt", ".md"):
        return _decode(data)
    elif suffix == ".pdf":
        with pymupdf.open(stream=data, filetype="pdf") as doc:
            return "\n".join(page.get_text() for page in doc)
    elif suffix in (".docx"):
        doc = docx.Document(io.BytesIO(data))
        return "\n".join(paragraph.text for paragraph in doc.paragraphs)
    
    raise ValueError(f"No extractor for {suffix}")