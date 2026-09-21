"""add agent execution persistence

Revision ID: 20260921_0005
Revises: 20260921_0004
Create Date: 2026-09-21 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260921_0005"
down_revision = "20260921_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=True),
        sa.Column("request", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("final_response", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_runs_user_id", "agent_runs", ["user_id"], unique=False)
    op.create_index("ix_agent_runs_organization_id", "agent_runs", ["organization_id"], unique=False)
    op.create_index("ix_agent_runs_conversation_id", "agent_runs", ["conversation_id"], unique=False)
    op.create_index("ix_agent_runs_status", "agent_runs", ["status"], unique=False)
    op.create_index("ix_agent_runs_org_status", "agent_runs", ["organization_id", "status"], unique=False)
    op.create_index("ix_agent_runs_user_created", "agent_runs", ["user_id", "created_at"], unique=False)
    op.create_index("ix_agent_runs_created_at", "agent_runs", ["created_at"], unique=False)
    op.create_index("ix_agent_runs_updated_at", "agent_runs", ["updated_at"], unique=False)

    op.create_table(
        "agent_steps",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("node_name", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["agent_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_steps_run_id", "agent_steps", ["run_id"], unique=False)
    op.create_index("ix_agent_steps_run_sequence", "agent_steps", ["run_id", "sequence"], unique=False)
    op.create_index("ix_agent_steps_created_at", "agent_steps", ["created_at"], unique=False)
    op.create_index("ix_agent_steps_updated_at", "agent_steps", ["updated_at"], unique=False)

    op.create_table(
        "tool_calls",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("tool_name", sa.String(length=128), nullable=False),
        sa.Column("arguments", sa.JSON(), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["agent_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tool_calls_run_id", "tool_calls", ["run_id"], unique=False)
    op.create_index("ix_tool_calls_run_created", "tool_calls", ["run_id", "created_at"], unique=False)
    op.create_index("ix_tool_calls_created_at", "tool_calls", ["created_at"], unique=False)
    op.create_index("ix_tool_calls_updated_at", "tool_calls", ["updated_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_tool_calls_updated_at", table_name="tool_calls")
    op.drop_index("ix_tool_calls_created_at", table_name="tool_calls")
    op.drop_index("ix_tool_calls_run_created", table_name="tool_calls")
    op.drop_index("ix_tool_calls_run_id", table_name="tool_calls")
    op.drop_table("tool_calls")

    op.drop_index("ix_agent_steps_updated_at", table_name="agent_steps")
    op.drop_index("ix_agent_steps_created_at", table_name="agent_steps")
    op.drop_index("ix_agent_steps_run_sequence", table_name="agent_steps")
    op.drop_index("ix_agent_steps_run_id", table_name="agent_steps")
    op.drop_table("agent_steps")

    op.drop_index("ix_agent_runs_updated_at", table_name="agent_runs")
    op.drop_index("ix_agent_runs_created_at", table_name="agent_runs")
    op.drop_index("ix_agent_runs_user_created", table_name="agent_runs")
    op.drop_index("ix_agent_runs_org_status", table_name="agent_runs")
    op.drop_index("ix_agent_runs_status", table_name="agent_runs")
    op.drop_index("ix_agent_runs_conversation_id", table_name="agent_runs")
    op.drop_index("ix_agent_runs_organization_id", table_name="agent_runs")
    op.drop_index("ix_agent_runs_user_id", table_name="agent_runs")
    op.drop_table("agent_runs")
