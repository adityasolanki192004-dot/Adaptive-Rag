"""
Retriever setup and vector store configuration.
"""

import os

from langchain_core.documents import Document
from langchain_core.tools import create_retriever_tool
from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore

from src.core.config import settings

embeddings = OpenAIEmbeddings()

# This ensures get_retriever() can access documents stored by retriever_chain()


def retriever_chain(chunks: list[Document]):
    """
    Initialize and store documents in FAISS vector database.

    Args:
        chunks: List of document chunks to store.

    Returns:
        Boolean indicating success of the operation.
    """


    try:
        # Commenting out Qdrant code for temporary FAISS usage
        # vectorstore = QdrantVectorStore.from_documents(
        #     documents=chunks,
        #     embedding=embeddings,
        #     url=settings.QDRANT_URL,
        #     api_key=settings.QDRANT_API_KEY,
        #     collection_name=settings.CODE_COLLECTION,
        # )
        QdrantVectorStore.from_documents(
    documents=chunks,
    embedding=embeddings,
    url=settings.QDRANT_URL,
    api_key=settings.QDRANT_API_KEY,
    collection_name=settings.CODE_COLLECTION,
)

print(f"Stored {len(chunks)} chunks in Qdrant")

return True
    except Exception as e:
        print(f"Error storing documents in FAISS: {e}")
        return False


def get_retriever():
    """
    Get a retriever tool connected to the FAISS vector store.

    Returns the retriever tool that can search documents stored by retriever_chain().
    If no documents have been uploaded yet, creates a retriever with a dummy document.

    Returns:
        A LangChain retriever tool configured for the vector store.

    Raises:
        Exception: If vector store initialization fails.
    """
  

    try:
        # Commenting out Qdrant code for temporary FAISS usage
        # vectorstore = QdrantVectorStore.from_documents(
        #     documents=[],
        #     embedding=embeddings,
        #     url=settings.QDRANT_URL,
        #     api_key=settings.QDRANT_API_KEY,
        #     collection_name=settings.CODE_COLLECTION,
        # )
        # retriever = vectorstore.as_retriever()

        # Use the global vectorstore if it exists (documents have been uploaded)
            retriever = _faiss_vectorstore.as_retriever()
            print("Using existing FAISS vectorstore with uploaded documents")
        else:
            # No documents uploaded yet, create dummy for initialization
            print("No documents uploaded yet, creating dummy vectorstore")
            
            retriever = _faiss_vectorstore.as_retriever()

        # Load document description
        if os.path.exists("description.txt"):
            with open("description.txt", "r", encoding="utf-8") as f:
                description = f.read()
        else:
            description = None

        retriever_tool = create_retriever_tool(
            retriever,
            "retriever_customer_uploaded_documents",
            f"Use this tool **only** to answer questions about: {description}\n"
            "Don't use this tool to answer anything else."
        )

        return retriever_tool

    except Exception as e:
        print(f"Error initializing retriever: {e}")
        raise Exception(e)
