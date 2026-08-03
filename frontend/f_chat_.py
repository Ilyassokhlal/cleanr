import streamlit as st

import api

from pathlib import Path

# Agent panel: ask questions about the cleaned document.

TEXT_FORMATS = {"txt", "md", "csv", "tsv", "json"}
MAX_DOCUMENT_CHARS = 200_000

# A helper to render the chat history as a markdown transcript for download if the user wants it.
def _history_markdown(history: list[dict], filename: str) -> str:
    """Render the conversation as a readable transcript."""
    lines = [f"# Questions about {filename}", ""]
    for turn in history:
        speaker = "**You**" if turn["role"] == "user" else "**Cleanr**"
        lines.append(f"{speaker}: {turn['content']}")
        lines.append("")
    return "\n".join(lines)

def render() -> None:
    """Draw the chat panel beneath the results."""
    cleaned = st.session_state.get("cleaned_file")
    if cleaned is None:
        return

    document = cleaned.get("text", "")
    if not document:
        st.info("💬 No text available for this document.")
        return

    history = st.session_state.setdefault("chat_history", [])

    st.subheader("💬 Ask about this document")

    for turn in history:
        with st.chat_message(turn["role"]):
            st.write(turn["content"])

    if history:
        st.download_button(
            "📝 Download conversation",
            data=_history_markdown(history, cleaned["filename"]),
            file_name=f"{Path(cleaned['filename']).stem}_chat.md",
            mime="text/markdown",
        )

    question = st.chat_input("Ask a question")
    if question:
        history.append({"role": "user", "content": question})
        try:
            answer = api.ask(question, document, history[:-1])
        except Exception as e:
            st.error(f"Error: {e}")
            return
        history.append({"role": "assistant", "content": answer})
        st.rerun()
