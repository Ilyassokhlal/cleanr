import streamlit as st
from f_chat_ import render as render_chat

# Results screen: preview the cleaned file and download it.

TEXT_PREVIEW = {"txt", "md", "csv", "tsv", "json"}
PREVIEW_CHARS = 4000


def render() -> None:
    """Show the cleaned file, offer a download, and allow starting over."""
    cleaned = st.session_state.get("cleaned_file")
    if cleaned is None:
        st.session_state["step"] = "form"
        st.rerun()

    data, filename = cleaned["bytes"], cleaned["filename"]
    suffix = filename.rsplit(".", 1)[-1].lower()

    st.title("✅ Cleaned")
    st.caption(f"{filename} — {len(data):,} bytes")

    st.download_button("⬇️ Download", data=data, file_name=filename, mime=cleaned["media_type"])

    st.subheader("👀 Preview")
    preview = cleaned.get("text", "")
    st.code(preview[:PREVIEW_CHARS] if preview else "(no preview available)")
    if len(preview) > PREVIEW_CHARS:
        st.caption(f"Preview truncated to {PREVIEW_CHARS:,} characters.")

    if st.button("🔄 Clean another"):
        st.session_state.pop("cleaned_file", None)
        st.session_state["step"] = "form"
        st.rerun()

    render_chat()


