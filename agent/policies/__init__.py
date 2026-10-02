"""Agent execution and safety policies."""

from typing import Final

ALLOWED_INTENTS: Final[set[str]] = {"knowledge", "operational", "general"}
DEFAULT_RETRIEVAL_LIMIT: Final[int] = 5
MAX_RETRIEVAL_LIMIT: Final[int] = 20
MAX_AGENT_STEPS: Final[int] = 10
EMPTY_RETRIEVAL_MESSAGE: Final[str] = (
    "No relevant documents were found in the knowledge base to answer your question."
)
SANITIZED_FAILURE_MESSAGE: Final[str] = "The agent could not complete the request."
