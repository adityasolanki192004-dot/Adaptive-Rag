"""
API routes for RAG operations.
"""

from fastapi import APIRouter, UploadFile, File, Header, HTTPException
from langchain_core.messages import HumanMessage, AIMessage

from src.core.logger import logger
from src.memory.chat_history_mongo import ChatHistory
from src.models.query_request import QueryRequest
from src.rag.document_upload import documents
from src.rag.graph_builder import builder

router = APIRouter()


@router.post("/rag/query")
async def rag_query(req: QueryRequest):
    """
    Process a RAG query and return the result.

    Args:
        req: The query request containing query text and session_id.

    Returns:
        The generated response from the RAG pipeline.
    """
    try:
        chat_history = ChatHistory.get_session_history(req.session_id)
        await chat_history.add_message(HumanMessage(content=req.query))

        # Fetch full history
        messages = await chat_history.get_messages()
        result = builder.invoke({
            "messages": messages
        })
        output_text = result["messages"][-1].content

        # Save assistant message
        await chat_history.add_message(AIMessage(content=output_text))

        return {"result": result["messages"][-1]}

    except Exception as e:
        logger.exception("rag_query failed")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process query: {e}"
        )


@router.post("/rag/documents/upload")
async def upload_file(
    file: UploadFile = File(...),
    description: str = Header(default="", alias="X-Description")
):
    """
    Upload a document for RAG processing.

    Args:
        file: The file to upload (PDF or TXT).
        description: Document description provided via header. Optional —
            defaults to an empty string if the client doesn't send one.

    Returns:
        Upload status.
    """
    try:
        status_upload = documents(description, file)
        return {"status": status_upload}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Document upload failed")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload document: {e}"
        )

