"""
Tools for graph routing and document grading.
"""

from typing import Literal

from langchain_core.prompts import PromptTemplate

from src.config.settings import Config
from src.llms.openai import llm
from src.models.state import State
from src.models.verification_result import VerificationResult

config = Config()


def routing_tool(state: State) -> Literal["retriever", "general_llm", "web_search"]:
    """
    Route the graph to the appropriate node.
    """

    route = state.get("route", "web")

    if route == "index":
        return "retriever"

    elif route == "general":
        return "general_llm"

    return "web_search"


def doc_tool(state: State) -> Literal["rewrite", "generate"]:
    """
    Decide whether retrieved documents are relevant.
    """

    score = str(state.get("binary_score", "no")).strip().lower()

    print(f"[doc_tool] score = {score}")

    if score in ["yes", "true"]:
        return "generate"

    return "rewrite"


def verify_answer(state: State) -> Literal["__end__", "generate"]:
    """
    Verify that the generated answer is grounded in the retrieved context.
    """

    # Skip verification for general LLM answers
    if state.get("route") == "general":
        return "__end__"

    try:

        question = state.get("latest_query", "")

        messages = state.get("messages", [])

        if len(messages) < 2:
            return "__end__"

        # Retrieved documents / context
        context = messages[-2].content

        # Final generated answer
        final_answer = messages[-1].content

        verify_prompt = PromptTemplate(
            template=config.prompt("verify_prompt"),
            input_variables=[
                "question",
                "context",
                "final_answer",
            ],
        )

        verifier = llm.with_structured_output(
            VerificationResult
        )

        verify_chain = verify_prompt | verifier

        result = verify_chain.invoke(
            {
                "question": question,
                "context": context,
                "final_answer": final_answer,
            }
        )

        print(f"[verify] faithful = {result.faithful}")

        if result.faithful:
            return "__end__"

        print("[verify] Answer not faithful. Regenerating...")

        return "generate"

    except Exception as e:

        print(f"[verify] Error: {e}")

        # Prevent graph crash or infinite loop
        return "__end__"
