from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from documents.retrieval.rag_context import RAGContext, RetrievedSource
from mcp.schemas.context import ToolContext
from mcp.servers.registry import MCPServer
from mcp.tools.knowledge import KnowledgeTools


USER_ID = UUID("00000000-0000-0000-0000-000000000001")
DOCUMENT_ID = UUID("00000000-0000-0000-0000-000000000002")


class FakeDocumentService:
    def __init__(self) -> None:
        self.document = SimpleNamespace(
            id=DOCUMENT_ID,
            filename="handbook.md",
            content_type="text/markdown",
            file_extension=".md",
            size_bytes=42,
            status="READY",
            error_message=None,
            metadata_json={"format": "markdown"},
        )

    async def search(self, query: str, limit: int) -> RAGContext:
        return RAGContext(
            context="[Source: handbook.md, chunk 0]\nIncident response guide.",
            sources=[RetrievedSource(DOCUMENT_ID, "handbook.md", 0, "Incident response guide.", 0.9)],
        )

    async def get(self, document_id: UUID) -> object | None:
        return self.document if document_id == DOCUMENT_ID else None


@pytest.fixture
def server() -> MCPServer:
    server = MCPServer("test")
    for tool in KnowledgeTools(FakeDocumentService()).registered_tools():
        server.register_tool(tool)
    return server


@pytest.fixture
def context() -> ToolContext:
    return ToolContext(user_id=USER_ID)


@pytest.mark.asyncio
async def test_search_documents_returns_grounded_sources(server: MCPServer, context: ToolContext) -> None:
    result = await server.call(
        "search_documents",
        {"query": "incident response", "limit": 3},
        context,
    )

    assert result.success is True
    assert result.data["sources"][0]["document_id"] == DOCUMENT_ID
    assert "handbook.md" in result.data["context"]


@pytest.mark.asyncio
async def test_get_document_returns_metadata(server: MCPServer, context: ToolContext) -> None:
    result = await server.call("get_document", {"document_id": str(DOCUMENT_ID)}, context)

    assert result.success is True
    assert result.data["filename"] == "handbook.md"
    assert result.data["status"] == "READY"


@pytest.mark.asyncio
async def test_invalid_input_is_structured_error(server: MCPServer, context: ToolContext) -> None:
    result = await server.call("search_documents", {"query": ""}, context)

    assert result.success is False
    assert result.error.code == "INVALID_TOOL_INPUT"


@pytest.mark.asyncio
async def test_unauthenticated_call_is_rejected(server: MCPServer) -> None:
    result = await server.call(
        "search_documents",
        {"query": "incident response"},
        ToolContext(user_id=USER_ID, is_authenticated=False),
    )

    assert result.success is False
    assert result.error.code == "AUTHORIZATION_ERROR"


@pytest.mark.asyncio
async def test_unknown_tool_is_structured_error(server: MCPServer, context: ToolContext) -> None:
    result = await server.call("create_task", {}, context)

    assert result.success is False
    assert result.error.code == "UNKNOWN_TOOL"


def test_duplicate_tool_registration_is_rejected(server: MCPServer) -> None:
    tool = KnowledgeTools(FakeDocumentService()).registered_tools()[0]

    with pytest.raises(ValueError, match="already registered"):
        server.register_tool(tool)


def test_server_lists_explicit_tool_schemas(server: MCPServer) -> None:
    tools = server.list_tools()

    assert [tool["name"] for tool in tools] == ["get_document", "search_documents"]
    assert "properties" in tools[1]["input_schema"]
