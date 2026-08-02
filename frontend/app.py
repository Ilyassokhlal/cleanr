import streamlit as st

import f_form_
import f_upload_, f_results_

import requests

# Cleanr — entry point and step routing.

st.set_page_config(page_title="Cleanr", page_icon="🧹", layout="centered")

if "step" not in st.session_state:
    st.session_state["step"] = "form"

step = st.session_state["step"]

# Step routing.
try:
    if step == "form":
        f_form_.render()
    elif step == "upload":
        f_upload_.render()
    elif step == "results":
        f_results_.render()
    else:
        st.error(f"⚠️ Unknown step: {step}")
except requests.exceptions.ConnectionError:
    st.error("⚠️ Can't reach the backend — is it running?")
    st.code("uvicorn backend.main:app --reload")
except requests.exceptions.HTTPError as exc:
    detail = exc.response.text
    try:
        detail = exc.response.json()["detail"]
    except Exception:
        pass
    st.error(f"⚠️ {detail}")