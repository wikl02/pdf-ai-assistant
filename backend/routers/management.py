from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.dependencies.auth import AdminUser
from backend.schemas.knowledge import UploadResponse
from backend.schemas.management import (
    DocumentResponse,
    DocumentUploadResponse,
    KnowledgeBaseCreate,
    KnowledgeBaseDetail,
    KnowledgeBaseResponse,
    MessageResponse,
)
from backend.services.management_service import (
    create_knowledge_base,
    delete_document,
    get_knowledge_base_detail,
    list_documents,
    list_knowledge_bases,
    reindex_document,
    upload_document,
)


router = APIRouter(prefix="/api/admin/knowledge-bases", tags=["admin-knowledge-bases"])
compatibility_router = APIRouter(tags=["knowledge"])


@router.get("", response_model=list[KnowledgeBaseResponse])
def get_knowledge_bases(
    _: AdminUser,
    db: Annotated[Session, Depends(get_db)],
) -> list[KnowledgeBaseResponse]:
    return [KnowledgeBaseResponse.model_validate(item) for item in list_knowledge_bases(db)]


@router.post("", response_model=KnowledgeBaseResponse, status_code=status.HTTP_201_CREATED)
def add_knowledge_base(
    payload: KnowledgeBaseCreate,
    current_user: AdminUser,
    db: Annotated[Session, Depends(get_db)],
) -> KnowledgeBaseResponse:
    knowledge_base = create_knowledge_base(db, payload, current_user)
    return KnowledgeBaseResponse.model_validate(knowledge_base)


@router.get("/{knowledge_base_id}", response_model=KnowledgeBaseDetail)
def get_knowledge_base(
    knowledge_base_id: int,
    _: AdminUser,
    db: Annotated[Session, Depends(get_db)],
) -> KnowledgeBaseDetail:
    return KnowledgeBaseDetail.model_validate(
        get_knowledge_base_detail(db, knowledge_base_id)
    )


@router.post(
    "/{knowledge_base_id}/documents",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_documents(
    knowledge_base_id: int,
    files: Annotated[list[UploadFile], File(...)],
    current_user: AdminUser,
    db: Annotated[Session, Depends(get_db)],
) -> DocumentUploadResponse:
    if not files:
        raise HTTPException(status_code=400, detail="请至少上传一个文档")
    documents = []
    for file in files:
        documents.append(
            upload_document(
                db,
                knowledge_base_id,
                current_user,
                file.filename or "document",
                await file.read(),
            )
        )
    detail = get_knowledge_base_detail(db, knowledge_base_id)
    return DocumentUploadResponse(
        knowledge_base_id=knowledge_base_id,
        collection_id=detail["collection_name"],
        documents=[DocumentResponse.model_validate(item) for item in documents],
        document_count=detail["document_count"],
        chunk_count=detail["chunk_count"],
    )


@router.get("/{knowledge_base_id}/documents", response_model=list[DocumentResponse])
def get_documents(
    knowledge_base_id: int,
    _: AdminUser,
    db: Annotated[Session, Depends(get_db)],
) -> list[DocumentResponse]:
    return [
        DocumentResponse.model_validate(document)
        for document in list_documents(db, knowledge_base_id)
    ]


@router.delete(
    "/{knowledge_base_id}/documents/{document_id}",
    response_model=MessageResponse,
)
def remove_document(
    knowledge_base_id: int,
    document_id: int,
    _: AdminUser,
    db: Annotated[Session, Depends(get_db)],
) -> MessageResponse:
    delete_document(db, knowledge_base_id, document_id)
    return MessageResponse(message="文档已删除，相关向量文本块已清理")


@router.post(
    "/{knowledge_base_id}/documents/{document_id}/reindex",
    response_model=DocumentResponse,
)
def rebuild_document_index(
    knowledge_base_id: int,
    document_id: int,
    _: AdminUser,
    db: Annotated[Session, Depends(get_db)],
) -> DocumentResponse:
    return DocumentResponse.model_validate(
        reindex_document(db, knowledge_base_id, document_id)
    )


@compatibility_router.post("/upload", response_model=UploadResponse)
@compatibility_router.post(
    "/api/knowledge/documents/upload",
    response_model=UploadResponse,
    include_in_schema=False,
)
async def compatibility_upload(
    files: Annotated[list[UploadFile], File(...)],
    current_user: AdminUser,
    db: Annotated[Session, Depends(get_db)],
) -> UploadResponse:
    if not files:
        raise HTTPException(status_code=400, detail="请至少上传一个文档")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    knowledge_base = create_knowledge_base(
        db,
        KnowledgeBaseCreate(
            name=f"Streamlit 上传 {timestamp}",
            description="由兼容上传接口自动创建",
        ),
        current_user,
    )
    documents = []
    for file in files:
        documents.append(
            upload_document(
                db,
                knowledge_base.id,
                current_user,
                file.filename or "document",
                await file.read(),
            )
        )
    return UploadResponse(
        collection_id=knowledge_base.collection_name,
        document_count=len(documents),
        chunk_count=sum(document.chunk_count for document in documents),
        documents=[
            {"name": item.filename, "type": item.file_type, "size": item.file_size}
            for item in documents
        ],
    )
