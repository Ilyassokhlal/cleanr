import re

from collections import Counter

from backend.schemas.options import CleaningRequest
from backend.services import extract, export

# Text cleaning pipeline: bytes in, cleaned bytes out.

def _collapse_blank_lines(content: str) -> str:
    """Reduce runs of two or more blank lines to a single blank line."""
    return re.sub(r"\n{3,}", "\n\n", content)

tranformations = {
    "â€™": "\u2019", "â€˜": "\u2018", "â€œ": "\u201c", "â€\u009d": "\u201d",
    "â€”": "\u2014", "â€“": "\u2013", "â€¦": "\u2026", "Â ": " ",
}

def _fix_encoding_artifacts(content: str) -> str:
    """Fix common encoding artifacts in the text."""
    for bad , good in tranformations.items():
        content = content.replace(bad, good)
    return content
    
def _rejoin_hyphenated_breaks(content: str) -> str:
    """Rejoin words that have been split across lines with hyphens."""
    return re.sub(r"(\w+)-\n(\w+)", r"\1\2", content)

def _strip_headers_footers(content: str, min_repeats: int = 3) -> str:
    """Drop short lines that repeat often enough to be running heads."""
    lines = content.split("\n")
    counts = Counter(line.strip() for line in lines if line.strip())
    repeated = {t for t, n in counts.items() if n >= min_repeats and len(t) < 80}
    return "\n".join(line for line in lines if line.strip() not in repeated)

def _write(content: str, output_format: str) -> bytes:
    """Serialize cleaned text into the requested format."""
    if output_format in ("txt", "md"):
        return content.encode("utf-8")
    if output_format == "docx":
        return export.write_docx(content)
    if output_format == "pdf":
        return export.write_pdf(content)
    raise ValueError(f"No writer for {output_format}")


def clean(data: bytes, filename: str, request: CleaningRequest) -> tuple[bytes, str]:
    """Apply the selected options and return the cleaned document."""
    content = extract.extract(data, filename)
    opts = request.selections

    if opts.get("collapse_blank_lines"):
        content = _collapse_blank_lines(content)
    if opts.get("fix_encoding_artifacts"):
        content = _fix_encoding_artifacts(content)
    if opts.get("rejoin_hyphenated_breaks"):
        content = _rejoin_hyphenated_breaks(content)
    if opts.get("strip_headers_footers"):
        content = _strip_headers_footers(content)
    
    return _write(content, request.output_format), content