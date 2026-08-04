from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from backend.schemas.knowledge import SourceChunk


class ConversationCreate(BaseModel):
    knowledge_base_id: int
    title: str | None = Field(default=None, max_length=160)


class ConversationUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=160)


class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    conversation_id: int
    role: str
    content: str
    sources: list[SourceChunk] | None
    status: str
    response_time_ms: int | None
    created_at: datetime


class ConversationSummary(BaseModel):
    id: int
    user_id: int
    knowledge_base_id: int
    knowledge_base_name: str
    title: str
    message_count: int
    created_at: datetime
    updated_at: datetime


class ConversationDetail(ConversationSummary):
    messages: list[ChatMessageResponse]
