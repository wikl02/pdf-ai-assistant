"""Authenticated users manage only their own persisted chat history."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.core.audit import audit_event
from backend.database import get_db
from backend.dependencies.auth import KnowledgeUser
from backend.schemas.chat import (
    ConversationCreate,
    ConversationDetail,
    ConversationSummary,
    ConversationUpdate,
)
from backend.schemas.management import MessageResponse
from backend.services.conversation_service import (
    create_conversation,
    delete_conversation,
    get_conversation_detail,
    list_conversations,
    rename_conversation,
)


router = APIRouter(prefix="/api/chat/conversations", tags=["chat-history"])


@router.get("", response_model=list[ConversationSummary])
def get_conversations(
    current_user: KnowledgeUser,
    db: Annotated[Session, Depends(get_db)],
    knowledge_base_id: int | None = None,
) -> list[ConversationSummary]:
    return [
        ConversationSummary.model_validate(item)
        for item in list_conversations(db, current_user, knowledge_base_id)
    ]


@router.post(
    "", response_model=ConversationSummary, status_code=status.HTTP_201_CREATED
)
def add_conversation(
    payload: ConversationCreate,
    current_user: KnowledgeUser,
    db: Annotated[Session, Depends(get_db)],
) -> ConversationSummary:
    conversation = create_conversation(db, current_user, payload)
    audit_event(
        "conversation_created",
        db=db,
        actor_id=current_user.id,
        actor_name=current_user.username,
        conversation_id=conversation.id,
        knowledge_base_id=conversation.knowledge_base_id,
    )
    return ConversationSummary.model_validate(
        get_conversation_detail(db, current_user, conversation.id)
    )


@router.get("/{conversation_id}", response_model=ConversationDetail)
def get_conversation(
    conversation_id: int,
    current_user: KnowledgeUser,
    db: Annotated[Session, Depends(get_db)],
) -> ConversationDetail:
    return ConversationDetail.model_validate(
        get_conversation_detail(db, current_user, conversation_id)
    )


@router.patch("/{conversation_id}", response_model=ConversationSummary)
def change_conversation(
    conversation_id: int,
    payload: ConversationUpdate,
    current_user: KnowledgeUser,
    db: Annotated[Session, Depends(get_db)],
) -> ConversationSummary:
    rename_conversation(db, current_user, conversation_id, payload.title)
    return ConversationSummary.model_validate(
        get_conversation_detail(db, current_user, conversation_id)
    )


@router.delete("/{conversation_id}", response_model=MessageResponse)
def remove_conversation(
    conversation_id: int,
    current_user: KnowledgeUser,
    db: Annotated[Session, Depends(get_db)],
) -> MessageResponse:
    delete_conversation(db, current_user, conversation_id)
    audit_event(
        "conversation_deleted",
        db=db,
        actor_id=current_user.id,
        actor_name=current_user.username,
        conversation_id=conversation_id,
    )
    return MessageResponse(message="会话已删除")
