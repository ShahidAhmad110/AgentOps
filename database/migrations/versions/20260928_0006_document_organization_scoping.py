"""scope documents to users and organizations

Revision ID: 20260928_0006
Revises: 20260921_0005
Create Date: 2026-09-28 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260928_0006"
down_revision = "20260921_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("user_id", sa.Uuid(), nullable=True))
    op.add_column("documents", sa.Column("organization_id", sa.Uuid(), nullable=True))

    op.create_index("ix_documents_user_id", "documents", ["user_id"], unique=False)
    op.create_index("ix_documents_organization_id", "documents", ["organization_id"], unique=False)
    op.create_index("ix_documents_org_status", "documents", ["organization_id", "status"], unique=False)

    op.execute(
        "UPDATE documents SET user_id = (SELECT id FROM users ORDER BY created_at LIMIT 1) WHERE user_id IS NULL"
    )
    op.execute(
        "UPDATE documents SET organization_id = (SELECT organization_id FROM users WHERE id = documents.user_id LIMIT 1) WHERE organization_id IS NULL"
    )

    op.alter_column("documents", "user_id", existing_type=sa.Uuid(), nullable=False)
    op.alter_column("documents", "organization_id", existing_type=sa.Uuid(), nullable=False)

    op.create_foreign_key(
        "fk_documents_user_id_users",
        "documents",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_documents_organization_id_organizations",
        "documents",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("fk_documents_organization_id_organizations", "documents", type_="foreignkey")
    op.drop_constraint("fk_documents_user_id_users", "documents", type_="foreignkey")
    op.drop_index("ix_documents_org_status", table_name="documents")
    op.drop_index("ix_documents_organization_id", table_name="documents")
    op.drop_index("ix_documents_user_id", table_name="documents")
    op.drop_column("documents", "organization_id")
    op.drop_column("documents", "user_id")
