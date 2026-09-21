"""add tasks and task comments

Revision ID: 20260921_0004
Revises: 20260921_0003
Create Date: 2026-09-21 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260921_0004"
down_revision = "20260921_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tasks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("assignee_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), server_default=sa.text("'TODO'"), nullable=False),
        sa.Column("priority", sa.String(length=32), nullable=True),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('TODO', 'IN_PROGRESS', 'BLOCKED', 'COMPLETED', 'CANCELLED')",
            name="ck_tasks_status",
        ),
        sa.ForeignKeyConstraint(["assignee_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tasks_organization_id", "tasks", ["organization_id"], unique=False)
    op.create_index("ix_tasks_owner_id", "tasks", ["owner_id"], unique=False)
    op.create_index("ix_tasks_assignee_id", "tasks", ["assignee_id"], unique=False)
    op.create_index("ix_tasks_status", "tasks", ["status"], unique=False)
    op.create_index("ix_tasks_organization_status", "tasks", ["organization_id", "status"], unique=False)
    op.create_index("ix_tasks_organization_assignee", "tasks", ["organization_id", "assignee_id"], unique=False)
    op.create_index("ix_tasks_due_date", "tasks", ["due_date"], unique=False)
    op.create_index("ix_tasks_created_at", "tasks", ["created_at"], unique=False)
    op.create_index("ix_tasks_updated_at", "tasks", ["updated_at"], unique=False)
    op.create_index("ix_tasks_deleted_at", "tasks", ["deleted_at"], unique=False)

    op.create_table(
        "task_comments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("author_id", sa.Uuid(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_task_comments_task_id", "task_comments", ["task_id"], unique=False)
    op.create_index("ix_task_comments_author_id", "task_comments", ["author_id"], unique=False)
    op.create_index("ix_task_comments_task_created", "task_comments", ["task_id", "created_at"], unique=False)
    op.create_index("ix_task_comments_created_at", "task_comments", ["created_at"], unique=False)
    op.create_index("ix_task_comments_updated_at", "task_comments", ["updated_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_task_comments_updated_at", table_name="task_comments")
    op.drop_index("ix_task_comments_created_at", table_name="task_comments")
    op.drop_index("ix_task_comments_task_created", table_name="task_comments")
    op.drop_index("ix_task_comments_author_id", table_name="task_comments")
    op.drop_index("ix_task_comments_task_id", table_name="task_comments")
    op.drop_table("task_comments")

    op.drop_index("ix_tasks_deleted_at", table_name="tasks")
    op.drop_index("ix_tasks_updated_at", table_name="tasks")
    op.drop_index("ix_tasks_created_at", table_name="tasks")
    op.drop_index("ix_tasks_due_date", table_name="tasks")
    op.drop_index("ix_tasks_organization_assignee", table_name="tasks")
    op.drop_index("ix_tasks_organization_status", table_name="tasks")
    op.drop_index("ix_tasks_status", table_name="tasks")
    op.drop_index("ix_tasks_assignee_id", table_name="tasks")
    op.drop_index("ix_tasks_owner_id", table_name="tasks")
    op.drop_index("ix_tasks_organization_id", table_name="tasks")
    op.drop_table("tasks")
