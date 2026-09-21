"""add document ingestion and retrieval tables

Revision ID: 20260920_0002
Revises: 20260919_0001
Create Date: 2026-09-20 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260920_0002"
down_revision = "20260919_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=150), nullable=False),
        sa.Column("file_extension", sa.String(length=16), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("checksum", sa.String(length=64), nullable=False),
        sa.Column("storage_path", sa.String(length=1024), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_documents_status", "documents", ["status"], unique=False)
    op.create_index("ix_documents_checksum", "documents", ["checksum"], unique=False)
    op.create_index("ix_documents_created_at", "documents", ["created_at"], unique=False)
    op.create_index("ix_documents_updated_at", "documents", ["updated_at"], unique=False)
    op.create_index("ix_documents_deleted_at", "documents", ["deleted_at"], unique=False)

    op.create_table(
        "document_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("extracted_text", sa.Text(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id", "version_number", name="uq_document_versions_number"),
    )
    op.create_index("ix_document_versions_document_id", "document_versions", ["document_id"], unique=False)
    op.create_index("ix_document_versions_created_at", "document_versions", ["created_at"], unique=False)
    op.create_index("ix_document_versions_updated_at", "document_versions", ["updated_at"], unique=False)

    op.create_table(
        "document_chunks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("version_id", sa.Uuid(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", sa.JSON(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["version_id"], ["document_versions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("version_id", "chunk_index", name="uq_document_chunks_index"),
    )
    op.create_index("ix_document_chunks_version_id", "document_chunks", ["version_id"], unique=False)
    op.create_index("ix_document_chunks_created_at", "document_chunks", ["created_at"], unique=False)
    op.create_index("ix_document_chunks_updated_at", "document_chunks", ["updated_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_document_chunks_updated_at", table_name="document_chunks")
    op.drop_index("ix_document_chunks_created_at", table_name="document_chunks")
    op.drop_index("ix_document_chunks_version_id", table_name="document_chunks")
    op.drop_table("document_chunks")

    op.drop_index("ix_document_versions_updated_at", table_name="document_versions")
    op.drop_index("ix_document_versions_created_at", table_name="document_versions")
    op.drop_index("ix_document_versions_document_id", table_name="document_versions")
    op.drop_table("document_versions")

    op.drop_index("ix_documents_deleted_at", table_name="documents")
    op.drop_index("ix_documents_updated_at", table_name="documents")
    op.drop_index("ix_documents_created_at", table_name="documents")
    op.drop_index("ix_documents_checksum", table_name="documents")
    op.drop_index("ix_documents_status", table_name="documents")
    op.drop_table("documents")
