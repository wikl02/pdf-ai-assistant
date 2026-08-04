"""Add departments and knowledge-base access-control tables.

Revision ID: 20260804_0003
Revises: 20260718_0002
Create Date: 2026-08-04
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260804_0003"
down_revision: str | None = "20260718_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "departments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        *_timestamps(),
    )
    op.create_index("ix_departments_name", "departments", ["name"], unique=True)
    op.create_index("ix_departments_code", "departments", ["code"], unique=True)
    op.create_index("ix_departments_is_active", "departments", ["is_active"])

    op.create_table(
        "user_departments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("department_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["department_id"], ["departments.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint("user_id", "department_id", name="uq_user_department"),
    )
    op.create_index("ix_user_departments_user_id", "user_departments", ["user_id"])
    op.create_index(
        "ix_user_departments_department_id", "user_departments", ["department_id"]
    )

    op.create_table(
        "knowledge_base_user_permissions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("knowledge_base_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("permission", sa.String(length=20), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["knowledge_base_id"], ["knowledge_bases.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "knowledge_base_id", "user_id", name="uq_kb_user_permission"
        ),
    )
    op.create_index(
        "ix_knowledge_base_user_permissions_knowledge_base_id",
        "knowledge_base_user_permissions",
        ["knowledge_base_id"],
    )
    op.create_index(
        "ix_knowledge_base_user_permissions_user_id",
        "knowledge_base_user_permissions",
        ["user_id"],
    )
    op.create_index(
        "ix_knowledge_base_user_permissions_permission",
        "knowledge_base_user_permissions",
        ["permission"],
    )

    op.create_table(
        "knowledge_base_role_permissions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("knowledge_base_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("permission", sa.String(length=20), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["knowledge_base_id"], ["knowledge_bases.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint(
            "knowledge_base_id", "role", name="uq_kb_role_permission"
        ),
    )
    op.create_index(
        "ix_knowledge_base_role_permissions_knowledge_base_id",
        "knowledge_base_role_permissions",
        ["knowledge_base_id"],
    )
    op.create_index(
        "ix_knowledge_base_role_permissions_role",
        "knowledge_base_role_permissions",
        ["role"],
    )
    op.create_index(
        "ix_knowledge_base_role_permissions_permission",
        "knowledge_base_role_permissions",
        ["permission"],
    )

    op.create_table(
        "knowledge_base_department_permissions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("knowledge_base_id", sa.Integer(), nullable=False),
        sa.Column("department_id", sa.Integer(), nullable=False),
        sa.Column("permission", sa.String(length=20), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["knowledge_base_id"], ["knowledge_bases.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["department_id"], ["departments.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint(
            "knowledge_base_id",
            "department_id",
            name="uq_kb_department_permission",
        ),
    )
    op.create_index(
        "ix_knowledge_base_department_permissions_knowledge_base_id",
        "knowledge_base_department_permissions",
        ["knowledge_base_id"],
    )
    op.create_index(
        "ix_knowledge_base_department_permissions_department_id",
        "knowledge_base_department_permissions",
        ["department_id"],
    )
    op.create_index(
        "ix_knowledge_base_department_permissions_permission",
        "knowledge_base_department_permissions",
        ["permission"],
    )

    # Preserve the pre-upgrade behavior for existing knowledge bases. Administrators
    # can remove these role grants later to switch individual bases to deny-by-default.
    op.execute(
        sa.text(
            """
            INSERT INTO knowledge_base_role_permissions
                (knowledge_base_id, role, permission, created_at, updated_at)
            SELECT id, 'user', 'query', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            FROM knowledge_bases
            """
        )
    )


def downgrade() -> None:
    op.drop_table("knowledge_base_department_permissions")
    op.drop_table("knowledge_base_role_permissions")
    op.drop_table("knowledge_base_user_permissions")
    op.drop_table("user_departments")
    op.drop_table("departments")
