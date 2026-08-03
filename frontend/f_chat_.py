import streamlit as st

import api

# Agent panel: ask questions about the cleaned document.

TEXT_FORMATS = {"txt", "md", "csv", "tsv", "json"}
MAX_DOCUMENT_CHARS = 200_000


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
