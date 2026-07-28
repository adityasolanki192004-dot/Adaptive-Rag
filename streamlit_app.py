import streamlit as st
import requests

BACKEND_URL = "https://adaptive-rag-backend-fyyu.onrender.com"

st.title("Adaptive RAG Chat")

question = st.text_input("Ask a question")

if st.button("Send"):
    if question:
        response = requests.post(
    f"{BACKEND_URL}/rag/query",
    json={
        "query": question,
        "session_id": "demo-session"
    }
)
     if response.status_code == 200:
            st.write(response.json())
        else:
            st.error(response.text)
