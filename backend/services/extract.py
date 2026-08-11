import re
from pathlib import Path
import zipfile

from charset_normalizer import from_bytes
import io
import docx
import pymupdf
import pytesseract
from PIL import Image

from concurrent.futures import ThreadPoolExecutor

from backend.errors import ProcessingFailed

# Constants for OCR and text extraction
OCR_MAX_PAGES = 150
OCR_WORKERS = 4


# Regular expression for detecting Arabic characters in text.
ARABIC = re.compile(r"[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]")
OCR_DPI = 300

# Set of characters considered as digits, including Arabic-Indic and Eastern Arabic-Indic digits.
DIGITS = set("0123456789") | {chr(c) for c in range(0x0660, 0x066A)} | {chr(c) for c in range(0x06F0, 0x06FA)}
NUM_SEPS = set(".,/-:\u066B\u066C")

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

def _text_layer_numbers(page) -> list[dict]:
    """Digit runs from the text layer, read left-to-right so RTL reversal is undone."""
    numbers = []
    for block in page.get_text("rawdict")["blocks"]:
        if block.get("type") != 0:
            continue
        for line in block["lines"]:

            chars = [ch for span in line["spans"] for ch in span["chars"]]

            chars.sort(key=lambda ch: ch["bbox"][0])

            # Scan left-to-right, collecting runs of digits and separators. When a run ends, trim trailing separators and add the run to the list.
            run = []
            for ch in chars + [None]:
                if ch and ch["c"] in DIGITS:
                    run.append(ch)
                elif ch and ch["c"] in NUM_SEPS and run:
                    run.append(ch)
                elif run:
                    while run and run[-1]["c"] in NUM_SEPS:
                        run.pop()
                    if run:
                        numbers.append({
                            "text": "".join(ch["c"] for ch in run),
                            "bbox": (
                                run[0]["bbox"][0],
                                min(ch["bbox"][1] for ch in run),
                                run[-1]["bbox"][2],
                                max(ch["bbox"][3] for ch in run),
                            ),
                        })
                    run = []
    return numbers

def _tokens_to_text(data: dict) -> str:
    """Rebuild page text from Tesseract's token table, preserving its order."""
    lines = []
    current = None
    for i, word in enumerate(data["text"]):
        if not word.strip():
            continue
        key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        if key != current:
            lines.append([])
            current = key
        lines[-1].append(word)
    return "\n".join(" ".join(line) for line in lines)

def _overlap(a: tuple, b: tuple) -> float:
    """How much of box a is covered by box b, 0.0 to 1.0. Boxes are (x0, y0, x1, y1)."""
    inter_width = min(a[2], b[2]) - max(a[0], b[0])
    inter_height = min(a[3], b[3]) - max(a[1], b[1])
    if inter_width <= 0 or inter_height <= 0:
        return 0.0
    inter_area = inter_width * inter_height
    a_area = (a[2] - a[0]) * (a[3] - a[1])
    if a_area == 0:
        return 0.0
    return inter_area / a_area

def _looks_numeric(token: str) -> bool:
    """Did OCR think this token was a number? Only such tokens are safe to replace."""
    chars = [c for c in token.strip() if c not in "\u200e\u200f"]
    if not chars:
        return False
    num_count = sum(1 for c in chars if c in DIGITS or c in NUM_SEPS)
    return num_count / len(chars) >= 0.8

def _merge_numbers(page, data: dict) -> dict:
    """Numbers from the text layer, positions from OCR. Returns a corrected token table."""
    scale = OCR_DPI / 72.0
    claims = {}

    # Collect indices of tokens that are not empty or whitespace. This is used to filter out irrelevant tokens when matching numbers from the text layer to OCR tokens.
    collected_indices = [i for i, text in enumerate(data["text"]) if text.strip()]
    for number in _text_layer_numbers(page):
        scaled_bbox = tuple(coord * scale for coord in number["bbox"])
        best_index = None
        best_overlap = 0.0
        for i in collected_indices:
            token_box = (
                data["left"][i],
                data["top"][i],
                data["left"][i] + data["width"][i],
                data["top"][i] + data["height"][i],
            )
            overlap_value = _overlap(scaled_bbox, token_box)
            if overlap_value > best_overlap:
                best_overlap = overlap_value
                best_index = i
        if best_index is not None and best_overlap >= 0.1 and _looks_numeric(data["text"][best_index]) and data["text"][best_index].strip() != number["text"]:
            claims.setdefault(best_index, []).append(number["text"])
    
    # If any index has multiple claims, delete it from the claims dictionary. This ensures that only indices with a single claim are kept for replacement.
    for index, claim_list in list(claims.items()):
        if len(claim_list) > 1:
            del claims[index]

    # Builds a new list of text tokens, replacing the original token with the claimed number if it exists in the claims dictionary. If an index has a claim, use that claim; otherwise, keep the original token.
    new_text = [
        claims[i][0] if i in claims else data["text"][i]
        for i in range(len(data["text"]))
    ]

    # Return a new dictionary with the original data and the updated text tokens. This allows for the replacement of OCR tokens with more accurate numbers from the text layer.
    return dict(data, text=new_text)

def _ocr_pdf(doc) -> str:
    """Read the pages as images — used when the text layer can't be trusted."""

    def _render(page) -> Image.Image:
        pix = page.get_pixmap(dpi=OCR_DPI)
        return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)

    def _read(image: Image.Image) -> dict:
        return pytesseract.image_to_data(image, lang="ara+eng", output_type=pytesseract.Output.DICT)

    if doc.page_count > OCR_MAX_PAGES:
        raise ProcessingFailed(
            f"This PDF has {doc.page_count} pages and needs OCR, which is capped "
            f"at {OCR_MAX_PAGES}. Split it, or upload the DOCX version instead."
        )
    pages = list(doc)
    
    texts = []
    with ThreadPoolExecutor(max_workers=OCR_WORKERS) as pool:
        for start in range(0, len(pages), OCR_WORKERS):
            chunk = pages[start : start + OCR_WORKERS]
            batch = [_render(page) for page in chunk]
            for page, data in zip(chunk, pool.map(_read, batch)):
                texts.append(_merge_numbers(page, data))
    return "\n".join(_tokens_to_text(data) for data in texts)

def extract(data: bytes, filename: str) -> str:
    """Return the document's text content."""
    suffix = Path(filename).suffix.lower()
    if suffix in (".txt", ".md"):
        return _decode(data)
    
    elif suffix == ".pdf":
        try:
            with pymupdf.open(stream=data, filetype="pdf") as doc:
                cleaned = _strip_control_chars("\n".join(page.get_text() for page in doc))
                if ARABIC.search(cleaned):
                    try:
                        cleaned = _strip_control_chars(_ocr_pdf(doc))
                    except pytesseract.TesseractNotFoundError:
                        pass
        except pymupdf.FileDataError as exc:
            raise ProcessingFailed("This PDF couldn't be read — it may be corrupt.") from exc
        if not cleaned.strip():
            raise ProcessingFailed("This PDF has no readable text layer.")
        return cleaned

    elif suffix == ".docx":
        try:
            doc = docx.Document(io.BytesIO(data))
        except zipfile.BadZipFile as exc:
            raise ProcessingFailed("This Word document couldn't be read — it may be corrupt.") from exc
        return "\n".join(paragraph.text for paragraph in doc.paragraphs)
    
    raise ValueError(f"No extractor for {suffix}")