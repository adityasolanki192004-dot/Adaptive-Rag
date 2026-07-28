import streamlit as st
import requests

BACKEND_URL = "https://adaptive-rag-frontend-we4k.onrender.com"

st.title("Adaptive RAG Chat")

question = st.text_input("Ask a question")

if st.button("Send"):
    if question:
        response = requests.post(
            f"{BACKEND_URL}/query",   # change this if your API endpoint is different
            json={"query": question}
        )

        if response.status_code == 200:
            st.write(response.json())
        else:
            st.error(response.text)
