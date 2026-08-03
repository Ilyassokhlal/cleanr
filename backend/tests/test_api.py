import base64
import io
import pytest
import zipfile

import pandas as pd

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
            "text_casing": "title",
            "standardize_dates": "iso",
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


def _body(response) -> str:
    return base64.b64decode(response.json()["content_b64"]).decode()


@pytest.mark.parametrize("cell", ["=cmd|'/c calc'!A1", "+1+1", "-2+3", "@SUM(A1)"])
def test_formula_cells_are_neutralised(post_clean, cell):
    csv = f'name,note\nann,"{cell}"\n'.encode()
    out = _body(post_clean("x.csv", csv, {"trim_whitespace": True}, "csv"))
    assert f"'{cell}" in out


def test_ordinary_cells_are_not_prefixed(post_clean):
    out = _body(post_clean("x.csv", b"name,note\nann,hello\n", {"trim_whitespace": True}, "csv"))
    assert "'hello" not in out


def test_zip_bomb_is_rejected(post_clean):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("big.xml", b"0" * (600 * 1024 * 1024))
    response = post_clean("bomb.xlsx", buf.getvalue(), {"trim_whitespace": True}, "csv")
    assert response.status_code == 400


def test_corrupt_archive_is_rejected(post_clean):
    response = post_clean("fake.xlsx", b"not a zip", {"trim_whitespace": True}, "csv")
    assert response.status_code == 400


@pytest.mark.parametrize(
    "filename,blob,output_format",
    [
        ("x.pdf", b"%PDF-1.4 truncated garbage", "txt"),
        ("x.csv", b"\n\n", "csv"),
        ("x.json", b"{not json", "csv"),
    ],
)
def test_unreadable_files_return_422(post_clean, filename, blob, output_format):
    response = post_clean(filename, blob, {"trim_whitespace": True}, output_format)
    assert response.status_code == 422


@pytest.fixture
def workbook() -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf) as writer:
        pd.DataFrame({"name": ["  ANN  ", "  ANN  "]}).to_excel(writer, sheet_name="Sales", index=False)
        pd.DataFrame({"b": [3, 4]}).to_excel(writer, sheet_name="Costs", index=False)
    return buf.getvalue()


def test_every_sheet_survives_xlsx_output(post_clean, workbook):
    response = post_clean("book.xlsx", workbook, {"trim_whitespace": True}, "xlsx")
    out = base64.b64decode(response.json()["content_b64"])
    assert pd.ExcelFile(io.BytesIO(out)).sheet_names == ["Sales", "Costs"]


def test_every_sheet_is_cleaned(post_clean, workbook):
    response = post_clean(
        "book.xlsx", workbook, {"trim_whitespace": True, "drop_duplicate_rows": True}, "xlsx"
    )
    out = base64.b64decode(response.json()["content_b64"])
    assert pd.read_excel(io.BytesIO(out), sheet_name="Sales")["name"].tolist() == ["ANN"]


def test_multi_sheet_refuses_single_sheet_output(post_clean, workbook):
    response = post_clean("book.xlsx", workbook, {"trim_whitespace": True}, "csv")
    assert response.status_code == 422
    assert "XLSX" in response.json()["detail"]


def test_whole_numbers_stay_integers(post_clean):
    out = _body(post_clean("x.csv", b"name,qty\nann,1\nbob,\ncid,3\n", {"trim_whitespace": True}, "csv"))
    assert "1.0" not in out
    assert "ann,1" in out


def test_decimals_are_left_alone(post_clean):
    out = _body(post_clean("x.csv", b"name,price\nann,1.5\n", {"trim_whitespace": True}, "csv"))
    assert "1.5" in out


def test_unambiguous_day_resolves_the_column(post_clean):
    csv = b"d\n25/12/2024\n03/04/2025\n"
    out = _body(post_clean("x.csv", csv, {"standardize_dates": "iso"}, "csv"))
    assert "2025-04-03" in out


@pytest.mark.parametrize(
    "choice,expected", [("day first", "2025-04-03"), ("month first", "2025-03-04")]
)
def test_explicit_date_direction_is_honoured(post_clean, choice, expected):
    out = _body(
        post_clean(
            "x.csv",
            b"d\n03/04/2025\n",
            {"standardize_dates": "iso", "input_date_format": choice},
            "csv",
        )
    )
    assert expected in out


@pytest.fixture
def long_arabic_pdf() -> bytes:
    import pymupdf

    from backend.services.export import FONT_DIR
    from backend.services.extract import OCR_MAX_PAGES

    doc = pymupdf.open()
    for _ in range(OCR_MAX_PAGES + 1):
        page = doc.new_page()
        page.insert_text(
            (72, 72),
            "مرحبا بالعالم",
            fontfile=str(FONT_DIR / "NotoSansArabic-Regular.ttf"),
            fontname="ar",
            fontsize=14,
        )
    return doc.tobytes()


def test_long_arabic_pdf_is_refused(post_clean, long_arabic_pdf):
    response = post_clean("long.pdf", long_arabic_pdf, {"collapse_blank_lines": True}, "txt")
    assert response.status_code == 422
    assert "pages" in response.json()["detail"]


@pytest.mark.parametrize(
    "uploaded,expected",
    [
        ("../../etc/passwd.csv", "cleaned_passwd.csv"),
        ("report\nX.csv", "cleaned_report_X.csv"),
        ("😀.csv", "cleaned__.csv"),
    ],
)
def test_output_filename_is_sanitised(uploaded, expected):
    from backend.utils.naming import safe_output_name

    assert safe_output_name(uploaded, "csv") == expected