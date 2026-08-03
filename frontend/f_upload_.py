from pathlib import Path
import streamlit as st
import api
import re


# Making sure the filename we return is safe to use on any OS.
SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


# Upload screen: pick a file, confirm the output format, send it to be cleaned.

def render() -> None:
    """Draw the uploader, then hand the file to the backend."""
    kind = st.session_state.get("kind")
    output_format = st.session_state.get("output_format")
    if kind is None or output_format is None:
        st.session_state["step"] = "form"
        st.rerun()

    specs = api.get_options()
    accepted = [ext.lstrip(".") for ext, k in specs["extensions"].items() if k == kind]

    st.title("📤 Upload your file")
    st.caption(f"Accepts {', '.join('.' + e for e in accepted)} — you'll get back a .{output_format}")

    uploaded = st.file_uploader(
        "Choose a file",
        type=accepted,
        help="Arabic PDFs are read with OCR — slower, and numbers may be misread. Upload the DOCX version where you can.",
    )

    if uploaded is None:
        st.stop()

    if st.button("🧹 Clean it"):
        with st.spinner("Cleaning your file — Arabic PDFs take a little longer…"):
            result = api.clean(
                uploaded.getvalue(),
                uploaded.name,
                st.session_state["selections"],
                output_format,
            )
        stem = SAFE_NAME.sub("_", Path(uploaded.name).stem)[:80] or "document"
        result["filename"] = f"cleaned_{stem}.{output_format}"
        st.session_state["cleaned_file"] = result
        st.session_state.pop("chat_history", None)
        st.session_state["step"] = "results"
        st.rerun()