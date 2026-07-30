import streamlit as st
import requests
from datetime import datetime

# Backend URL
BACKEND_URL = "https://adaptive-rag-backend-fyyu.onrender.com"

st.set_page_config(page_title="Adaptive RAG Chat", layout="centered")

# --- Chat history state ---
if "chat_log" not in st.session_state:
    st.session_state.chat_log = []
if "show_history" not in st.session_state:
    st.session_state.show_history = False

# ----------------------------------------------------------------------
# ANIMATIONS
# ----------------------------------------------------------------------
st.markdown(
    """
    <style>
    /* ---- Page load fade/slide ---- */
    .main .block-container {
        animation: pageFadeIn 0.6s ease-out;
        max-width: 900px;
    }
    @keyframes pageFadeIn {
        from { opacity: 0; transform: translateY(12px); }
        to   { opacity: 1; transform: translateY(0); }
    }

    /* ---- Title ---- */
    h1 {
        animation: titleSlideIn 0.6s ease-out;
    }
    @keyframes titleSlideIn {
        from { opacity: 0; transform: translateX(-16px); }
        to   { opacity: 1; transform: translateX(0); }
    }

    /* ---- All buttons: hover / press / glow ---- */
    div.stButton > button {
        border-radius: 10px;
        border: 1px solid rgba(255,255,255,0.15);
        background-color: #1a1c23;
        color: #f2f2f2;
        font-weight: 600;
        transition: transform 0.18s ease, background-color 0.18s ease,
                    border-color 0.18s ease, box-shadow 0.25s ease;
        animation: buttonPopIn 0.4s ease-out;
    }
    @keyframes buttonPopIn {
        from { opacity: 0; transform: scale(0.9); }
        to   { opacity: 1; transform: scale(1); }
    }
    div.stButton > button:hover {
        background-color: #23262f;
        border-color: rgba(120,150,255,0.55);
        transform: translateY(-3px);
        box-shadow: 0 8px 20px rgba(80,110,255,0.25);
    }
    div.stButton > button:active {
        transform: translateY(0px) scale(0.96);
        box-shadow: 0 2px 6px rgba(0,0,0,0.4);
    }

    /* spin the clock emoji in the History button on hover */
    div.stButton > button:hover p {
        animation: wiggle 0.5s ease-in-out;
    }
    @keyframes wiggle {
        0%   { transform: rotate(0deg); }
        25%  { transform: rotate(-8deg); }
        50%  { transform: rotate(0deg); }
        75%  { transform: rotate(8deg); }
        100% { transform: rotate(0deg); }
    }

    /* ---- History panel open/close ---- */
    .history-panel {
        animation: slideDown 0.4s cubic-bezier(0.22, 1, 0.36, 1);
        transform-origin: top;
        overflow: hidden;
        margin-top: 0.75rem;
        margin-bottom: 1rem;
        border-radius: 14px;
        background-color: #14161c;
        border: 1px solid rgba(255,255,255,0.08);
        padding: 0.9rem 1rem;
    }
    @keyframes slideDown {
        from { opacity: 0; max-height: 0; transform: scaleY(0.85) translateY(-14px); }
        to   { opacity: 1; max-height: 900px; transform: scaleY(1) translateY(0); }
    }

    /* ---- Individual history cards, staggered ---- */
    .history-item {
        border-radius: 10px;
        background-color: #1c1e26;
        padding: 0.6rem 0.8rem;
        margin-bottom: 0.55rem;
        animation: itemFadeIn 0.45s ease-out both;
        transition: background-color 0.2s ease, transform 0.2s ease;
    }
    .history-item:hover {
        background-color: #24262f;
        transform: translateX(4px);
    }
    .history-item:nth-child(1) { animation-delay: 0.03s; }
    .history-item:nth-child(2) { animation-delay: 0.09s; }
    .history-item:nth-child(3) { animation-delay: 0.15s; }
    .history-item:nth-child(4) { animation-delay: 0.21s; }
    .history-item:nth-child(5) { animation-delay: 0.27s; }
    .history-item:nth-child(n+6) { animation-delay: 0.32s; }
    @keyframes itemFadeIn {
        from { opacity: 0; transform: translateX(-10px); }
        to   { opacity: 1; transform: translateX(0); }
    }

    .history-q { color: #f2f2f2; font-weight: 600; margin-bottom: 2px; }
    .history-a { color: #b7bac2; font-size: 0.92rem; }
    .history-time { color: #6b6f7b; font-size: 0.75rem; margin-bottom: 4px; }

    /* ---- Empty state pulse ---- */
    div[data-testid="stAlert"] {
        animation: emptyPulse 2.4s ease-in-out infinite, itemFadeIn 0.4s ease-out;
    }
    @keyframes emptyPulse {
        0%, 100% { opacity: 1; }
        50%      { opacity: 0.7; }
    }

    /* ---- Text input + file uploader: focus/hover glow ---- */
    div[data-testid="stTextInput"] input {
        transition: border-color 0.25s ease, box-shadow 0.25s ease;
        border-radius: 10px !important;
    }
    div[data-testid="stTextInput"] input:focus {
        border-color: rgba(120,150,255,0.7) !important;
        box-shadow: 0 0 0 3px rgba(80,110,255,0.18);
    }

    section[data-testid="stFileUploaderDropzone"] {
        transition: border-color 0.25s ease, box-shadow 0.25s ease, transform 0.2s ease;
        border-radius: 12px !important;
    }
    section[data-testid="stFileUploaderDropzone"]:hover {
        border-color: rgba(120,150,255,0.6) !important;
        box-shadow: 0 6px 18px rgba(80,110,255,0.15);
        transform: translateY(-2px);
    }

    /* ---- Success / error / info messages slide in ---- */
    div[data-testid="stNotification"], div[data-testid="stAlert"] {
        animation: itemFadeIn 0.4s ease-out;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ----------------------------------------------------------------------
# Header: title + History toggle
# ----------------------------------------------------------------------
title_col, history_col = st.columns([5, 1.3])
with title_col:
    st.title("Adaptive RAG Chat")
with history_col:
    st.write("")
    label = "Hide History" if st.session_state.show_history else "🕘 History"
    if st.button(label, use_container_width=True):
        st.session_state.show_history = not st.session_state.show_history

# ----------------------------------------------------------------------
# Animated history panel
# ----------------------------------------------------------------------
if st.session_state.show_history:
    st.markdown('<div class="history-panel">', unsafe_allow_html=True)

    if not st.session_state.chat_log:
        st.info("No questions asked yet.")
    else:
        if st.button("Clear History", key="clear_history"):
            st.session_state.chat_log = []
            st.rerun()

        for entry in reversed(st.session_state.chat_log):
            st.markdown(
                f"""
                <div class="history-item">
                    <div class="history-time">{entry['time']}</div>
                    <div class="history-q">Q: {entry['question']}</div>
                    <div class="history-a">A: {entry['answer']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("</div>", unsafe_allow_html=True)

# ----------------------------------------------------------------------
# Upload Document
# ----------------------------------------------------------------------
uploaded_file = st.file_uploader(
    "Upload Document",
    type=["pdf", "txt"]
)

if uploaded_file:
    files = {
        "file": (
            uploaded_file.name,
            uploaded_file.getvalue(),
            uploaded_file.type
        )
    }
    headers = {
        "X-Description": uploaded_file.name
    }
    upload_response = requests.post(
        f"{BACKEND_URL}/rag/documents/upload",
        files=files,
        headers=headers
    )
    if upload_response.status_code == 200:
        st.success("Document Uploaded Successfully!")
    else:
        st.error(upload_response.text)

# ----------------------------------------------------------------------
# Ask a question
# ----------------------------------------------------------------------
question = st.text_input("Ask a question")

if st.button("Send"):
    if question.strip():
        try:
            response = requests.post(
                f"{BACKEND_URL}/rag/query",
                json={
                    "query": question,
                    "session_id": "demo-session"
                },
                timeout=60
            )

            if response.status_code == 200:
                data = response.json()

                answer_text = "No answer found."
                if "result" in data:
                    result = data["result"]
                    if isinstance(result, dict):
                        answer_text = result.get("content", "No answer found.")
                    else:
                        answer_text = str(result)
                elif "content" in data:
                    answer_text = data["content"]
                else:
                    st.error("Answer not found in response.")
                    st.json(data)

                st.markdown(answer_text)

                st.session_state.chat_log.append({
                    "question": question,
                    "answer": answer_text,
                    "time": datetime.now().strftime("%H:%M:%S"),
                })

            else:
                st.error(f"Error: {response.status_code}")
                st.text(response.text)

        except Exception as e:
            st.error(f"Request failed: {e}")
    else:
        st.warning("Please enter a question.")
