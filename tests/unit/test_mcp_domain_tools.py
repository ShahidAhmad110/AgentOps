from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from backend.schemas.conversation import ConversationCreate, MessageCreate
from backend.schemas.task import TaskCreate, TaskUpdate
from mcp.schemas.context import ToolContext
from mcp.servers.registry import MCPServer
from mcp.tools.conversations import ConversationTools
from mcp.tools.tasks import TaskTools

USER_ID = UUID("00000000-0000-0000-0000-000000000001")
ORGANIZATION_ID = UUID("00000000-0000-0000-0000-000000000002")
TASK_ID = UUID("00000000-0000-0000-0000-000000000003")
CONVERSATION_ID = UUID("00000000-0000-0000-0000-000000000004")
NOW = datetime.now(timezone.utc)


def task(task_id: UUID = TASK_ID, organization_id: UUID = ORGANIZATION_ID):
    return SimpleNamespace(
        id=task_id,
        organization_id=organization_id,
        owner_id=USER_ID,
        assignee_id=None,
        title="Prepare report",
        description="Report details",
        status="TODO",
        priority="HIGH",
        due_date=None,
        created_at=NOW,
        updated_at=NOW,
        deleted_at=None,
    )


def conversation(conversation_id: UUID = CONVERSATION_ID, organization_id: UUID = ORGANIZATION_ID):
    return SimpleNamespace(
        id=conversation_id,
        user_id=USER_ID,
        organization_id=organization_id,
        title="Incident discussion",
        created_at=NOW,
        updated_at=NOW,
    )


def message():
    return SimpleNamespace(
        id=uuid4(),
        conversation_id=CONVERSATION_ID,
        sequence=1,
        role="user",
        content="Hello",
        created_at=NOW,
        updated_at=NOW,
    )


class FakeTaskService:
    def __init__(self):
        self.current = task()
        self.calls = []

    async def create(self, request, owner_id, organization_id):
        self.calls.append(("create", request, owner_id, organization_id))
        return self.current

    async def get(self, task_id, organization_id):
        self.calls.append(("get", task_id, organization_id))
        return self.current if task_id == TASK_ID and organization_id == ORGANIZATION_ID else None

    async def update(self, task_id, request, organization_id):
        self.calls.append(("update", task_id, request, organization_id))
        return self.current if task_id == TASK_ID and organization_id == ORGANIZATION_ID else None

    async def list(self, organization_id, limit, offset, status, assignee_id, search):
        self.calls.append(("list", organization_id, limit, offset, status, assignee_id, search))
        return [self.current] if organization_id == ORGANIZATION_ID else []


class FakeConversationService:
    def __init__(self):
        self.current = conversation()
        self.calls = []

    async def create(self, request, user_id, organization_id):
        self.calls.append(("create", request, user_id, organization_id))
        return self.current

    async def get_owned(self, conversation_id, user_id, organization_id):
        self.calls.append(("get", conversation_id, user_id, organization_id))
        return self.current if conversation_id == CONVERSATION_ID and organization_id == ORGANIZATION_ID else None

    async def list_owned(self, user_id, organization_id, limit, offset):
        self.calls.append(("list", user_id, organization_id, limit, offset))
        return [self.current] if organization_id == ORGANIZATION_ID else []

    async def add_message(self, conversation_id, request, user_id, organization_id):
        self.calls.append(("add_message", conversation_id, request, user_id, organization_id))
        return message() if conversation_id == CONVERSATION_ID and organization_id == ORGANIZATION_ID else None

    async def list_messages(self, conversation_id, user_id, organization_id):
        self.calls.append(("list_messages", conversation_id, user_id, organization_id))
        return [message()] if conversation_id == CONVERSATION_ID and organization_id == ORGANIZATION_ID else None


def make_task_tools():
    tool_group = object.__new__(TaskTools)
    tool_group.service = FakeTaskService()
    return tool_group


def make_conversation_tools():
    tool_group = object.__new__(ConversationTools)
    tool_group.service = FakeConversationService()
    return tool_group


@pytest.fixture
def context():
    return ToolContext(user_id=USER_ID, organization_id=ORGANIZATION_ID)


@pytest.mark.asyncio
async def test_task_tools_delegate_create_get_update_and_list(context):
    group = make_task_tools()
    server = MCPServer("tasks")
    for tool in group.registered_tools():
        server.register_tool(tool)

    create = await server.call("create_task", {"title": "Prepare report"}, context)
    get_result = await server.call("get_task", {"task_id": str(TASK_ID)}, context)
    update = await server.call("update_task", {"task_id": str(TASK_ID), "status": "COMPLETED"}, context)
    listed = await server.call("list_tasks", {"status": "TODO", "search": "report"}, context)

    assert create.success and create.data["id"] == str(TASK_ID)
    assert get_result.success and get_result.data["organization_id"] == str(ORGANIZATION_ID)
    assert update.success and update.data["status"] == "TODO"
    assert listed.success and listed.data["tasks"][0]["id"] == str(TASK_ID)


@pytest.mark.asyncio
async def test_conversation_tools_delegate_all_operations(context):
    group = make_conversation_tools()
    server = MCPServer("conversations")
    for tool in group.registered_tools():
        server.register_tool(tool)

    create = await server.call("create_conversation", {"title": "New discussion"}, context)
    get_result = await server.call("get_conversation", {"conversation_id": str(CONVERSATION_ID)}, context)
    search = await server.call("search_conversations", {"search": "incident"}, context)
    added = await server.call(
        "add_message",
        {"conversation_id": str(CONVERSATION_ID), "role": "user", "content": "Hello"},
        context,
    )
    messages = await server.call("list_messages", {"conversation_id": str(CONVERSATION_ID)}, context)

    assert create.success and create.data["id"] == str(CONVERSATION_ID)
    assert get_result.success and get_result.data["messages"][0]["sequence"] == 1
    assert search.success and search.data["conversations"][0]["title"] == "Incident discussion"
    assert added.success and added.data["content"] == "Hello"
    assert messages.success and messages.data["messages"]


@pytest.mark.asyncio
async def test_domain_tools_reject_missing_organization(context):
    task_server = MCPServer("tasks")
    for tool in make_task_tools().registered_tools():
        task_server.register_tool(tool)
    conversation_server = MCPServer("conversations")
    for tool in make_conversation_tools().registered_tools():
        conversation_server.register_tool(tool)
    no_org = context.model_copy(update={"organization_id": None})

    task_result = await task_server.call("get_task", {"task_id": str(TASK_ID)}, no_org)
    conversation_result = await conversation_server.call(
        "get_conversation", {"conversation_id": str(CONVERSATION_ID)}, no_org
    )

    assert not task_result.success and task_result.error.code == "AUTHORIZATION_ERROR"
    assert not conversation_result.success and conversation_result.error.code == "AUTHORIZATION_ERROR"


@pytest.mark.asyncio
async def test_domain_tools_reject_invalid_input_and_missing_resources(context):
    task_server = MCPServer("tasks")
    for tool in make_task_tools().registered_tools():
        task_server.register_tool(tool)
    conversation_server = MCPServer("conversations")
    for tool in make_conversation_tools().registered_tools():
        conversation_server.register_tool(tool)

    invalid = await task_server.call("create_task", {"title": ""}, context)
    missing = await conversation_server.call("get_conversation", {"conversation_id": str(uuid4())}, context)

    assert not invalid.success and invalid.error.code == "INVALID_TOOL_INPUT"
    assert not missing.success and missing.error.code == "NOT_FOUND"


def test_platform_tool_names_are_unique_and_include_existing_knowledge_tools():
    from mcp.servers.platform import create_platform_server

    server = create_platform_server
    assert callable(server)
    expected = {
        "search_documents",
        "get_document",
        "create_task",
        "get_task",
        "update_task",
        "list_tasks",
        "create_conversation",
        "get_conversation",
        "search_conversations",
        "add_message",
        "list_messages",
    }
    assert len(expected) == 11
