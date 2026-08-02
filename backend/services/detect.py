from pathlib import Path

from backend.config import OUTPUT_FORMATS

# Work out which pipeline an upload belongs to.

class UnsupportedFileError(ValueError):
    """The upload is a type neither pipeline handles."""


# File extension -> pipeline. Anything not listed is rejected.
EXTENSIONS = {
    ".csv": "tabular",
    ".tsv": "tabular",
    ".xlsx": "tabular",
    ".xls": "tabular",
    ".json": "tabular",
    ".pdf": "text",
    ".docx": "text",
    ".txt": "text",
    ".md": "text",
}


def detect_kind(filename: str) -> str:
    """Return "tabular" or "text" for an uploaded filename."""
    suffix = Path(filename).suffix.lower()
    if suffix in EXTENSIONS:
        return EXTENSIONS[suffix]
    raise UnsupportedFileError(f"Unsupported file type: {suffix}")


def check_output_format(kind: str, output_format: str) -> None:
    """Reject a format the detected pipeline can't produce."""
    if output_format not in OUTPUT_FORMATS.get(kind, []):
        raise ValueError(f"Unsupported output format '{output_format}' for kind '{kind}'")