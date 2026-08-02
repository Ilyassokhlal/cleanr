import json
import types

import pytest
from fastapi.testclient import TestClient

from backend.main import app

import backend.routers.ask as ask_module

# Shared fixtures for the Cleanr test suite.

@pytest.fixture
def client() -> TestClient:
    """Returns error responses instead of raising, so status codes are assertable."""
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def messy_csv() -> bytes:
    """Whitespace, a duplicate row, and US-format dates."""
    return b"First Name,joined\n  ANN  ,03/04/2025\n  ANN  ,03/04/2025\n bob ,12/25/2024\n"


@pytest.fixture
def messy_text() -> bytes:
    """A repeated header, mojibake, and a hyphenated line break."""
    return "Header\nItâ€™s a sen-\ntence.\n\n\n\nHeader\nbody\nHeader\n".encode("utf-8")


@pytest.fixture
def post_clean(client):
    """Post a file plus options to /clean the way the frontend does."""

    def _post(filename: str, blob: bytes, selections: dict, output_format: str):
        return client.post(
            "/clean",
            files={
                "file": (filename, blob),
                "selections": (None, json.dumps(selections)),
                "output_format": (None, output_format),
            },
        )

    return _post


@pytest.fixture
def stub_anthropic(monkeypatch):
    """Replace the Anthropic client with a fake returning a canned response."""

    def _stub(text: str = "stubbed answer", stop_reason: str = "end_turn") -> None:
        content = [] if stop_reason == "refusal" else [types.SimpleNamespace(text=text)]
        fake = types.SimpleNamespace(
            messages=types.SimpleNamespace(
                create=lambda **kwargs: types.SimpleNamespace(
                    stop_reason=stop_reason, content=content
                )
            )
        )
        monkeypatch.setattr(ask_module, "_client", fake)

    return _stub