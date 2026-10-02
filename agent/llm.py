from __future__ import annotations

import json
import logging
import os
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from agent.policies import EMPTY_RETRIEVAL_MESSAGE
from agent.prompts.templates import (
    INTENT_ANALYSIS_PROMPT,
    RESPONSE_GENERATION_PROMPT,
    SYSTEM_PROMPT,
)
from agent.state.agent_state import Intent

logger = logging.getLogger(__name__)


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


class DefaultLLMClient:
    """Built-in deterministic agent client adhering to SDD prompts and policies."""

    async def analyze_intent(
        self, request: str, conversation_context: Sequence[Mapping[str, Any]]
    ) -> IntentDecision:
        text = request.strip().lower()

        # Operational tool patterns
        # 1. Create task
        create_task_pattern = re.search(
            r"^(?:please\s+)?(?:create|add|make|new|open)\s+(?:a\s+)?task(?:\s+(?:to|for|named|called|with title)?\s*(.*))?",
            text,
            re.IGNORECASE,
        )
        if create_task_pattern:
            remainder = create_task_pattern.group(1) or ""
            title = remainder.strip().strip('"\'') or "New Task"
            priority = None
            if "critical" in text:
                priority = "CRITICAL"
            elif "high" in text:
                priority = "HIGH"
            elif "low" in text:
                priority = "LOW"
            elif "medium" in text or "normal" in text:
                priority = "MEDIUM"

            return IntentDecision(
                intent="operational",
                selected_tool="create_task",
                tool_arguments={"title": title, "priority": priority},
            )

        # 2. List tasks
        if any(
            phrase in text
            for phrase in [
                "list task",
                "list all task",
                "show task",
                "show all task",
                "get task",
                "all tasks",
                "my tasks",
                "view tasks",
                "see tasks",
            ]
        ) or text in ("tasks", "task list"):
            return IntentDecision(
                intent="operational",
                selected_tool="list_tasks",
                tool_arguments={"limit": 50},
            )

        # 3. Create conversation
        if any(
            phrase in text
            for phrase in [
                "create conversation",
                "start conversation",
                "new conversation",
                "create chat",
                "start chat",
                "new chat",
            ]
        ):
            return IntentDecision(
                intent="operational",
                selected_tool="create_conversation",
                tool_arguments={"title": "New Conversation"},
            )

        # 4. Search documents via operational tool
        if text.startswith("search documents") or text.startswith("search docs"):
            query = re.sub(r"^search (?:documents|docs)\s*(?:for)?\s*", "", text, flags=re.IGNORECASE).strip()
            return IntentDecision(
                intent="operational",
                selected_tool="search_documents",
                tool_arguments={"query": query or request, "limit": 5},
            )

        # Standalone greetings and courtesies
        pure_greetings = {"hello", "hi", "hey", "good morning", "good afternoon", "good evening", "greetings", "yo", "sup"}
        if text in pure_greetings or text in {"who are you", "what can you do", "help", "thanks", "thank you"}:
            return IntentDecision(intent="general")

        # By default, route user questions and informational requests to the knowledge base RAG pipeline
        search_query = request
        # Strip conversational prefix if present (e.g. "can you tell me", "please search for")
        search_query = re.sub(
            r"^(?:can you\s+)?(?:please\s+)?(?:tell me\s+|show me\s+|find\s+|search\s+(?:for\s+)?|what is\s+|what are\s+|how do i\s+|how to\s+)?",
            "",
            request,
            flags=re.IGNORECASE,
        ).strip()
        return IntentDecision(
            intent="knowledge",
            tool_arguments={"query": search_query or request, "limit": 5},
        )

    async def generate_response(self, state: Mapping[str, Any]) -> str:
        intent = state.get("intent", "general")
        request = state.get("request", "").strip()
        req_lower = request.lower()

        if intent == "knowledge":
            sources = state.get("retrieved_sources") or []
            tool_result = state.get("tool_result") or {}
            if not sources and isinstance(tool_result, dict):
                data = tool_result.get("data")
                if isinstance(data, dict):
                    sources = data.get("sources") or []

            if not sources:
                return EMPTY_RETRIEVAL_MESSAGE

            # Extract concise, precise facts answering the question directly
            return self._extract_concise_answer(request, sources)

        if intent == "operational":
            tool_result = state.get("tool_result") or {}
            selected_tool = state.get("selected_tool")
            is_success = tool_result.get("success", False) if isinstance(tool_result, dict) else False
            data = tool_result.get("data") if isinstance(tool_result, dict) else None

            if not is_success:
                return "The requested operation could not be completed."

            if selected_tool == "create_task" and isinstance(data, dict):
                title = data.get("title", "Task")
                task_id = data.get("id", "")
                status = data.get("status", "TODO")
                priority = data.get("priority")
                p_text = f" with **{priority}** priority" if priority else ""
                return f"Task **\"{title}\"** has been created successfully{p_text} (ID: `{task_id}`, Status: `{status}`)."

            if selected_tool == "list_tasks":
                tasks_list = []
                if isinstance(data, dict) and "tasks" in data:
                    tasks_list = data["tasks"]
                elif isinstance(data, list):
                    tasks_list = data

                if not tasks_list:
                    return "No tasks were found in your organization."
                items = []
                for t in tasks_list[:10]:
                    items.append(f"- **{t.get('title')}** [{t.get('status')}] (ID: `{t.get('id')}`)")
                return f"Here are the tasks in your organization ({len(tasks_list)} total):\n\n" + "\n".join(items)

            if selected_tool == "create_conversation" and isinstance(data, dict):
                title = data.get("title", "New Conversation")
                conv_id = data.get("id", "")
                return f"Conversation **\"{title}\"** has been created (ID: `{conv_id}`)."

            return "The operation completed successfully."

        # General intent
        if any(g in req_lower for g in ["hello", "hi", "hey", "good morning", "good afternoon", "good evening", "greetings"]):
            return (
                "Hello! I am your AgentOps AI Assistant. I can help you search organizational knowledge, "
                "manage operational tasks, and execute agent workflows.\n\n"
                "How can I assist you today?"
            )

        if any(q in req_lower for q in ["who are you", "what are you", "what can you do", "help"]):
            return (
                "I am the AgentOps AI Assistant. I provide enterprise agentic operations including:\n\n"
                "1. **Knowledge Retrieval**: Search and answer questions grounded in your uploaded documents.\n"
                "2. **Task Operations**: Create, list, track, and update organization tasks.\n"
                "3. **Agent Traceability**: Inspect workflow runs, tool calls, and node execution traces.\n\n"
                "How can I help you right now?"
            )

        if any(t in req_lower for t in ["thanks", "thank you", "appreciate"]):
            return "You're welcome! Let me know if you need any further assistance."

        return (
            f"I have received your request: \"{request}\". I am ready to help you with organizational knowledge, "
            "task management, or agent operations. What would you like to do next?"
        )

    def _extract_concise_answer(self, request: str, sources: list[Mapping[str, Any]]) -> str:
        stop_words = {
            "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", "aren",
            "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but", "by",
            "can", "could", "did", "do", "does", "doing", "down", "during", "each", "few", "for", "from",
            "further", "had", "has", "have", "having", "he", "her", "here", "hers", "herself", "him", "himself",
            "his", "how", "i", "if", "in", "into", "is", "it", "its", "itself", "just", "me", "more", "most",
            "my", "myself", "no", "nor", "not", "now", "of", "off", "on", "once", "only", "or", "other", "our",
            "ours", "ourselves", "out", "over", "own", "same", "she", "should", "so", "some", "such", "than",
            "that", "the", "their", "theirs", "them", "themselves", "then", "there", "these", "they", "this",
            "those", "through", "to", "too", "under", "until", "up", "very", "was", "we", "were", "what", "when",
            "where", "which", "while", "who", "whom", "why", "will", "with", "you", "your", "yours", "yourself",
            "yourselves", "please", "tell", "show", "give"
        }
        q_tokens = [w for w in re.findall(r"[a-z0-9]+", request.lower()) if w not in stop_words]
        if not q_tokens:
            q_tokens = re.findall(r"[a-z0-9]+", request.lower())

        ignore_patterns = [
            r"^\s*\|", r"^\s*#+\s*", r"^\s*Effective date:", r"^\s*Version:", r"^\s*Applies to:",
            r"^\s*Owner:", r"^\s*---", r"^\s*Signature", r"^\s*>", r"^\s*Acknowledgment"
        ]

        matched_items: list[tuple[float, str, str, int]] = []
        seen_texts: set[str] = set()

        for src in sources[:4]:
            filename = src.get("filename", "Document")
            chunk_index = src.get("chunk_index", 0)
            content = src.get("content", "")

            raw_lines = [l.strip() for l in content.splitlines() if l.strip()]
            for line in raw_lines:
                clean = re.sub(r"^[0-9]+[\.\)]\s*", "", line).strip()
                clean = re.sub(r"^[-*]\s*", "", clean).strip()
                clean = clean.strip(">").strip()
                if line.startswith("#") or clean.startswith("#") or "##" in line or clean.startswith(('"', "'", ">")):
                    continue
                if len(clean) < 20 or clean.startswith(("`", "{", "}", "[", "]", "---")):
                    continue

                clean_lower = clean.lower()
                overlap_count = sum(1 for t in q_tokens if t in clean_lower)
                if overlap_count > 0:
                    score = (overlap_count / len(q_tokens))
                    if len(q_tokens) > 1 and " ".join(q_tokens) in clean_lower:
                        score += 0.6
                    # Prefer complete sentences over fragments
                    if clean.endswith((".", "!", "?", "\"", "’")):
                        score += 0.2
                    if clean not in seen_texts:
                        seen_texts.add(clean)
                        matched_items.append((score, clean, filename, chunk_index))

        matched_items.sort(key=lambda x: x[0], reverse=True)

        citations: list[str] = []
        for src in sources[:2]:
            fn = src.get("filename", "Document")
            ci = src.get("chunk_index", 0)
            citations.append(f"`{fn}` (chunk {ci + 1})")

        distinct_citations = list(dict.fromkeys(citations))

        if matched_items:
            max_score = matched_items[0][0]
            filtered = [item for item in matched_items if item[0] >= 0.6 * max_score]
            top_answers = [f"- {item[1]}" for item in filtered[:3]]
            answer_body = "\n".join(top_answers)
            source_line = f"\n\n*Sources:* {', '.join(distinct_citations)}"
            return f"{answer_body}{source_line}"

        top_chunk = sources[0].get("content", "").strip()
        first_para = "\n".join([l.strip() for l in top_chunk.splitlines() if l.strip() and not l.startswith("#")][:2])
        source_line = f"\n\n*Sources:* {', '.join(distinct_citations)}"
        return f"{first_para}{source_line}"


class ProviderLLMClient:
    """LLM client connecting to an OpenAI-compatible API endpoint with automatic fallback."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4o-mini",
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.fallback = DefaultLLMClient()

    async def analyze_intent(
        self, request: str, conversation_context: Sequence[Mapping[str, Any]]
    ) -> IntentDecision:
        import httpx

        prompt = (
            f"{SYSTEM_PROMPT}\n\n{INTENT_ANALYSIS_PROMPT}\n\n"
            f"User Request: {request}\n\n"
            "Return valid JSON ONLY in this format:\n"
            "{\n"
            '  "intent": "knowledge" | "operational" | "general",\n'
            '  "selected_tool": "<tool_name_or_null>",\n'
            '  "tool_arguments": { ... }\n'
            "}"
        )

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for msg in conversation_context[-5:]:
            messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})
        messages.append({"role": "user", "content": prompt})

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": messages,
                        "temperature": 0.1,
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    content = data["choices"][0]["message"]["content"]
                    # Extract JSON
                    json_match = re.search(r"\{.*\}", content, re.DOTALL)
                    if json_match:
                        parsed = json.loads(json_match.group(0))
                        intent = parsed.get("intent", "general")
                        if intent not in ("knowledge", "operational", "general"):
                            intent = "general"
                        return IntentDecision(
                            intent=intent,
                            selected_tool=parsed.get("selected_tool"),
                            tool_arguments=parsed.get("tool_arguments") or {},
                        )
        except Exception as exc:
            logger.warning("Provider LLM intent analysis failed, using default client: %s", exc)

        return await self.fallback.analyze_intent(request, conversation_context)

    async def generate_response(self, state: Mapping[str, Any]) -> str:
        import httpx

        intent = state.get("intent", "general")
        request = state.get("request", "")
        sources = state.get("retrieved_sources") or []
        tool_result = state.get("tool_result")

        prompt = (
            f"{SYSTEM_PROMPT}\n\n{RESPONSE_GENERATION_PROMPT}\n\n"
            f"User Request: {request}\n"
            f"Intent: {intent}\n"
            f"Retrieved Sources: {json.dumps(sources)}\n"
            f"Tool Result: {json.dumps(tool_result)}\n\n"
            "Provide the final synthesized user-facing response:"
        )

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": prompt},
                        ],
                        "temperature": 0.3,
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return data["choices"][0]["message"]["content"].strip()
        except Exception as exc:
            logger.warning("Provider LLM response generation failed, using default client: %s", exc)

        return await self.fallback.generate_response(state)


RuleBasedLLMClient = DefaultLLMClient


def get_default_llm_client() -> LLMClient:
    """Factory to retrieve the configured LLM client or fallback default."""
    api_key = (
        os.getenv("OPENAI_API_KEY")
        or os.getenv("GROQ_API_KEY")
        or os.getenv("LLM_API_KEY")
        or os.getenv("GEMINI_API_KEY")
    )
    base_url = os.getenv("LLM_BASE_URL") or os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1"
    model = os.getenv("LLM_MODEL") or "gpt-4o-mini"

    if api_key:
        return ProviderLLMClient(api_key=api_key, base_url=base_url, model=model)

    return DefaultLLMClient()
