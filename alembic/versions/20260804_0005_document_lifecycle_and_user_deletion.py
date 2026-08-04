"""Add document lifecycle records and user soft deletion.

Revision ID: 20260804_0005
Revises: 20260804_0004
Create Date: 2026-08-04
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260804_0005"
down_revision: str | None = "20260804_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("deleted_by_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_users_deleted_at", ["deleted_at"])
        batch_op.create_index("ix_users_deleted_by_id", ["deleted_by_id"])

    with op.batch_alter_table("documents") as batch_op:
        batch_op.add_column(
            sa.Column(
                "current_version_number",
                sa.Integer(),
                nullable=False,
                server_default="1",
            )
        )

    op.create_table(
        "document_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("file_type", sa.String(length=20), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("storage_path", sa.String(length=500), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("chunk_count", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("document_id", "version_number", name="uq_document_version"),
        sa.UniqueConstraint("storage_path"),
    )
    op.create_index("ix_document_versions_document_id", "document_versions", ["document_id"])
    op.create_index("ix_document_versions_sha256", "document_versions", ["sha256"])
    op.create_index("ix_document_versions_status", "document_versions", ["status"])
    op.create_index("ix_document_versions_created_by_id", "document_versions", ["created_by_id"])

    op.create_table(
        "document_index_tasks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("knowledge_base_id", sa.Integer(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("trigger", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("chunk_count", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("initiated_by_id", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["knowledge_base_id"], ["knowledge_bases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["initiated_by_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_document_index_tasks_document_id", "document_index_tasks", ["document_id"])
    op.create_index("ix_document_index_tasks_knowledge_base_id", "document_index_tasks", ["knowledge_base_id"])
    op.create_index("ix_document_index_tasks_trigger", "document_index_tasks", ["trigger"])
    op.create_index("ix_document_index_tasks_status", "document_index_tasks", ["status"])
    op.create_index("ix_document_index_tasks_initiated_by_id", "document_index_tasks", ["initiated_by_id"])

    # Existing documents become version 1 without moving or duplicating their files.
    op.execute(
        sa.text(
            """
            INSERT INTO document_versions
                (document_id, version_number, filename, file_type, file_size, sha256,
                 storage_path, status, chunk_count, error_message, created_by_id, created_at)
            SELECT id, 1, filename, file_type, file_size, sha256,
                   storage_path, status, chunk_count, error_message, uploaded_by_id, created_at
            FROM documents
            """
        )
    )


def downgrade() -> None:
    op.drop_table("document_index_tasks")
    op.drop_table("document_versions")
    with op.batch_alter_table("documents") as batch_op:
        batch_op.drop_column("current_version_number")
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_index("ix_users_deleted_by_id")
        batch_op.drop_index("ix_users_deleted_at")
        batch_op.drop_column("deleted_by_id")
        batch_op.drop_column("deleted_at")
