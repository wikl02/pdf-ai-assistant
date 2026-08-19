import asyncio
import logging
from time import perf_counter
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.core.audit import audit_event
from backend.database import get_db
from backend.dependencies.auth import AdminUser, KnowledgeUser
from backend.schemas.knowledge import (
    AskRequest,
    AskResponse,
    CancelQuestionResponse,
    UploadResponse,
)
from backend.services.access_control_service import require_collection_permission
from backend.services.conversation_service import (
    add_assistant_message,
    add_user_message,
    get_or_create_conversation,
)
from backend.services.knowledge_service import (
    answer_question_async,
    build_file_info,
    build_knowledge_base,
)
from backend.services.question_task_service import (
    cancel_question_task,
    complete_question_task,
    is_question_task_active,
    register_question_task,
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
async def ask_question(
    request: AskRequest,
    current_user: KnowledgeUser,
    db: Annotated[Session, Depends(get_db)],
) -> AskResponse:
    request_id = request.request_id or uuid4().hex
    if is_question_task_active(current_user.id, request_id):
        raise HTTPException(status_code=409, detail="该问题正在处理中，请勿重复提交")

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
    answer_task = asyncio.create_task(
        answer_question_async(request.collection_id, request.question)
    )
    task_entry = register_question_task(
        current_user.id,
        request_id,
        answer_task,
        conversation_id=conversation.id,
        user_message_id=user_message.id,
    )
    try:
        result = AskResponse.model_validate(
            await answer_task
        )
    except asyncio.CancelledError:
        elapsed_ms = round((perf_counter() - started_at) * 1000)
        cancelled_message = add_assistant_message(
            db,
            conversation,
            "回答已停止。",
            sources=None,
            response_time_ms=elapsed_ms,
            status="cancelled",
        )
        task_entry.assistant_message_id = cancelled_message.id
        audit_event(
            "question_answered",
            db=db,
            outcome="cancelled",
            actor_id=current_user.id,
            actor_name=current_user.username,
            conversation_id=conversation.id,
            knowledge_base_id=knowledge_base.id,
            request_id=request_id,
            response_time_ms=elapsed_ms,
        )
        complete_question_task(
            current_user.id,
            request_id,
            answer_task,
            assistant_message_id=cancelled_message.id,
        )
        raise HTTPException(status_code=409, detail="回答已停止") from None
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
            request_id=request_id,
            response_time_ms=elapsed_ms,
            error_status=exc.status_code,
        )
        complete_question_task(current_user.id, request_id, answer_task)
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
            request_id=request_id,
            response_time_ms=elapsed_ms,
            error_status=500,
        )
        complete_question_task(current_user.id, request_id, answer_task)
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
        request_id=request_id,
        question_length=len(request.question.strip()),
        source_count=len(result.sources),
        response_time_ms=elapsed_ms,
        llm_model=result.llm_model,
        prompt_tokens=result.prompt_tokens,
        completion_tokens=result.completion_tokens,
        total_tokens=result.total_tokens,
    )
    complete_question_task(
        current_user.id,
        request_id,
        answer_task,
        assistant_message_id=assistant_message.id,
    )
    return result.model_copy(
        update={
            "conversation_id": conversation.id,
            "user_message_id": user_message.id,
            "assistant_message_id": assistant_message.id,
        }
    )


@router.post(
    "/api/chat/requests/{request_id}/cancel",
    response_model=CancelQuestionResponse,
)
async def cancel_question(
    request_id: str,
    current_user: KnowledgeUser,
    db: Annotated[Session, Depends(get_db)],
) -> CancelQuestionResponse:
    if not 8 <= len(request_id) <= 64:
        raise HTTPException(status_code=422, detail="请求编号格式无效")
    result = await cancel_question_task(current_user.id, request_id)
    audit_event(
        "question_cancel_requested",
        db=db,
        outcome="success" if result["cancelled"] else "ignored",
        actor_id=current_user.id,
        actor_name=current_user.username,
        request_id=request_id,
        conversation_id=result.get("conversation_id"),
    )
    return CancelQuestionResponse.model_validate(result)
