from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete

from database.connection.session import session_factory
from database.models.conversation import Conversation, Message
from database.models.organization import Organization
from database.models.task import Task, TaskComment
from database.models.user import User
from mcp.schemas.context import ToolContext
from mcp.servers.platform import create_platform_server


@pytest.mark.asyncio
async def test_platform_mcp_tools_use_task_and_conversation_domains() -> None:
    organization_id = uuid4()
    other_organization_id = uuid4()
    user_id = uuid4()
    other_user_id = uuid4()
    created_task_id = None
    created_conversation_id = None

    async with session_factory() as session:
        try:
            session.add_all(
                [
                    Organization(id=organization_id, name="MCP Integration Org", slug="mcp-integration-org"),
                    Organization(id=other_organization_id, name="Other MCP Org", slug="other-mcp-org"),
                    User(
                        id=user_id,
                        email="mcp-integration@example.com",
                        username="mcp_integration",
                        password_hash="test-hash",
                        role="user",
                        organization_id=organization_id,
                    ),
                    User(
                        id=other_user_id,
                        email="mcp-other@example.com",
                        username="mcp_other",
                        password_hash="test-hash",
                        role="user",
                        organization_id=other_organization_id,
                    ),
                ]
            )
            await session.commit()

            server = create_platform_server(session)
            tool_names = {tool["name"] for tool in server.list_tools()}
            assert {
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
            } <= tool_names

            context = ToolContext(user_id=user_id, organization_id=organization_id)
            other_context = ToolContext(user_id=other_user_id, organization_id=other_organization_id)

            task_result = await server.call(
                "create_task", {"title": "MCP task", "priority": "HIGH"}, context
            )
            assert task_result.success is True
            created_task_id = task_result.data["id"]

            update_result = await server.call(
                "update_task",
                {"task_id": created_task_id, "status": "IN_PROGRESS"},
                context,
            )
            assert update_result.success is True
            assert update_result.data["status"] == "IN_PROGRESS"

            list_result = await server.call("list_tasks", {"status": "IN_PROGRESS"}, context)
            assert list_result.success is True
            assert list_result.data["tasks"][0]["id"] == created_task_id

            other_task_result = await server.call("get_task", {"task_id": created_task_id}, other_context)
            assert other_task_result.success is False
            assert other_task_result.error.code == "NOT_FOUND"

            conversation_result = await server.call(
                "create_conversation", {"title": "MCP conversation"}, context
            )
            assert conversation_result.success is True
            created_conversation_id = conversation_result.data["id"]

            message_result = await server.call(
                "add_message",
                {
                    "conversation_id": created_conversation_id,
                    "role": "user",
                    "content": "Hello through MCP",
                },
                context,
            )
            assert message_result.success is True
            assert message_result.data["sequence"] == 1

            conversation_read = await server.call(
                "get_conversation", {"conversation_id": created_conversation_id}, context
            )
            assert conversation_read.success is True
            assert conversation_read.data["messages"][0]["content"] == "Hello through MCP"

            other_conversation_result = await server.call(
                "get_conversation", {"conversation_id": created_conversation_id}, other_context
            )
            assert other_conversation_result.success is False
            assert other_conversation_result.error.code == "NOT_FOUND"
        finally:
            task_id = UUID(created_task_id) if created_task_id else None
            conversation_id = UUID(created_conversation_id) if created_conversation_id else None
            if task_id is not None:
                await session.execute(delete(TaskComment).where(TaskComment.task_id == task_id))
            await session.execute(delete(Task).where(Task.organization_id.in_([organization_id, other_organization_id])))
            if conversation_id is not None:
                await session.execute(delete(Message).where(Message.conversation_id == conversation_id))
            await session.execute(
                delete(Conversation).where(
                    Conversation.organization_id.in_([organization_id, other_organization_id])
                )
            )
            await session.execute(delete(User).where(User.id.in_([user_id, other_user_id])))
            await session.execute(
                delete(Organization).where(Organization.id.in_([organization_id, other_organization_id]))
            )
            await session.commit()
