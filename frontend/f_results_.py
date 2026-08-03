import streamlit as st
from f_chat_ import render as render_chat
import html
import io
import pandas as pd

# Results screen: preview the cleaned file and download it.

PREVIEW_CHARS = 4000

# A helper to render a preview block for the cleaned text, with proper escaping and directionality.
def _preview_block(text: str) -> str:
    """Escaped, direction-aware preview. Never interpolate unescaped text here."""
    return (
        '<div dir="auto" style="white-space:pre-wrap; font-family:monospace; '
        'background:#141821; padding:1rem; border-radius:0.5rem; '
        f'max-height:24rem; overflow:auto">{html.escape(text)}</div>'
    )

def render() -> None:
    """Show the cleaned file, offer a download, and allow starting over."""
    cleaned = st.session_state.get("cleaned_file")
    if cleaned is None:
        st.session_state["step"] = "form"
        st.rerun()

    data, filename = cleaned["bytes"], cleaned["filename"]

    st.title("✅ Cleaned")
    st.caption(f"{filename} — {len(data):,} bytes")


    main, side = st.columns([2, 1], gap="large")

    with main:
        st.subheader("👀 Preview")
        preview = cleaned.get("text", "")
        if st.session_state.get("kind") == "tabular" and not preview.startswith("--- "):
            try:
                st.dataframe(pd.read_csv(io.StringIO(preview)), width="stretch")
            except Exception:
                st.markdown(_preview_block(preview[:PREVIEW_CHARS]), unsafe_allow_html=True)
        else:
            st.markdown(_preview_block(preview[:PREVIEW_CHARS]), unsafe_allow_html=True)
        if len(preview) > PREVIEW_CHARS:
            st.caption(f"Preview truncated to {PREVIEW_CHARS:,} characters.")

    with side:
        st.subheader("📦 Your file")
        with st.container(border=True):
            st.download_button(
                "⬇️ Download",
                data=data,
                file_name=filename,
                mime=cleaned["media_type"],
                width="stretch",
            )
            if st.button("⬅️ Back to upload", width="stretch"):
                st.session_state["step"] = "upload"
                st.rerun()
            if st.button("🔄 Start over", width="stretch"):
                for key in ("cleaned_file", "chat_history", "selections", "kind", "output_format"):
                    st.session_state.pop(key, None)
                st.session_state["step"] = "form"
                st.rerun()

    render_chat()


