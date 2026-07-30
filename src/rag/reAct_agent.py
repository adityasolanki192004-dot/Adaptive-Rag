"""
ReAct agent setup for document retrieval and question answering.
"""

import os

from langchain.agents import create_react_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate

from src.config.settings import Config
from src.llms.openai import llm
from src.rag.retriever_setup import get_retriever

config = Config()

# Create ReAct agent prompt (doesn't need any live connections, safe at import time)
prompt = ChatPromptTemplate.from_messages([
    ("system", config.prompt("system_prompt")),
    ("human", "{input}"),
    ("ai", "{agent_scratchpad}")
])

_agent_executor = None


def reset_agent_executor() -> None:
    """
    Clear the cached agent executor.

    Call this after a new document is uploaded so the next query rebuilds
    the retriever tool (and its description) instead of reusing a stale
    one from an earlier upload.
    """
    global _agent_executor
    _agent_executor = None


def get_agent_executor() -> AgentExecutor:
    """
    Lazily build the ReAct agent executor on first use.

    This avoids connecting to the vector store (Qdrant) at module import
    time, which would crash the whole app on startup if the vector store
    isn't reachable yet. The connection is only attempted when a query
    actually needs the retriever, and any failure only affects that
    request instead of preventing the server from starting.

    Returns:
        A cached AgentExecutor instance.
    """
    global _agent_executor

    if _agent_executor is None:
        tools = [get_retriever()]

        react_agent = create_react_agent(llm, tools, prompt)
        _agent_executor = AgentExecutor(
            agent=react_agent,
            tools=tools,
            handle_parsing_errors=True,
            max_iterations=2,
            verbose=True,
            return_intermediate_steps=True
        )

    return _agent_executor
