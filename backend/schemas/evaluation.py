from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from backend.models.evaluation import EvaluationReviewStatus, EvaluationRunStatus


class EvaluationDatasetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    knowledge_base_id: int = Field(gt=0)


class EvaluationDatasetUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    is_active: bool | None = None


class EvaluationCaseCreate(BaseModel):
    question: str = Field(min_length=1, max_length=5000)
    expected_answer_keywords: list[str] = Field(min_length=1, max_length=20)
    expected_source_names: list[str] = Field(min_length=1, max_length=20)
    notes: str | None = Field(default=None, max_length=2000)
    is_active: bool = True


class EvaluationCaseUpdate(BaseModel):
    question: str | None = Field(default=None, min_length=1, max_length=5000)
    expected_answer_keywords: list[str] | None = Field(default=None, min_length=1, max_length=20)
    expected_source_names: list[str] | None = Field(default=None, min_length=1, max_length=20)
    notes: str | None = Field(default=None, max_length=2000)
    is_active: bool | None = None


class EvaluationCaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    dataset_id: int
    question: str
    expected_answer_keywords: list[str]
    expected_source_names: list[str]
    notes: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class EvaluationResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    run_id: int
    case_id: int | None
    question: str
    expected_answer_keywords: list[str]
    expected_source_names: list[str]
    answer: str | None
    sources: list[dict[str, Any]]
    answer_keyword_hits: list[str]
    source_hits: list[str]
    answer_hit: bool
    source_hit: bool
    response_time_ms: int | None
    error_message: str | None
    review_status: EvaluationReviewStatus
    reviewer_id: int | None
    review_note: str | None
    reviewed_at: datetime | None
    created_at: datetime


class EvaluationRunSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    dataset_id: int
    status: EvaluationRunStatus
    total_cases: int
    completed_cases: int
    answer_hit_count: int
    source_hit_count: int
    average_response_time_ms: float | None
    error_message: str | None
    triggered_by_id: int | None
    started_at: datetime
    completed_at: datetime | None
    created_at: datetime


class EvaluationRunDetail(EvaluationRunSummary):
    results: list[EvaluationResultResponse]


class EvaluationDatasetSummary(BaseModel):
    id: int
    name: str
    description: str | None
    knowledge_base_id: int
    knowledge_base_name: str
    is_active: bool
    created_by_id: int | None
    case_count: int
    run_count: int
    created_at: datetime
    updated_at: datetime


class EvaluationDatasetDetail(EvaluationDatasetSummary):
    cases: list[EvaluationCaseResponse]
    recent_runs: list[EvaluationRunSummary]


class EvaluationReviewUpdate(BaseModel):
    review_status: EvaluationReviewStatus
    review_note: str | None = Field(default=None, max_length=2000)


class EvaluationSummary(BaseModel):
    dataset_count: int
    case_count: int
    completed_run_count: int
    latest_answer_hit_rate: float | None
    latest_source_hit_rate: float | None
    latest_average_response_time_ms: float | None


class EvaluationMessage(BaseModel):
    message: str
