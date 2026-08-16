import logging
from time import perf_counter
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.core.audit import audit_event
from backend.database import get_db
from backend.dependencies.auth import AdminUser, KnowledgeUser
from backend.schemas.knowledge import AskRequest, AskResponse, UploadResponse
from backend.services.access_control_service import require_collection_permission
from backend.services.conversation_service import (
    add_assistant_message,
    add_user_message,
    get_or_create_conversation,
)
from backend.services.knowledge_service import (
    answer_question,
    build_file_info,
    build_knowledge_base,
)


logger = logging.getLogger("pdf_ai_assistant.knowledge.router")
router = APIRouter(tags=["knowledge"])


@router.post("/api/knowledge/documents/upload", response_model=UploadResponse)
@router.post("/upload", response_model=UploadResponse, include_in_schema=False)
async def upload_documents(
    files: Annotated[list[UploadFile], File(...)],
    current_user: AdminUser,
    db: Annotated[Session, Depends(get_db)],
) -> UploadResponse:
    if not files:
        raise HTTPException(status_code=400, detail="请至少上传一个文件")
    file_infos = []
    for file in files:
        file_infos.append(build_file_info(file.filename or "", await file.read()))
    result = UploadResponse.model_validate(build_knowledge_base(file_infos))
    audit_event(
        "compatibility_upload",
        db=db,
        actor_id=current_user.id,
        actor_name=current_user.username,
        collection_id=result.collection_id,
        file_count=len(file_infos),
        total_bytes=sum(item["size"] for item in file_infos),
        chunk_count=result.chunk_count,
    )
    return result


@router.post("/api/chat/ask", response_model=AskResponse)
@router.post("/ask", response_model=AskResponse, include_in_schema=False)
def ask_question(
    request: AskRequest,
    current_user: KnowledgeUser,
    db: Annotated[Session, Depends(get_db)],
) -> AskResponse:
    knowledge_base = require_collection_permission(
        db, current_user, request.collection_id
    )
    conversation = get_or_create_conversation(
        db,
        current_user,
        knowledge_base,
        request.conversation_id,
    )
    user_message = add_user_message(db, conversation, request.question)
    started_at = perf_counter()
    try:
        result = AskResponse.model_validate(
            answer_question(request.collection_id, request.question)
        )
    except HTTPException as exc:
        elapsed_ms = round((perf_counter() - started_at) * 1000)
        failure_text = exc.detail if isinstance(exc.detail, str) else "回答生成失败"
        add_assistant_message(
            db,
            conversation,
            failure_text,
            sources=None,
            response_time_ms=elapsed_ms,
            status="failed",
        )
        audit_event(
            "question_answered",
            db=db,
            outcome="failed",
            actor_id=current_user.id,
            actor_name=current_user.username,
            conversation_id=conversation.id,
            knowledge_base_id=knowledge_base.id,
            response_time_ms=elapsed_ms,
            error_status=exc.status_code,
        )
        raise
    except Exception:
        elapsed_ms = round((perf_counter() - started_at) * 1000)
        failure_text = "AI 服务暂时不可用，请稍后重试。"
        logger.exception(
            "Unexpected question answering failure: user_id=%s conversation_id=%s",
            current_user.id,
            conversation.id,
        )
        add_assistant_message(
            db,
            conversation,
            failure_text,
            sources=None,
            response_time_ms=elapsed_ms,
            status="failed",
        )
        audit_event(
            "question_answered",
            db=db,
            outcome="failed",
            actor_id=current_user.id,
            actor_name=current_user.username,
            conversation_id=conversation.id,
            knowledge_base_id=knowledge_base.id,
            response_time_ms=elapsed_ms,
            error_status=500,
        )
        raise HTTPException(status_code=503, detail=failure_text) from None

    elapsed_ms = round((perf_counter() - started_at) * 1000)
    assistant_message = add_assistant_message(
        db,
        conversation,
        result.answer,
        sources=[source.model_dump(mode="json") for source in result.sources],
        response_time_ms=elapsed_ms,
        llm_model=result.llm_model,
        prompt_tokens=result.prompt_tokens,
        completion_tokens=result.completion_tokens,
        total_tokens=result.total_tokens,
    )
    audit_event(
        "question_answered",
        db=db,
        actor_id=current_user.id,
        actor_name=current_user.username,
        conversation_id=conversation.id,
        knowledge_base_id=knowledge_base.id,
        collection_id=request.collection_id,
        question_length=len(request.question.strip()),
        source_count=len(result.sources),
        response_time_ms=elapsed_ms,
        llm_model=result.llm_model,
        prompt_tokens=result.prompt_tokens,
        completion_tokens=result.completion_tokens,
        total_tokens=result.total_tokens,
    )
    return result.model_copy(
        update={
            "conversation_id": conversation.id,
            "user_message_id": user_message.id,
            "assistant_message_id": assistant_message.id,
        }
    )
