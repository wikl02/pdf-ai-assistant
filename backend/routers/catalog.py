from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.dependencies.auth import KnowledgeUser
from backend.schemas.management import KnowledgeBaseResponse
from backend.services.access_control_service import accessible_knowledge_base_ids
from backend.services.management_service import list_knowledge_bases


router = APIRouter(prefix="/api/knowledge-bases", tags=["knowledge-catalog"])


@router.get("", response_model=list[KnowledgeBaseResponse])
def get_accessible_knowledge_bases(
    current_user: KnowledgeUser,
    db: Annotated[Session, Depends(get_db)],
) -> list[KnowledgeBaseResponse]:
    allowed_ids = accessible_knowledge_base_ids(db, current_user)
    return [
        KnowledgeBaseResponse.model_validate(item)
        for item in list_knowledge_bases(db, allowed_ids)
    ]
