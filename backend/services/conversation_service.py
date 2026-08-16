"""Ownership-safe persistence for chat conversations and messages."""

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.models.activity import ChatConversation, ChatMessage
from backend.models.knowledge import KnowledgeBase
from backend.models.user import User
from backend.schemas.chat import ConversationCreate
from backend.services.access_control_service import (
    accessible_knowledge_base_ids,
    require_knowledge_base_permission,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _owned_conversation_or_404(
    db: Session, user: User, conversation_id: int
) -> ChatConversation:
    conversation = db.scalar(
        select(ChatConversation).where(
            ChatConversation.id == conversation_id,
            ChatConversation.user_id == user.id,
        )
    )
    if not conversation:
        raise HTTPException(status_code=404, detail="会话不存在")
    return conversation


def create_conversation(
    db: Session, user: User, payload: ConversationCreate
) -> ChatConversation:
    require_knowledge_base_permission(db, user, payload.knowledge_base_id)
    title = payload.title.strip() if payload.title else "新会话"
    conversation = ChatConversation(
        user_id=user.id,
        knowledge_base_id=payload.knowledge_base_id,
        title=title,
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def get_or_create_conversation(
    db: Session,
    user: User,
    knowledge_base: KnowledgeBase,
    conversation_id: int | None,
) -> ChatConversation:
    if conversation_id is None:
        return create_conversation(
            db,
            user,
            ConversationCreate(knowledge_base_id=knowledge_base.id),
        )
    conversation = _owned_conversation_or_404(db, user, conversation_id)
    if conversation.knowledge_base_id != knowledge_base.id:
        raise HTTPException(status_code=400, detail="会话与当前知识库不匹配")
    require_knowledge_base_permission(db, user, conversation.knowledge_base_id)
    return conversation


def list_conversations(
    db: Session, user: User, knowledge_base_id: int | None = None
) -> list[dict]:
    allowed_ids = accessible_knowledge_base_ids(db, user)
    message_count = (
        select(func.count(ChatMessage.id))
        .where(ChatMessage.conversation_id == ChatConversation.id)
        .correlate(ChatConversation)
        .scalar_subquery()
    )
    statement = (
        select(ChatConversation, KnowledgeBase.name, message_count)
        .join(KnowledgeBase, KnowledgeBase.id == ChatConversation.knowledge_base_id)
        .where(ChatConversation.user_id == user.id)
    )
    if allowed_ids is not None:
        if not allowed_ids:
            return []
        statement = statement.where(ChatConversation.knowledge_base_id.in_(allowed_ids))
    if knowledge_base_id is not None:
        require_knowledge_base_permission(db, user, knowledge_base_id)
        statement = statement.where(ChatConversation.knowledge_base_id == knowledge_base_id)
    rows = db.execute(statement.order_by(ChatConversation.updated_at.desc())).all()
    return [
        {
            "id": conversation.id,
            "user_id": conversation.user_id,
            "knowledge_base_id": conversation.knowledge_base_id,
            "knowledge_base_name": knowledge_base_name,
            "title": conversation.title,
            "message_count": count,
            "created_at": conversation.created_at,
            "updated_at": conversation.updated_at,
        }
        for conversation, knowledge_base_name, count in rows
    ]


def get_conversation_detail(db: Session, user: User, conversation_id: int) -> dict:
    conversation = _owned_conversation_or_404(db, user, conversation_id)
    require_knowledge_base_permission(db, user, conversation.knowledge_base_id)
    knowledge_base = db.get(KnowledgeBase, conversation.knowledge_base_id)
    messages = list(
        db.scalars(
            select(ChatMessage)
            .where(ChatMessage.conversation_id == conversation.id)
            .order_by(ChatMessage.created_at, ChatMessage.id)
        )
    )
    return {
        "id": conversation.id,
        "user_id": conversation.user_id,
        "knowledge_base_id": conversation.knowledge_base_id,
        "knowledge_base_name": knowledge_base.name,
        "title": conversation.title,
        "message_count": len(messages),
        "created_at": conversation.created_at,
        "updated_at": conversation.updated_at,
        "messages": messages,
    }


def rename_conversation(
    db: Session, user: User, conversation_id: int, title: str
) -> ChatConversation:
    conversation = _owned_conversation_or_404(db, user, conversation_id)
    conversation.title = title.strip()
    conversation.updated_at = utc_now()
    db.commit()
    db.refresh(conversation)
    return conversation


def delete_conversation(db: Session, user: User, conversation_id: int) -> None:
    conversation = _owned_conversation_or_404(db, user, conversation_id)
    db.delete(conversation)
    db.commit()


def add_user_message(
    db: Session, conversation: ChatConversation, content: str
) -> ChatMessage:
    message = ChatMessage(
        conversation_id=conversation.id,
        role="user",
        content=content.strip(),
        status="complete",
    )
    if conversation.title == "新会话":
        conversation.title = content.strip()[:60]
    conversation.updated_at = utc_now()
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def add_assistant_message(
    db: Session,
    conversation: ChatConversation,
    content: str,
    *,
    sources: list[dict] | None,
    response_time_ms: int,
    status: str = "complete",
    llm_model: str | None = None,
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
    total_tokens: int | None = None,
) -> ChatMessage:
    message = ChatMessage(
        conversation_id=conversation.id,
        role="assistant",
        content=content,
        sources=sources,
        status=status,
        response_time_ms=response_time_ms,
        llm_model=llm_model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
    )
    conversation.updated_at = utc_now()
    db.add(message)
    db.commit()
    db.refresh(message)
    return message
