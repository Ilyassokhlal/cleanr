import anthropic
from fastapi import APIRouter, HTTPException

from backend.schemas.responses import AskRequest, AskResponse

# POST /ask — answer questions about a cleaned document.

router = APIRouter()
_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    """Build the client on first use, after .env has loaded."""
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client

MODEL = "claude-haiku-4-5"
MAX_DOCUMENT_CHARS = 200_000

SYSTEM_PROMPT = (
    "You answer questions about a document the user has just cleaned. "
    "Base every answer only on the document provided. If the answer isn't "
    "in it, say so plainly rather than guessing. Keep answers brief. "
    "If there's any ambiguity, ask the user to clarify rather than guessing or assuming. "
    "If the user asks you to summarize the document, under no circumstances should the summary be longer than the original document. "
)


@router.post("/ask", response_model=AskResponse)
def ask(request: AskRequest) -> AskResponse:
    """Answer a question about the supplied document."""
    document = request.document[:MAX_DOCUMENT_CHARS]

    messages = [
        *request.history,
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": document,
                    "cache_control": {"type": "ephemeral"},
                },
                {"type": "text", "text": request.question},
            ],
        },
    ]

    response = _get_client().messages.create(
        model=MODEL,
        max_tokens=16000,
        system=SYSTEM_PROMPT,
        messages=messages,
    )
    if response.stop_reason == "refusal":
        raise HTTPException(400, "Couldn't produce an answer for this document. Please try again.")
    return AskResponse(answer=response.content[0].text)