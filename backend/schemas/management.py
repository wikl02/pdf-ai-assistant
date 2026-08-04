from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from backend.models.knowledge import DocumentStatus, IndexTaskStatus, IndexTaskTrigger


class KnowledgeBaseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)


class KnowledgeBaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    collection_name: str
    created_by_id: int
    document_count: int = 0
    chunk_count: int = 0
    created_at: datetime
    updated_at: datetime


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    file_type: str
    file_size: int
    sha256: str
    storage_path: str
    status: DocumentStatus
    chunk_count: int
    error_message: str | None
    current_version_number: int
    uploaded_by_id: int
    created_at: datetime
    updated_at: datetime


class KnowledgeBaseDetail(KnowledgeBaseResponse):
    documents: list[DocumentResponse]


class DocumentUploadResponse(BaseModel):
    knowledge_base_id: int
    collection_id: str
    documents: list[DocumentResponse]
    document_count: int
    chunk_count: int


class MessageResponse(BaseModel):
    message: str


class DocumentVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    version_number: int
    filename: str
    file_type: str
    file_size: int
    sha256: str
    status: DocumentStatus
    chunk_count: int
    error_message: str | None
    created_by_id: int | None
    created_at: datetime


class DocumentIndexTaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    knowledge_base_id: int
    version_number: int
    trigger: IndexTaskTrigger
    status: IndexTaskStatus
    chunk_count: int
    error_message: str | None
    duration_ms: int | None
    initiated_by_id: int | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


class DocumentLifecycleResponse(BaseModel):
    document: DocumentResponse
    versions: list[DocumentVersionResponse]
    index_tasks: list[DocumentIndexTaskResponse]
