from pydantic import BaseModel, Field

# Request and response shapes for the AI agent.

class AskRequest(BaseModel):
    """A question about the cleaned document."""

    question: str = Field(min_length=1, max_length=2000)
    document: str = Field(min_length=1)
    history: list[dict[str, str]] = Field(default_factory=list)


class AskResponse(BaseModel):
    """The agent's answer."""

    answer: str

class CleanResponse(BaseModel):
    """A cleaned document, plus a text view of it for the agent."""

    filename: str
    media_type: str
    content_b64: str
    text: str = ""