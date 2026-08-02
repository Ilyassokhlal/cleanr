import io
from pathlib import Path

import pandas as pd
from backend.schemas.options import CleaningRequest

# Tabular cleaning pipeline: bytes in, cleaned bytes out.

def _read(data: bytes, filename: str) -> pd.DataFrame:
    """Parse the upload into a DataFrame based on its extension."""
    buffer = io.BytesIO(data)
    suffix = Path(filename).suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(buffer)
    elif suffix == ".tsv":
        return pd.read_csv(buffer, sep="\t")
    elif suffix in (".xlsx", ".xls"):
        return pd.read_excel(buffer)
    elif suffix == ".json":
        return pd.read_json(buffer)
    else:
        raise ValueError(f"No reader for {suffix}")

def _write(df: pd.DataFrame, output_format: str) -> bytes:
    """Serialize the cleaned frame into the requested format."""
    if output_format == "csv":
        return df.to_csv(index=False).encode("utf-8")
    elif output_format == "xlsx":
        buffer = io.BytesIO()
        df.to_excel(buffer, index=False)
        return buffer.getvalue()
    elif output_format == "json":
        return df.to_json(orient="records", indent=2).encode("utf-8")
    else:
        raise ValueError(f"No writer for {output_format}")

def _trim_whitespace(df: pd.DataFrame) -> pd.DataFrame:
    """Strip leading and trailing whitespace from every text cell."""
    for col in df.columns:
        if pd.api.types.is_string_dtype(df[col]):
            df[col] = df[col].str.strip()
    return df

def clean(data: bytes, filename: str, request: CleaningRequest) -> tuple[bytes, str]:
    """Apply the selected options and return the cleaned file."""
    df = _read(data, filename)
    opts = request.selections

    if opts.get("trim_whitespace"):
        df = _trim_whitespace(df)
    if opts.get("drop_duplicate_rows"):
        df = df.drop_duplicates()
    if opts.get("normalize_column_names"):
        df.columns = (
            df.columns.str.lower()
            .str.strip()
            .str.replace(r"\s+", "_", regex=True)
        )
    strip_currency = opts.get("strip_currency_commas")
    if strip_currency:
        for col in df.columns:
            if pd.api.types.is_string_dtype(df[col]):
                df[col] = (
                    df[col]
                    .str.replace(r"[\$,]", "", regex=True)
                    .str.replace(r"\s+", " ", regex=True)
                    .str.strip()
                )
    date_format = opts.get("standardize_dates")
    if date_format and date_format != "Keep":
        patterns = {"ISO": "%Y-%m-%d", "US": "%m/%d/%Y", "EU": "%d/%m/%Y"}
        for col in df.columns:
            if not pd.api.types.is_string_dtype(df[col]):
                continue
            parsed = pd.to_datetime(df[col], errors="coerce")
            if parsed.notna().all():
                df[col] = parsed.dt.strftime(patterns[date_format])
    text_casing = opts.get("text_casing")
    if text_casing and text_casing != "none":
        for col in df.columns:
            if pd.api.types.is_string_dtype(df[col]):
                if text_casing == "lower":
                    df[col] = df[col].str.lower()
                elif text_casing == "UPPER":
                    df[col] = df[col].str.upper()
                elif text_casing == "Title":
                    df[col] = df[col].str.title()
    missing = opts.get("missing_values")
    if missing and missing != "leave":
        if missing == "drop row":
            df = df.dropna()
        elif missing == "fill blank":
            for col in df.columns:
                if pd.api.types.is_string_dtype(df[col]):
                    df[col] = df[col].fillna("")

    return _write(df, request.output_format), df.to_csv(index=False)
