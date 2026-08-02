import streamlit as st

import api

# Front page: the cleaning options form.

def render() -> None:
    """Draw the options form. On submit, store selections and advance."""
    specs = api.get_options()

    st.title("🧹 Cleanr")
    st.caption("Pick what you're cleaning, choose your options, then upload.")

    kind = st.radio(
        "What are you cleaning?",
        options=["tabular", "text"],
        format_func=lambda k: "📊 Spreadsheets & data" if k == "tabular" else "📄 Documents & text",
        horizontal=True,
    )

    with st.form("cleaning_options"):
        selections: dict[str, bool | str] = {}

        for spec in specs[kind]:
            if spec["type"] == "bool":
                selections[spec["key"]] = st.checkbox(spec["label"], value=spec["default"])

            elif spec["type"] == "choice":
                default_index = spec["choices"].index(spec["default"])
                selections[spec["key"]] = st.selectbox(spec["label"], spec["choices"], index=default_index)

            elif spec["type"] == "text":
                selections[spec["key"]] = st.text_input(spec["label"], value=spec["default"])

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