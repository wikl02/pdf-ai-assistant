"""Add per-answer LLM token usage.

Revision ID: 20260813_0007
Revises: 20260804_0006
Create Date: 2026-08-13
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260813_0007"
down_revision: str | None = "20260804_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("chat_messages") as batch_op:
        batch_op.add_column(sa.Column("llm_model", sa.String(length=80), nullable=True))
        batch_op.add_column(sa.Column("prompt_tokens", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("completion_tokens", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("total_tokens", sa.Integer(), nullable=True))

    with op.batch_alter_table("evaluation_results") as batch_op:
        batch_op.add_column(sa.Column("llm_model", sa.String(length=80), nullable=True))
        batch_op.add_column(sa.Column("prompt_tokens", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("completion_tokens", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("total_tokens", sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("evaluation_results") as batch_op:
        batch_op.drop_column("total_tokens")
        batch_op.drop_column("completion_tokens")
        batch_op.drop_column("prompt_tokens")
        batch_op.drop_column("llm_model")

    with op.batch_alter_table("chat_messages") as batch_op:
        batch_op.drop_column("total_tokens")
        batch_op.drop_column("completion_tokens")
        batch_op.drop_column("prompt_tokens")
        batch_op.drop_column("llm_model")
