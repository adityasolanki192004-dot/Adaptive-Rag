import streamlit as st
import requests
from datetime import datetime

# Backend URL
BACKEND_URL = "https://adaptive-rag-backend-fyyu.onrender.com"

# --- Chat history state ---
if "chat_log" not in st.session_state:
    st.session_state.chat_log = []
if "show_history" not in st.session_state:
    st.session_state.show_history = False

# Page Title
title_col, history_col = st.columns([5, 1.3])
with title_col:
    st.title("Adaptive RAG Chat")
with history_col:
    st.write("")
    label = "Hide History" if st.session_state.show_history else "🕘 History"
    if st.button(label, use_container_width=True):
        st.session_state.show_history = not st.session_state.show_history

if st.session_state.show_history:
    if not st.session_state.chat_log:
        st.info("No questions asked yet.")
    else:
        if st.button("Clear History", key="clear_history"):
            st.session_state.chat_log = []
            st.rerun()
        for entry in reversed(st.session_state.chat_log):
            with st.container(border=True):
                st.caption(entry["time"])
                st.markdown(f"**Q:** {entry['question']}")
                st.markdown(f"**A:** {entry['answer']}")

uploaded_file = st.file_uploader(
    "Upload Document",
    type=["pdf", "txt"]
)

# User Input
question = st.text_input("Ask a question")

# Send Button
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

                # Show only the answer
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
