import logging
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile

from backend.core.audit import audit_event
from backend.dependencies.auth import AdminUser, KnowledgeUser
from backend.schemas.knowledge import AskRequest, AskResponse, UploadResponse
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
) -> UploadResponse:
    if not files:
        raise HTTPException(status_code=400, detail="请至少上传一个文件")
    file_infos = []
    for file in files:
        file_infos.append(build_file_info(file.filename or "", await file.read()))
    result = UploadResponse.model_validate(build_knowledge_base(file_infos))
    audit_event(
        "compatibility_upload",
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
def ask_question(request: AskRequest, current_user: KnowledgeUser) -> AskResponse:
    result = AskResponse.model_validate(
        answer_question(request.collection_id, request.question)
    )
    audit_event(
        "question_answered",
        actor_id=current_user.id,
        actor_name=current_user.username,
        collection_id=request.collection_id,
        question_length=len(request.question.strip()),
        source_count=len(result.sources),
    )
    return result
