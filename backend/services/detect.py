from pathlib import Path

from backend.config import OUTPUT_FORMATS

import io
import zipfile

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

ZIP_EXTENSIONS = {".xlsx", ".docx"}
MAX_UNCOMPRESSED_BYTES = 500 * 1024 * 1024

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


def check_archive_size(data: bytes, filename: str) -> None:
    """Reject zip-based uploads that expand disproportionately when opened."""
    if Path(filename).suffix.lower() not in ZIP_EXTENSIONS:
        return
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            total = sum(info.file_size for info in archive.infolist())
    except zipfile.BadZipFile as exc:
        raise ValueError("This file is corrupt or not a real Office document.") from exc
    if total > MAX_UNCOMPRESSED_BYTES:
        raise ValueError("This file expands to an unreasonable size when opened.")