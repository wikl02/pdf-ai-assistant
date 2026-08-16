from typing import Any

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    collection_id: str = Field(min_length=1, max_length=255)
    question: str = Field(min_length=1, max_length=5000)
    conversation_id: int | None = None


class SourceChunk(BaseModel):
    text: str
    metadata: dict[str, Any]
    score: float


class AskResponse(BaseModel):
    answer: str
    sources: list[SourceChunk]
    conversation_id: int | None = None
    user_message_id: int | None = None
    assistant_message_id: int | None = None
    llm_model: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None


class UploadedDocument(BaseModel):
    name: str
    type: str
    size: int


class UploadResponse(BaseModel):
    collection_id: str
    document_count: int
    chunk_count: int
    documents: list[UploadedDocument]
