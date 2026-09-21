"""MCP server factories and registry."""

from mcp.servers.platform import create_platform_server
from mcp.servers.knowledge import create_knowledge_server
from mcp.servers.registry import MCPServer

__all__ = ["MCPServer", "create_knowledge_server", "create_platform_server"]
