from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.dependencies.auth import KnowledgeUser
from backend.schemas.management import KnowledgeBaseResponse
from backend.services.management_service import list_knowledge_bases


router = APIRouter(prefix="/api/knowledge-bases", tags=["knowledge-catalog"])


@router.get("", response_model=list[KnowledgeBaseResponse])
def get_accessible_knowledge_bases(
    _: KnowledgeUser,
    db: Annotated[Session, Depends(get_db)],
) -> list[KnowledgeBaseResponse]:
    return [
        KnowledgeBaseResponse.model_validate(item)
        for item in list_knowledge_bases(db)
    ]
