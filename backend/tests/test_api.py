import base64

import pytest

from backend.services import detect

# End-to-end tests for the Cleanr API.

@pytest.mark.parametrize(
    "filename,expected",
    [
        ("sales.csv", "tabular"),
        ("book.XLSX", "tabular"),
        ("report.PDF", "text"),
        ("notes.md", "text"),
    ],
)
def test_detect_kind(filename, expected):
    assert detect.detect_kind(filename) == expected


def test_detect_kind_rejects_unknown_extension():
    with pytest.raises(detect.UnsupportedFileError):
        detect.detect_kind("archive.rtf")


def test_check_output_format_rejects_mismatch():
    with pytest.raises(ValueError):
        detect.check_output_format("tabular", "pdf")


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_options_lists_both_pipelines(client):
    body = client.get("/options").json()
    assert set(body) == {"tabular", "text", "output_formats", "extensions"}
    assert body["output_formats"]["tabular"] == ["csv", "xlsx", "json"]


@pytest.mark.parametrize(
    "output_format,magic",
    [("csv", b"first"), ("xlsx", b"PK\x03\x04"), ("json", b"[")],
)
def test_clean_tabular_output_formats(post_clean, messy_csv, output_format, magic):
    response = post_clean(
        "sales.csv", messy_csv, {"normalize_column_names": True}, output_format
    )
    assert response.status_code == 200
    assert base64.b64decode(response.json()["content_b64"]).startswith(magic)


def test_clean_applies_every_selected_option(post_clean, messy_csv):
    response = post_clean(
        "sales.csv",
        messy_csv,
        {
            "trim_whitespace": True,
            "drop_duplicate_rows": True,
            "normalize_column_names": True,
            "text_casing": "Title",
            "standardize_dates": "ISO",
        },
        "csv",
    )
    out = base64.b64decode(response.json()["content_b64"]).decode()
    assert "first_name" in out
    assert out.count("Ann") == 1
    assert "2025-03-04" in out


def test_clean_text_pipeline(post_clean, messy_text):
    response = post_clean(
        "doc.txt",
        messy_text,
        {
            "collapse_blank_lines": True,
            "fix_encoding_artifacts": True,
            "rejoin_hyphenated_breaks": True,
            "strip_headers_footers": True,
        },
        "txt",
    )
    out = base64.b64decode(response.json()["content_b64"]).decode()
    assert "Header" not in out
    assert "It’s" in out
    assert "sentence" in out


def test_clean_returns_text_for_binary_output(post_clean, messy_text):
    body = post_clean("doc.txt", messy_text, {"collapse_blank_lines": True}, "pdf").json()
    assert base64.b64decode(body["content_b64"]).startswith(b"%PDF-")
    assert body["text"]


@pytest.mark.parametrize(
    "filename,selections,output_format,blob",
    [
        ("x.csv", "{bad json", "csv", b"a,b\n1,2\n"),
        ("x.csv", '{"nope": true}', "csv", b"a,b\n1,2\n"),
        ("x.rtf", '{"trim_whitespace": true}', "csv", b"a,b\n1,2\n"),
        ("x.csv", '{"trim_whitespace": true}', "pdf", b"a,b\n1,2\n"),
        ("x.csv", '{"trim_whitespace": true}', "csv", b""),
    ],
)
def test_clean_rejects_bad_input(client, filename, selections, output_format, blob):
    response = client.post(
        "/clean",
        files={
            "file": (filename, blob),
            "selections": (None, selections),
            "output_format": (None, output_format),
        },
    )
    assert response.status_code == 400


def test_ask_returns_answer(client, stub_anthropic):
    stub_anthropic(text="42 rows.")
    response = client.post(
        "/ask", json={"question": "How many rows?", "document": "a,b\n1,2\n"}
    )
    assert response.status_code == 200
    assert response.json()["answer"] == "42 rows."


def test_ask_handles_refusal(client, stub_anthropic):
    stub_anthropic(stop_reason="refusal")
    response = client.post("/ask", json={"question": "q", "document": "d"})
    assert response.status_code == 400


def test_ask_rejects_empty_question(client):
    response = client.post("/ask", json={"question": "", "document": "d"})
    assert response.status_code == 422