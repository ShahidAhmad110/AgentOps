"""add conversations and messages

Revision ID: 20260921_0003
Revises: 20260920_0002
Create Date: 2026-09-21 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260921_0003"
down_revision = "20260920_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "conversations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_conversations_user_id", "conversations", ["user_id"], unique=False)
    op.create_index("ix_conversations_organization_id", "conversations", ["organization_id"], unique=False)
    op.create_index("ix_conversations_user_org", "conversations", ["user_id", "organization_id"], unique=False)
    op.create_index("ix_conversations_updated_at", "conversations", ["updated_at"], unique=False)
    op.create_index("ix_conversations_created_at", "conversations", ["created_at"], unique=False)
    op.create_index("ix_conversations_deleted_at", "conversations", ["deleted_at"], unique=False)

    op.create_table(
        "messages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("conversation_id", "sequence", name="uq_messages_conversation_sequence"),
    )
    op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"], unique=False)
    op.create_index("ix_messages_conversation_created", "messages", ["conversation_id", "created_at"], unique=False)
    op.create_index("ix_messages_created_at", "messages", ["created_at"], unique=False)
    op.create_index("ix_messages_updated_at", "messages", ["updated_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_messages_updated_at", table_name="messages")
    op.drop_index("ix_messages_created_at", table_name="messages")
    op.drop_index("ix_messages_conversation_created", table_name="messages")
    op.drop_index("ix_messages_conversation_id", table_name="messages")
    op.drop_table("messages")

    op.drop_index("ix_conversations_deleted_at", table_name="conversations")
    op.drop_index("ix_conversations_created_at", table_name="conversations")
    op.drop_index("ix_conversations_updated_at", table_name="conversations")
    op.drop_index("ix_conversations_user_org", table_name="conversations")
    op.drop_index("ix_conversations_organization_id", table_name="conversations")
    op.drop_index("ix_conversations_user_id", table_name="conversations")
    op.drop_table("conversations")
