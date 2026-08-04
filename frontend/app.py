# Cleanr — clean messy spreadsheets and documents
# Copyright (C) 2026 <Ilias OKHLAL>
#
# Licensed under the GNU Affero General Public License v3.0.
# See the LICENSE file for the full terms.

import streamlit as st

import f_form_
import f_upload_, f_results_

import subprocess
import sys
import time

import requests

import api

# Cleanr — entry point and step routing.

st.set_page_config(page_title="Cleanr", page_icon="🧹", layout="wide")

st.markdown(
    """
    <style>
    .stApp {
        background:
            radial-gradient(900px 600px at 12% -10%, rgba(61, 220, 151, 0.10), transparent 60%),
            radial-gradient(800px 520px at 88% 0%, rgba(99, 102, 241, 0.10), transparent 55%),
            #090B10;
        background-attachment: fixed;
    }
    .stApp::before {
        content: "";
        position: fixed;
        inset: 0;
        pointer-events: none;
        z-index: 0;
        opacity: 0.09;
        background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='140' height='140'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.55' numOctaves='4'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
    }
    </style>
    """,
    unsafe_allow_html=True,
)

@st.cache_resource
def _start_backend():
    """Start uvicorn once per container. No-op if something is already serving."""
    try:
        requests.get(f"{api.BASE_URL}/health", timeout=1)
        return None
    except requests.exceptions.RequestException:
        pass

    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8000"]
    )
    for _ in range(60):
        try:
            requests.get(f"{api.BASE_URL}/health", timeout=1)
            break
        except requests.exceptions.RequestException:
            time.sleep(0.5)
    return process


_start_backend()

if "step" not in st.session_state:
    st.session_state["step"] = "form"

step = st.session_state["step"]

STEPS = [("form", "Options"), ("upload", "Upload"), ("results", "Result")]


def _progress(current: str) -> None:
    """Show which of the three stages we're on."""
    position = [key for key, _ in STEPS].index(current)
    st.caption(
        "  ·  ".join(
            f"**{i + 1}. {label}**" if i == position else f"{i + 1}. {label}"
            for i, (_, label) in enumerate(STEPS)
        )
    )


if step in [key for key, _ in STEPS]:
    _progress(step)

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