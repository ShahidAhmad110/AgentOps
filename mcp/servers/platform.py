from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.document_service import DocumentService
from mcp.servers.registry import MCPServer
from mcp.tools.conversations import ConversationTools
from mcp.tools.knowledge import KnowledgeTools
from mcp.tools.tasks import TaskTools


def create_platform_server(session: AsyncSession) -> MCPServer:
    server = MCPServer(name="agentops-platform")
    tool_groups = (
        KnowledgeTools(DocumentService(session)).registered_tools(),
        TaskTools(session).registered_tools(),
        ConversationTools(session).registered_tools(),
    )
    for tools in tool_groups:
        for tool in tools:
            server.register_tool(tool)
    return server