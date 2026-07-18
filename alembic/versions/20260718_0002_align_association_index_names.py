"""Align association index names with SQLAlchemy metadata.

Revision ID: 20260718_0002
Revises: 20260718_0001
Create Date: 2026-07-18
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260718_0002"
down_revision: str | None = "20260718_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


OLD_DOCUMENT_INDEX = "ix_kb_documents_document_id"
OLD_KNOWLEDGE_BASE_INDEX = "ix_kb_documents_knowledge_base_id"
NEW_DOCUMENT_INDEX = "ix_knowledge_base_documents_document_id"
NEW_KNOWLEDGE_BASE_INDEX = "ix_knowledge_base_documents_knowledge_base_id"


def _index_names() -> set[str]:
    indexes = sa.inspect(op.get_bind()).get_indexes("knowledge_base_documents")
    return {index["name"] for index in indexes}


def upgrade() -> None:
    indexes = _index_names()
    if OLD_DOCUMENT_INDEX in indexes:
        op.drop_index(OLD_DOCUMENT_INDEX, table_name="knowledge_base_documents")
    if OLD_KNOWLEDGE_BASE_INDEX in indexes:
        op.drop_index(OLD_KNOWLEDGE_BASE_INDEX, table_name="knowledge_base_documents")
    indexes = _index_names()
    if NEW_DOCUMENT_INDEX not in indexes:
        op.create_index(
            NEW_DOCUMENT_INDEX,
            "knowledge_base_documents",
            ["document_id"],
            unique=False,
        )
    if NEW_KNOWLEDGE_BASE_INDEX not in indexes:
        op.create_index(
            NEW_KNOWLEDGE_BASE_INDEX,
            "knowledge_base_documents",
            ["knowledge_base_id"],
            unique=False,
        )


def downgrade() -> None:
    indexes = _index_names()
    if NEW_DOCUMENT_INDEX in indexes:
        op.drop_index(NEW_DOCUMENT_INDEX, table_name="knowledge_base_documents")
    if NEW_KNOWLEDGE_BASE_INDEX in indexes:
        op.drop_index(NEW_KNOWLEDGE_BASE_INDEX, table_name="knowledge_base_documents")
    op.create_index(
        OLD_DOCUMENT_INDEX,
        "knowledge_base_documents",
        ["document_id"],
        unique=False,
    )
    op.create_index(
        OLD_KNOWLEDGE_BASE_INDEX,
        "knowledge_base_documents",
        ["knowledge_base_id"],
        unique=False,
    )
