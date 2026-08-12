"""Repeatable RAG evaluation without writing into user chat history."""

import json
from datetime import datetime, timezone
from time import perf_counter
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.models.evaluation import (
    EvaluationCase,
    EvaluationDataset,
    EvaluationResult,
    EvaluationReviewStatus,
    EvaluationRun,
    EvaluationRunStatus,
)
from backend.models.knowledge import KnowledgeBase
from backend.models.user import User
from backend.schemas.evaluation import (
    EvaluationCaseCreate,
    EvaluationCaseUpdate,
    EvaluationDatasetCreate,
    EvaluationDatasetUpdate,
    EvaluationReviewUpdate,
)
from backend.services.knowledge_service import answer_question


MAX_CASES_PER_RUN = 50


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _clean_values(values: list[str]) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = value.strip()
        key = normalized.casefold()
        if normalized and key not in seen:
            cleaned.append(normalized)
            seen.add(key)
    if not cleaned:
        raise HTTPException(status_code=422, detail="期望关键词和期望来源不能只包含空白内容")
    return cleaned


def _get_dataset(db: Session, dataset_id: int) -> EvaluationDataset:
    dataset = db.get(EvaluationDataset, dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="评估问题集不存在")
    return dataset


def _get_case(db: Session, dataset_id: int, case_id: int) -> EvaluationCase:
    case = db.scalar(
        select(EvaluationCase).where(
            EvaluationCase.id == case_id,
            EvaluationCase.dataset_id == dataset_id,
        )
    )
    if not case:
        raise HTTPException(status_code=404, detail="标准问题不存在")
    return case


def _get_run(db: Session, run_id: int) -> EvaluationRun:
    run = db.get(EvaluationRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="评估运行记录不存在")
    return run


def _dataset_dict(db: Session, dataset: EvaluationDataset) -> dict[str, Any]:
    knowledge_base = db.get(KnowledgeBase, dataset.knowledge_base_id)
    case_count = db.scalar(
        select(func.count(EvaluationCase.id)).where(EvaluationCase.dataset_id == dataset.id)
    ) or 0
    run_count = db.scalar(
        select(func.count(EvaluationRun.id)).where(EvaluationRun.dataset_id == dataset.id)
    ) or 0
    return {
        "id": dataset.id,
        "name": dataset.name,
        "description": dataset.description,
        "knowledge_base_id": dataset.knowledge_base_id,
        "knowledge_base_name": knowledge_base.name if knowledge_base else "已删除知识库",
        "is_active": dataset.is_active,
        "created_by_id": dataset.created_by_id,
        "case_count": case_count,
        "run_count": run_count,
        "created_at": dataset.created_at,
        "updated_at": dataset.updated_at,
    }


def list_datasets(db: Session) -> list[dict[str, Any]]:
    datasets = db.scalars(
        select(EvaluationDataset).order_by(EvaluationDataset.updated_at.desc())
    ).all()
    return [_dataset_dict(db, item) for item in datasets]


def create_dataset(
    db: Session, payload: EvaluationDatasetCreate, current_user: User
) -> EvaluationDataset:
    if not db.get(KnowledgeBase, payload.knowledge_base_id):
        raise HTTPException(status_code=404, detail="知识库不存在")
    dataset = EvaluationDataset(
        name=payload.name.strip(),
        description=payload.description.strip() if payload.description else None,
        knowledge_base_id=payload.knowledge_base_id,
        created_by_id=current_user.id,
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    return dataset


def update_dataset(
    db: Session, dataset_id: int, payload: EvaluationDatasetUpdate
) -> EvaluationDataset:
    dataset = _get_dataset(db, dataset_id)
    values = payload.model_dump(exclude_unset=True)
    if "name" in values and values["name"] is not None:
        values["name"] = values["name"].strip()
    if "description" in values and values["description"] is not None:
        values["description"] = values["description"].strip() or None
    for field, value in values.items():
        setattr(dataset, field, value)
    db.commit()
    db.refresh(dataset)
    return dataset


def delete_dataset(db: Session, dataset_id: int) -> None:
    dataset = _get_dataset(db, dataset_id)
    db.delete(dataset)
    db.commit()


def get_dataset_detail(db: Session, dataset_id: int) -> dict[str, Any]:
    dataset = _get_dataset(db, dataset_id)
    result = _dataset_dict(db, dataset)
    result["cases"] = db.scalars(
        select(EvaluationCase)
        .where(EvaluationCase.dataset_id == dataset_id)
        .order_by(EvaluationCase.created_at.asc())
    ).all()
    result["recent_runs"] = db.scalars(
        select(EvaluationRun)
        .where(EvaluationRun.dataset_id == dataset_id)
        .order_by(EvaluationRun.created_at.desc())
        .limit(10)
    ).all()
    return result


def create_case(
    db: Session, dataset_id: int, payload: EvaluationCaseCreate
) -> EvaluationCase:
    _get_dataset(db, dataset_id)
    case = EvaluationCase(
        dataset_id=dataset_id,
        question=payload.question.strip(),
        expected_answer_keywords=_clean_values(payload.expected_answer_keywords),
        expected_source_names=_clean_values(payload.expected_source_names),
        notes=payload.notes.strip() if payload.notes else None,
        is_active=payload.is_active,
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    return case


def update_case(
    db: Session, dataset_id: int, case_id: int, payload: EvaluationCaseUpdate
) -> EvaluationCase:
    case = _get_case(db, dataset_id, case_id)
    values = payload.model_dump(exclude_unset=True)
    if values.get("question") is not None:
        values["question"] = values["question"].strip()
    for field in ("expected_answer_keywords", "expected_source_names"):
        if values.get(field) is not None:
            values[field] = _clean_values(values[field])
    if "notes" in values and values["notes"] is not None:
        values["notes"] = values["notes"].strip() or None
    for field, value in values.items():
        setattr(case, field, value)
    db.commit()
    db.refresh(case)
    return case


def delete_case(db: Session, dataset_id: int, case_id: int) -> None:
    case = _get_case(db, dataset_id, case_id)
    db.delete(case)
    db.commit()


def _json_sources(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return json.loads(json.dumps(sources, default=str))


def _source_names(sources: list[dict[str, Any]]) -> list[str]:
    names: list[str] = []
    for source in sources:
        metadata = source.get("metadata") or {}
        name = metadata.get("source_name") or metadata.get("filename")
        if name:
            names.append(str(name))
    return names


def _matched_sources(expected: list[str], actual: list[str]) -> list[str]:
    actual_keys = [item.casefold() for item in actual]
    return [
        item
        for item in expected
        if any(item.casefold() == value or item.casefold() in value for value in actual_keys)
    ]


def run_evaluation(db: Session, dataset_id: int, current_user: User) -> EvaluationRun:
    dataset = _get_dataset(db, dataset_id)
    if not dataset.is_active:
        raise HTTPException(status_code=409, detail="该问题集已停用，不能执行评估")
    knowledge_base = db.get(KnowledgeBase, dataset.knowledge_base_id)
    if not knowledge_base:
        raise HTTPException(status_code=404, detail="关联知识库不存在")
    cases = db.scalars(
        select(EvaluationCase)
        .where(
            EvaluationCase.dataset_id == dataset_id,
            EvaluationCase.is_active.is_(True),
        )
        .order_by(EvaluationCase.id.asc())
    ).all()
    if not cases:
        raise HTTPException(status_code=409, detail="问题集中没有可执行的标准问题")
    if len(cases) > MAX_CASES_PER_RUN:
        raise HTTPException(
            status_code=409,
            detail=f"单次最多执行 {MAX_CASES_PER_RUN} 道启用题，请先停用部分问题",
        )

    run = EvaluationRun(
        dataset_id=dataset_id,
        status=EvaluationRunStatus.RUNNING.value,
        total_cases=len(cases),
        triggered_by_id=current_user.id,
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    durations: list[int] = []
    failed_count = 0
    for case in cases:
        started_at = perf_counter()
        answer: str | None = None
        sources: list[dict[str, Any]] = []
        error_message: str | None = None
        try:
            payload = answer_question(knowledge_base.collection_name, case.question)
            answer = str(payload.get("answer") or "")
            sources = _json_sources(payload.get("sources") or [])
        except HTTPException as exc:
            error_message = exc.detail if isinstance(exc.detail, str) else "问答服务返回错误"
            failed_count += 1
        except Exception:
            error_message = "问答服务暂时不可用"
            failed_count += 1

        elapsed_ms = round((perf_counter() - started_at) * 1000)
        durations.append(elapsed_ms)
        keyword_hits = [
            item for item in case.expected_answer_keywords if item.casefold() in (answer or "").casefold()
        ]
        source_hits = _matched_sources(
            case.expected_source_names, _source_names(sources)
        )
        result = EvaluationResult(
            run_id=run.id,
            case_id=case.id,
            question=case.question,
            expected_answer_keywords=list(case.expected_answer_keywords),
            expected_source_names=list(case.expected_source_names),
            answer=answer,
            sources=sources,
            answer_keyword_hits=keyword_hits,
            source_hits=source_hits,
            answer_hit=bool(answer) and len(keyword_hits) == len(case.expected_answer_keywords),
            source_hit=len(source_hits) > 0,
            response_time_ms=elapsed_ms,
            error_message=error_message,
        )
        db.add(result)
        run.completed_cases += 1
        if result.answer_hit:
            run.answer_hit_count += 1
        if result.source_hit:
            run.source_hit_count += 1
        db.commit()

    run.status = EvaluationRunStatus.COMPLETED.value
    run.average_response_time_ms = round(sum(durations) / len(durations), 2)
    run.error_message = f"{failed_count} 道题执行失败" if failed_count else None
    run.completed_at = utc_now()
    db.commit()
    db.refresh(run)
    return run


def list_runs(db: Session, dataset_id: int | None = None) -> list[EvaluationRun]:
    query = select(EvaluationRun)
    if dataset_id is not None:
        query = query.where(EvaluationRun.dataset_id == dataset_id)
    return db.scalars(query.order_by(EvaluationRun.created_at.desc()).limit(100)).all()


def get_run_detail(db: Session, run_id: int) -> dict[str, Any]:
    run = _get_run(db, run_id)
    return {
        **{column.name: getattr(run, column.name) for column in EvaluationRun.__table__.columns},
        "results": db.scalars(
            select(EvaluationResult)
            .where(EvaluationResult.run_id == run_id)
            .order_by(EvaluationResult.id.asc())
        ).all(),
    }


def review_result(
    db: Session,
    run_id: int,
    result_id: int,
    payload: EvaluationReviewUpdate,
    current_user: User,
) -> EvaluationResult:
    _get_run(db, run_id)
    result = db.scalar(
        select(EvaluationResult).where(
            EvaluationResult.id == result_id,
            EvaluationResult.run_id == run_id,
        )
    )
    if not result:
        raise HTTPException(status_code=404, detail="评估结果不存在")
    result.review_status = payload.review_status.value
    result.review_note = payload.review_note.strip() if payload.review_note else None
    result.reviewer_id = current_user.id
    result.reviewed_at = utc_now()
    db.commit()
    db.refresh(result)
    return result


def get_summary(db: Session) -> dict[str, Any]:
    latest = db.scalar(
        select(EvaluationRun)
        .where(EvaluationRun.status == EvaluationRunStatus.COMPLETED.value)
        .order_by(EvaluationRun.completed_at.desc())
        .limit(1)
    )
    return {
        "dataset_count": db.scalar(select(func.count(EvaluationDataset.id))) or 0,
        "case_count": db.scalar(select(func.count(EvaluationCase.id))) or 0,
        "completed_run_count": db.scalar(
            select(func.count(EvaluationRun.id)).where(
                EvaluationRun.status == EvaluationRunStatus.COMPLETED.value
            )
        ) or 0,
        "latest_answer_hit_rate": (
            round(latest.answer_hit_count / latest.total_cases * 100, 2)
            if latest and latest.total_cases
            else None
        ),
        "latest_source_hit_rate": (
            round(latest.source_hit_count / latest.total_cases * 100, 2)
            if latest and latest.total_cases
            else None
        ),
        "latest_average_response_time_ms": latest.average_response_time_ms if latest else None,
    }
