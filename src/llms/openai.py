"""
OpenAI LLM initialization and configuration.
"""

import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "")

llm = ChatOpenAI(
    model="gpt-4o",
    max_tokens=800,   # cap response size - keeps total request+response well under a low-tier TPM limit
    max_retries=2,    # let the client retry short transient rate-limit/network errors on its own
)
