from __future__ import annotations

from typing import Any

from mcp.schemas.context import ToolContext
from mcp.schemas.results import ToolResponse
from mcp.tools.base import RegisteredTool


class MCPServer:
    """In-process MCP capability server with explicit tool registration."""

    def __init__(self, name: str) -> None:
        self.name = name
        self._tools: dict[str, RegisteredTool[Any]] = {}

    def register_tool(self, tool: RegisteredTool[Any]) -> None:
        if tool.name in self._tools:
            raise ValueError(f"MCP tool '{tool.name}' is already registered.")
        self._tools[tool.name] = tool

    def list_tools(self) -> list[dict[str, Any]]:
        return [self._tools[name].descriptor() for name in sorted(self._tools)]

    async def call(
        self,
        name: str,
        arguments: dict[str, Any],
        context: ToolContext,
    ) -> ToolResponse[Any]:
        tool = self._tools.get(name)
        if tool is None:
            return ToolResponse.failure("UNKNOWN_TOOL", f"MCP tool '{name}' is not registered.")
        return await tool.invoke(arguments, context)
