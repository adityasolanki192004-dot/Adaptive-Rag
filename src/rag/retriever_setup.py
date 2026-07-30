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


def retriever_chain(chunks: list[Document]) -> bool:
    """
    Store document chunks in the Qdrant vector store.

    Args:
        chunks: List of document chunks to store.

    Returns:
        Boolean indicating success of the operation.
    """
    try:
        QdrantVectorStore.from_documents(
            documents=chunks,
            embedding=embeddings,
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY,
            collection_name=settings.CODE_COLLECTION,
            force_recreate=True,
        )

        print(f"Stored {len(chunks)} chunks in Qdrant")
        return True
    except Exception as e:
        print(f"Error storing documents in Qdrant: {e}")
        return False


def get_retriever():
    """
    Returns the retriever tool that can search documents stored by retriever_chain().
    If no documents have been uploaded yet, creates a retriever with a dummy document.

    Returns:
        A LangChain retriever tool configured for the vector store.

    Raises:
        Exception: If vector store initialization fails.
    """
    try:
        try:
            # Normal case: collection already exists because documents were uploaded.
            vectorstore = QdrantVectorStore.from_existing_collection(
                embedding=embeddings,
                url=settings.QDRANT_URL,
                api_key=settings.QDRANT_API_KEY,
                collection_name=settings.CODE_COLLECTION,
            )
        except Exception:
            # No documents uploaded yet - create the collection with a
            # placeholder document so the graph can still run end to end.
            vectorstore = QdrantVectorStore.from_documents(
                documents=[Document(page_content="No documents uploaded yet.")],
                embedding=embeddings,
                url=settings.QDRANT_URL,
                api_key=settings.QDRANT_API_KEY,
                collection_name=settings.CODE_COLLECTION,
            )

        # k=3 caps how many chunks get pulled into a single prompt. Without
        # this, a large document can push a single request past the
        # account's tokens-per-minute limit (OpenAI 429 "Request too large").
        retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

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
