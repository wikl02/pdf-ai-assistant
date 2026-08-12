from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.core.audit import audit_event
from backend.database import get_db
from backend.dependencies.auth import AdminUser
from backend.schemas.evaluation import (
    EvaluationCaseCreate,
    EvaluationCaseResponse,
    EvaluationCaseUpdate,
    EvaluationDatasetCreate,
    EvaluationDatasetDetail,
    EvaluationDatasetSummary,
    EvaluationDatasetUpdate,
    EvaluationMessage,
    EvaluationResultResponse,
    EvaluationReviewUpdate,
    EvaluationRunDetail,
    EvaluationRunSummary,
    EvaluationSummary,
)
from backend.services.evaluation_service import (
    create_case,
    create_dataset,
    delete_case,
    delete_dataset,
    get_dataset_detail,
    get_run_detail,
    get_summary,
    list_datasets,
    list_runs,
    review_result,
    run_evaluation,
    update_case,
    update_dataset,
)


router = APIRouter(prefix="/api/admin/evaluations", tags=["admin-evaluations"])


@router.get("/summary", response_model=EvaluationSummary)
def evaluation_summary(_: AdminUser, db: Annotated[Session, Depends(get_db)]):
    return EvaluationSummary.model_validate(get_summary(db))


@router.get("/datasets", response_model=list[EvaluationDatasetSummary])
def get_datasets(_: AdminUser, db: Annotated[Session, Depends(get_db)]):
    return [EvaluationDatasetSummary.model_validate(item) for item in list_datasets(db)]


@router.post(
    "/datasets",
    response_model=EvaluationDatasetSummary,
    status_code=status.HTTP_201_CREATED,
)
def add_dataset(
    payload: EvaluationDatasetCreate,
    current_user: AdminUser,
    db: Annotated[Session, Depends(get_db)],
):
    dataset = create_dataset(db, payload, current_user)
    audit_event(
        "evaluation_dataset_created",
        db=db,
        actor_id=current_user.id,
        actor_name=current_user.username,
        dataset_id=dataset.id,
        knowledge_base_id=dataset.knowledge_base_id,
    )
    return EvaluationDatasetSummary.model_validate(get_dataset_detail(db, dataset.id))


@router.get("/datasets/{dataset_id}", response_model=EvaluationDatasetDetail)
def get_dataset(dataset_id: int, _: AdminUser, db: Annotated[Session, Depends(get_db)]):
    return EvaluationDatasetDetail.model_validate(get_dataset_detail(db, dataset_id))


@router.patch("/datasets/{dataset_id}", response_model=EvaluationDatasetSummary)
def edit_dataset(
    dataset_id: int,
    payload: EvaluationDatasetUpdate,
    current_user: AdminUser,
    db: Annotated[Session, Depends(get_db)],
):
    dataset = update_dataset(db, dataset_id, payload)
    audit_event(
        "evaluation_dataset_updated",
        db=db,
        actor_id=current_user.id,
        actor_name=current_user.username,
        dataset_id=dataset.id,
    )
    return EvaluationDatasetSummary.model_validate(get_dataset_detail(db, dataset.id))


@router.delete("/datasets/{dataset_id}", response_model=EvaluationMessage)
def remove_dataset(
    dataset_id: int,
    current_user: AdminUser,
    db: Annotated[Session, Depends(get_db)],
):
    delete_dataset(db, dataset_id)
    audit_event(
        "evaluation_dataset_deleted",
        db=db,
        actor_id=current_user.id,
        actor_name=current_user.username,
        dataset_id=dataset_id,
    )
    return EvaluationMessage(message="评估问题集已删除")


@router.post(
    "/datasets/{dataset_id}/cases",
    response_model=EvaluationCaseResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_case(
    dataset_id: int,
    payload: EvaluationCaseCreate,
    current_user: AdminUser,
    db: Annotated[Session, Depends(get_db)],
):
    case = create_case(db, dataset_id, payload)
    audit_event(
        "evaluation_case_created",
        db=db,
        actor_id=current_user.id,
        actor_name=current_user.username,
        dataset_id=dataset_id,
        case_id=case.id,
    )
    return EvaluationCaseResponse.model_validate(case)


@router.patch(
    "/datasets/{dataset_id}/cases/{case_id}", response_model=EvaluationCaseResponse
)
def edit_case(
    dataset_id: int,
    case_id: int,
    payload: EvaluationCaseUpdate,
    current_user: AdminUser,
    db: Annotated[Session, Depends(get_db)],
):
    case = update_case(db, dataset_id, case_id, payload)
    audit_event(
        "evaluation_case_updated",
        db=db,
        actor_id=current_user.id,
        actor_name=current_user.username,
        dataset_id=dataset_id,
        case_id=case_id,
    )
    return EvaluationCaseResponse.model_validate(case)


@router.delete(
    "/datasets/{dataset_id}/cases/{case_id}", response_model=EvaluationMessage
)
def remove_case(
    dataset_id: int,
    case_id: int,
    current_user: AdminUser,
    db: Annotated[Session, Depends(get_db)],
):
    delete_case(db, dataset_id, case_id)
    audit_event(
        "evaluation_case_deleted",
        db=db,
        actor_id=current_user.id,
        actor_name=current_user.username,
        dataset_id=dataset_id,
        case_id=case_id,
    )
    return EvaluationMessage(message="标准问题已删除")


@router.post(
    "/datasets/{dataset_id}/runs",
    response_model=EvaluationRunDetail,
    status_code=status.HTTP_201_CREATED,
)
def execute_run(
    dataset_id: int,
    current_user: AdminUser,
    db: Annotated[Session, Depends(get_db)],
):
    run = run_evaluation(db, dataset_id, current_user)
    audit_event(
        "evaluation_run_completed",
        db=db,
        actor_id=current_user.id,
        actor_name=current_user.username,
        dataset_id=dataset_id,
        run_id=run.id,
        total_cases=run.total_cases,
        answer_hit_count=run.answer_hit_count,
        source_hit_count=run.source_hit_count,
        average_response_time_ms=run.average_response_time_ms,
    )
    return EvaluationRunDetail.model_validate(get_run_detail(db, run.id))


@router.get("/runs", response_model=list[EvaluationRunSummary])
def get_runs(
    _: AdminUser,
    db: Annotated[Session, Depends(get_db)],
    dataset_id: int | None = None,
):
    return [EvaluationRunSummary.model_validate(item) for item in list_runs(db, dataset_id)]


@router.get("/runs/{run_id}", response_model=EvaluationRunDetail)
def get_run(run_id: int, _: AdminUser, db: Annotated[Session, Depends(get_db)]):
    return EvaluationRunDetail.model_validate(get_run_detail(db, run_id))


@router.patch(
    "/runs/{run_id}/results/{result_id}/review",
    response_model=EvaluationResultResponse,
)
def update_result_review(
    run_id: int,
    result_id: int,
    payload: EvaluationReviewUpdate,
    current_user: AdminUser,
    db: Annotated[Session, Depends(get_db)],
):
    result = review_result(db, run_id, result_id, payload, current_user)
    audit_event(
        "evaluation_result_reviewed",
        db=db,
        actor_id=current_user.id,
        actor_name=current_user.username,
        run_id=run_id,
        result_id=result_id,
        review_status=result.review_status,
    )
    return EvaluationResultResponse.model_validate(result)
