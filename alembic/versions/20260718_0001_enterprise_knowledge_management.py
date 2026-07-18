"""Create users and enterprise knowledge management tables.

Revision ID: 20260718_0001
Revises:
Create Date: 2026-07-18
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260718_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _table_names() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    tables = _table_names()

    if "users" not in tables:
        op.create_table(
            "users",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("username", sa.String(length=64), nullable=False),
            sa.Column("password_hash", sa.String(length=255), nullable=False),
            sa.Column("display_name", sa.String(length=100), nullable=True),
            sa.Column("role", sa.String(length=20), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_users_username", "users", ["username"], unique=True)
        op.create_index("ix_users_role", "users", ["role"], unique=False)
        op.create_index("ix_users_is_active", "users", ["is_active"], unique=False)

    if "knowledge_bases" not in tables:
        op.create_table(
            "knowledge_bases",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(length=120), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("collection_name", sa.String(length=255), nullable=False),
            sa.Column("created_by_id", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        )
        op.create_index("ix_knowledge_bases_name", "knowledge_bases", ["name"], unique=True)
        op.create_index(
            "ix_knowledge_bases_collection_name",
            "knowledge_bases",
            ["collection_name"],
            unique=True,
        )
        op.create_index(
            "ix_knowledge_bases_created_by_id",
            "knowledge_bases",
            ["created_by_id"],
            unique=False,
        )

    if "documents" not in tables:
        op.create_table(
            "documents",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("filename", sa.String(length=255), nullable=False),
            sa.Column("file_type", sa.String(length=20), nullable=False),
            sa.Column("file_size", sa.Integer(), nullable=False),
            sa.Column("sha256", sa.String(length=64), nullable=False),
            sa.Column("storage_path", sa.String(length=500), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False),
            sa.Column("chunk_count", sa.Integer(), nullable=False),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("uploaded_by_id", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["uploaded_by_id"], ["users.id"]),
            sa.UniqueConstraint("storage_path"),
        )
        op.create_index("ix_documents_filename", "documents", ["filename"], unique=False)
        op.create_index("ix_documents_file_type", "documents", ["file_type"], unique=False)
        op.create_index("ix_documents_sha256", "documents", ["sha256"], unique=False)
        op.create_index("ix_documents_status", "documents", ["status"], unique=False)
        op.create_index(
            "ix_documents_uploaded_by_id", "documents", ["uploaded_by_id"], unique=False
        )

    if "knowledge_base_documents" not in tables:
        op.create_table(
            "knowledge_base_documents",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("knowledge_base_id", sa.Integer(), nullable=False),
            sa.Column("document_id", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(
                ["knowledge_base_id"], ["knowledge_bases.id"], ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
            sa.UniqueConstraint("knowledge_base_id", "document_id", name="uq_kb_document"),
        )
        op.create_index(
            "ix_kb_documents_knowledge_base_id",
            "knowledge_base_documents",
            ["knowledge_base_id"],
            unique=False,
        )
        op.create_index(
            "ix_kb_documents_document_id",
            "knowledge_base_documents",
            ["document_id"],
            unique=False,
        )


def downgrade() -> None:
    tables = _table_names()
    if "knowledge_base_documents" in tables:
        op.drop_table("knowledge_base_documents")
    if "documents" in tables:
        op.drop_table("documents")
    if "knowledge_bases" in tables:
        op.drop_table("knowledge_bases")
    # Keep users because it may predate Alembic in first-stage installations.
