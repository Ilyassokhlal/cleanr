import io
from pathlib import Path

import pandas as pd
from backend.schemas.options import CleaningRequest
from backend.errors import ProcessingFailed

# Tabular cleaning pipeline: bytes in, cleaned bytes out.

def _read(data: bytes, filename: str) -> dict[str, pd.DataFrame]:
    """Parse the upload into one or more named frames."""
    buffer = io.BytesIO(data)
    suffix = Path(filename).suffix.lower()
    try:
        if suffix == ".csv":
            return {"Sheet1": pd.read_csv(buffer)}
        elif suffix == ".tsv":
            return {"Sheet1": pd.read_csv(buffer, sep="\t")}
        elif suffix in (".xlsx", ".xls"):
            return pd.read_excel(buffer, sheet_name=None)
        elif suffix == ".json":
            return {"Sheet1": pd.read_json(buffer)}
    except (pd.errors.ParserError, pd.errors.EmptyDataError, ValueError) as exc:
        raise ProcessingFailed(f"This file couldn't be read as data: {exc}") from exc
    raise ValueError(f"No reader for {suffix}")

def _write(frames: dict[str, pd.DataFrame], output_format: str) -> bytes:
    """Serialize the cleaned frames into the requested format."""
    if output_format == "xlsx":
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer) as writer:
            for name, df in frames.items():
                df.to_excel(writer, sheet_name=name[:31], index=False)
        return buffer.getvalue()

    if len(frames) > 1:
        raise ProcessingFailed(
            f"This workbook has {len(frames)} sheets. Choose XLSX output to keep them all."
        )

    df = next(iter(frames.values()))
    if output_format == "csv":
        return df.to_csv(index=False).encode("utf-8")
    elif output_format == "json":
        return df.to_json(orient="records", indent=2).encode("utf-8")
    raise ValueError(f"No writer for {output_format}")


def _trim_whitespace(df: pd.DataFrame) -> pd.DataFrame:
    """Strip leading and trailing whitespace from every text cell."""
    for col in df.columns:
        if pd.api.types.is_string_dtype(df[col]):
            df[col] = df[col].str.strip()
    return df

FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")

def _neutralise_formulas(df: pd.DataFrame) -> pd.DataFrame:
    """Stop spreadsheet apps executing cell text as a formula."""
    for col in df.columns:
        if pd.api.types.is_string_dtype(df[col]):
            mask = df[col].str.startswith(FORMULA_PREFIXES, na=False)
            df.loc[mask, col] = "'" + df.loc[mask, col]
    return df

def clean(data: bytes, filename: str, request: CleaningRequest) -> tuple[bytes, str]:
    """Apply the selected options to every sheet and return the cleaned file."""
    frames = _read(data, filename)
    opts = request.selections
    cleaned = {name: _apply(df, opts) for name, df in frames.items()}
    if len(cleaned) == 1:
        text = next(iter(cleaned.values())).to_csv(index=False)
    else:
        text = "\n\n".join(
            f"--- {name} ---\n{df.to_csv(index=False)}" for name, df in cleaned.items()
        )
    return _write(cleaned, request.output_format), text

def _is_dayfirst(series: pd.Series, choice: str) -> bool:
    """Decide whether a date column is written day-first."""
    if choice == "day first":
        return True
    if choice == "month first":
        return False
    firsts = series.str.extract(r"^(\d{1,2})[/-]", expand=False).dropna()
    return bool((firsts.astype(int) > 12).any())

def _apply(df: pd.DataFrame, opts: dict) -> pd.DataFrame:
    """Run the selected transforms over one frame."""
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
    if opts.get("strip_currency_commas"):
        for col in df.columns:
            if pd.api.types.is_string_dtype(df[col]):
                df[col] = (
                    df[col]
                    .str.replace(r"[\$,]", "", regex=True)
                    .str.replace(r"\s+", " ", regex=True)
                    .str.strip()
                )

    date_format = opts.get("standardize_dates")
    if date_format and date_format != "keep":
        patterns = {"iso": "%Y-%m-%d", "us": "%m/%d/%Y", "eu": "%d/%m/%Y"}
        for col in df.columns:
            if not pd.api.types.is_string_dtype(df[col]):
                continue
            parsed = pd.to_datetime(
                df[col],
                errors="coerce",
                dayfirst=_is_dayfirst(df[col], opts.get("input_date_format", "auto")),
            )
            if parsed.notna().all():
                df[col] = parsed.dt.strftime(patterns[date_format])

    text_casing = opts.get("text_casing")
    if text_casing and text_casing != "none":
        for col in df.columns:
            if pd.api.types.is_string_dtype(df[col]):
                if text_casing == "lower":
                    df[col] = df[col].str.lower()
                elif text_casing == "upper":
                    df[col] = df[col].str.upper()
                elif text_casing == "title":
                    df[col] = df[col].str.title()

    missing = opts.get("missing_values")
    if missing and missing != "leave":
        if missing == "drop row":
            df = df.dropna()
        elif missing == "fill blank":
            for col in df.columns:
                if pd.api.types.is_string_dtype(df[col]):
                    df[col] = df[col].fillna("")

    for col in df.columns:
        if pd.api.types.is_float_dtype(df[col]):
            values = df[col].dropna()
            if not values.empty and (values % 1 == 0).all():
                df[col] = df[col].astype("Int64")

    return _neutralise_formulas(df)

    return _neutralise_formulas(df)