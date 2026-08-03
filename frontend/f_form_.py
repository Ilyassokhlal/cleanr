import streamlit as st

import api

# Front page: the cleaning options form.

def render() -> None:
    """Draw the options form. On submit, store selections and advance."""
    specs = api.get_options()

    st.title("🧹 Cleanr")
    st.caption("Upload a messy spreadsheet or document. Pick what to fix, get it back clean.")

    with st.expander("What can it do?"):
        st.markdown(
            "- **Spreadsheets** — CSV, Excel, TSV, JSON. Trims whitespace, drops duplicate "
            "rows, normalises column names, standardises dates, fixes casing and missing values.\n"
            "- **Documents** — PDF, Word, text, Markdown. Collapses blank lines, repairs "
            "encoding damage, rejoins hyphenated words, strips repeated headers.\n"
            "- Ask questions about whatever you uploaded once it's cleaned.\n"
            "- Nothing is stored — files are processed and returned, not kept."
        )

    kind = st.radio(
        "What are you cleaning?",
        options=["tabular", "text"],
        format_func=lambda k: "📊 Spreadsheets & data" if k == "tabular" else "📄 Documents & text",
        horizontal=True,
    )

    with st.form("cleaning_options"):
        selections: dict[str, bool | str] = {}

        ordered = sorted(specs[kind], key=lambda s: s["type"] != "bool")
        for start in range(0, len(ordered), 2):
            for column, spec in zip(st.columns(2), ordered[start : start + 2]):
                if spec["type"] == "bool":
                    selections[spec["key"]] = column.checkbox(spec["label"], value=spec["default"])

                elif spec["type"] == "choice":
                    default_index = spec["choices"].index(spec["default"])
                    selections[spec["key"]] = column.selectbox(spec["label"], spec["choices"], index=default_index)

                elif spec["type"] == "text":
                    selections[spec["key"]] = column.text_input(spec["label"], value=spec["default"])

                else:
                    raise ValueError(f"Unknown option type: {spec['type']}")

        output_format = st.selectbox("💾 Output format", specs["output_formats"][kind])
        submitted = st.form_submit_button("✨ Continue")

    if submitted:
        st.session_state["kind"] = kind
        st.session_state["selections"] = selections
        st.session_state["output_format"] = output_format
        st.session_state["step"] = "upload"
        st.rerun()