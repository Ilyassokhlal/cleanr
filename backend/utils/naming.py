import re
from pathlib import Path

# Turn an uploaded filename into something safe to hand back.

SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


def safe_output_name(filename: str, output_format: str) -> str:
    """Build a download name that can't escape a directory or break a header."""
    stem = SAFE_NAME.sub("_", Path(filename).stem)[:80] or "document"
    return f"cleaned_{stem}.{output_format}"