from pydantic import BaseModel, field_validator
from backend.config import OptionType, TABULAR_OPTIONS, TEXT_OPTIONS, OUTPUT_FORMATS


# Request and response shapes for the cleaning options.

# A selection is either a checkbox state or a dropdown value.
OptionValue = bool | str


class OptionSpec(BaseModel):
    """One cleaning option, as served by GET /options."""

    key: str
    label: str
    type: OptionType
    default: OptionValue
    choices: list[str] | None = None


class OptionsResponse(BaseModel):
    """Full payload for GET /options — what the frontend builds the form from."""

    tabular: list[OptionSpec]
    text: list[OptionSpec]
    output_formats: dict[str, list[str]]
    extensions: dict[str, str]


class CleaningRequest(BaseModel):
    """The user's form selections, posted alongside the file."""

    selections: dict[str, OptionValue]
    output_format: str

    # validator: reject any key in `selections` that isn't defined in config

    @field_validator("selections")
    @classmethod
    def _known_keys(cls, v: dict[str, OptionValue]) -> dict[str, OptionValue]:
        valid = {opt["key"] for opt in TABULAR_OPTIONS + TEXT_OPTIONS}
        for key in v:
            if key not in valid:
                raise ValueError(f"Invalid option key: {key}")
        return v
    # validator: reject an output_format not listed in OUTPUT_FORMATS
    @field_validator("output_format")
    @classmethod
    def _valid_output_format(cls, v: str) -> str:
        if v not in [fmt for fmts in OUTPUT_FORMATS.values() for fmt in fmts]:
            raise ValueError(f"Invalid output format: {v}")
        return v
