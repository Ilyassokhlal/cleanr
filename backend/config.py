from enum import Enum

# Cleaning option definitions. Single source of truth for the form.


class OptionType(str, Enum):
    """Type of cleaning option."""
    BOOL = "bool"
    CHOICE = "choice"
    TEXT = "text"


# One entry per cleaning option.
# key / label / type / default / choices (choices only for CHOICE)
TABULAR_OPTIONS = [
    {"key": "trim_whitespace", "label": "✂️ Trim whitespace", "type": OptionType.BOOL, "default": True},
    {"key": "drop_duplicate_rows", "label": "🧬 Drop duplicate rows", "type": OptionType.BOOL, "default": True},
    {"key": "normalize_column_names", "label": "📝 Normalize column names", "type": OptionType.BOOL, "default": True},
    {"key": "standardize_dates", "label": "📅 Standardize dates", "type": OptionType.CHOICE, "choices": ["ISO", "US", "EU", "Keep"], "default": "Keep"},
    {"key": "text_casing", "label": "🔠 Text casing", "type": OptionType.CHOICE, "choices": ["none", "lower", "Title", "UPPER"], "default": "none"},
    {"key": "missing_values", "label": "🕳️ Missing values", "type": OptionType.CHOICE, "choices": ["leave", "drop row", "fill blank"], "default": "leave"},
    {"key": "strip_currency_commas", "label": "💲 Strip currency + commas", "type": OptionType.BOOL, "default": False},
]

TEXT_OPTIONS = [
    {"key": "collapse_blank_lines", "label": "↕️ Collapse blank lines", "type": OptionType.BOOL, "default": True},
    {"key": "fix_encoding_artifacts", "label": "🩹 Fix encoding artifacts", "type": OptionType.BOOL, "default": True},
    {"key": "rejoin_hyphenated_breaks", "label": "🔗 Rejoin hyphenated breaks", "type": OptionType.BOOL, "default": True},
    {"key": "strip_headers_footers", "label": "📑 Strip headers / footers", "type": OptionType.BOOL, "default": False},
]

OUTPUT_FORMATS = {
    "tabular": ["csv", "xlsx", "json"],
    "text":    ["txt", "md", "docx", "pdf"]
}