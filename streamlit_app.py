import streamlit as st
import requests

# Backend URL
BACKEND_URL = "https://adaptive-rag-backend-fyyu.onrender.com"

# Page Title
st.title("Adaptive RAG Chat")

uploaded_file = st.file_uploader(
    "Upload Document",
    type=["pdf", "txt"]
)
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
                if "result" in data:
                    result = data["result"]

                    # If result is a dictionary
                    if isinstance(result, dict):
                        st.markdown(result.get("content", "No answer found."))

                    # If result is already a string
                    else:
                        st.markdown(result)

                # Fallback
                elif "content" in data:
                    st.markdown(data["content"])

                else:
                    st.error("Answer not found in response.")
                    st.json(data)

            else:
                st.error(f"Error: {response.status_code}")
                st.text(response.text)

        except Exception as e:
            st.error(f"Request failed: {e}")
    else:
        st.warning("Please enter a question.")
