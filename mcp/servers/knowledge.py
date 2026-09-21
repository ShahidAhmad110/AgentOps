from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.document_service import DocumentService
from mcp.servers.registry import MCPServer
from mcp.tools.knowledge import KnowledgeTools


def create_knowledge_server(session: AsyncSession) -> MCPServer:
    server = MCPServer(name="agentops-knowledge")
    for tool in KnowledgeTools(DocumentService(session)).registered_tools():
        server.register_tool(tool)
    return server
