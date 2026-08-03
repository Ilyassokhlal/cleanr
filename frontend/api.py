import os
import json
import requests
import base64

# HTTP client for the Cleanr backend. The only place the frontend talks to it.

BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
TIMEOUT = 30
CLEAN_TIMEOUT = 180


# A few functions that wrap the backend API endpoints. These are called by the frontend step functions.
def get_options() -> dict:
    """Fetch the form definition served by GET /options."""
    response = requests.get(f"{BASE_URL}/options", timeout=TIMEOUT)
    response.raise_for_status()
    return response.json()



def clean(file_bytes: bytes, filename: str, selections: dict, output_format: str) -> dict:
    """Send the file and options to the backend. Returns bytes, text and media type."""
    files = {
        "file": (filename, file_bytes),
        "selections": (None, json.dumps(selections)),
        "output_format": (None, output_format),
    }
    response = requests.post(f"{BASE_URL}/clean", files=files, timeout=TIMEOUT)
    response.raise_for_status()
    payload = response.json()
    return {
        "bytes": base64.b64decode(payload["content_b64"]),
        "text": payload["text"],
        "media_type": payload["media_type"],
    }


ASK_TIMEOUT = 120

def ask(question: str, document: str, history: list[dict]) -> str:
    """Send a question about the cleaned document to the backend for an answer."""
    response = requests.post(
        f"{BASE_URL}/ask",
        json={"question": question, "document": document, "history": history},
        timeout=ASK_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()["answer"]