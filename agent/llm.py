from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from agent.state.agent_state import Intent


class LLMError(RuntimeError):
    """Base error for model-provider failures."""


class LLMUnavailableError(LLMError):
    pass


@dataclass(frozen=True)
class IntentDecision:
    intent: Intent
    selected_tool: str | None = None
    tool_arguments: dict[str, Any] | None = None


class LLMClient(Protocol):
    async def analyze_intent(
        self, request: str, conversation_context: Sequence[Mapping[str, Any]]
    ) -> IntentDecision: ...

    async def generate_response(self, state: Mapping[str, Any]) -> str: ...


class UnconfiguredLLMClient:
    """Explicit default until an SDD-approved provider is configured."""

    async def analyze_intent(
        self, request: str, conversation_context: Sequence[Mapping[str, Any]]
    ) -> IntentDecision:
        raise LLMUnavailableError("No LLM provider is configured.")

    async def generate_response(self, state: Mapping[str, Any]) -> str:
        raise LLMUnavailableError("No LLM provider is configured.")
