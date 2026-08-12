"""Add repeatable question-answer quality evaluation records.

Revision ID: 20260804_0006
Revises: 20260804_0005
Create Date: 2026-08-04
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260804_0006"
down_revision: str | None = "20260804_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "evaluation_datasets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("knowledge_base_id", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["knowledge_base_id"], ["knowledge_bases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_evaluation_datasets_name", "evaluation_datasets", ["name"])
    op.create_index("ix_evaluation_datasets_knowledge_base_id", "evaluation_datasets", ["knowledge_base_id"])
    op.create_index("ix_evaluation_datasets_is_active", "evaluation_datasets", ["is_active"])
    op.create_index("ix_evaluation_datasets_created_by_id", "evaluation_datasets", ["created_by_id"])

    op.create_table(
        "evaluation_cases",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("dataset_id", sa.Integer(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("expected_answer_keywords", sa.JSON(), nullable=False),
        sa.Column("expected_source_names", sa.JSON(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["dataset_id"], ["evaluation_datasets.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_evaluation_cases_dataset_id", "evaluation_cases", ["dataset_id"])
    op.create_index("ix_evaluation_cases_is_active", "evaluation_cases", ["is_active"])

    op.create_table(
        "evaluation_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("dataset_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("total_cases", sa.Integer(), nullable=False),
        sa.Column("completed_cases", sa.Integer(), nullable=False),
        sa.Column("answer_hit_count", sa.Integer(), nullable=False),
        sa.Column("source_hit_count", sa.Integer(), nullable=False),
        sa.Column("average_response_time_ms", sa.Float(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("triggered_by_id", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["dataset_id"], ["evaluation_datasets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["triggered_by_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_evaluation_runs_dataset_id", "evaluation_runs", ["dataset_id"])
    op.create_index("ix_evaluation_runs_status", "evaluation_runs", ["status"])
    op.create_index("ix_evaluation_runs_triggered_by_id", "evaluation_runs", ["triggered_by_id"])

    op.create_table(
        "evaluation_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("case_id", sa.Integer(), nullable=True),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("expected_answer_keywords", sa.JSON(), nullable=False),
        sa.Column("expected_source_names", sa.JSON(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=True),
        sa.Column("sources", sa.JSON(), nullable=False),
        sa.Column("answer_keyword_hits", sa.JSON(), nullable=False),
        sa.Column("source_hits", sa.JSON(), nullable=False),
        sa.Column("answer_hit", sa.Boolean(), nullable=False),
        sa.Column("source_hit", sa.Boolean(), nullable=False),
        sa.Column("response_time_ms", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("review_status", sa.String(length=20), nullable=False),
        sa.Column("reviewer_id", sa.Integer(), nullable=True),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["evaluation_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["case_id"], ["evaluation_cases.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reviewer_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_evaluation_results_run_id", "evaluation_results", ["run_id"])
    op.create_index("ix_evaluation_results_case_id", "evaluation_results", ["case_id"])
    op.create_index("ix_evaluation_results_answer_hit", "evaluation_results", ["answer_hit"])
    op.create_index("ix_evaluation_results_source_hit", "evaluation_results", ["source_hit"])
    op.create_index("ix_evaluation_results_review_status", "evaluation_results", ["review_status"])
    op.create_index("ix_evaluation_results_reviewer_id", "evaluation_results", ["reviewer_id"])


def downgrade() -> None:
    op.drop_table("evaluation_results")
    op.drop_table("evaluation_runs")
    op.drop_table("evaluation_cases")
    op.drop_table("evaluation_datasets")
