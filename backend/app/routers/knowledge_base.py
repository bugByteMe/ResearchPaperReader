from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import require_admin
from app.db import get_db
from app.schemas import DomainKnowledgeBaseOut, DomainKnowledgeBaseUpdate
from app.services.knowledge_base_service import get_or_create_knowledge_base


router = APIRouter(prefix="/knowledge-base", tags=["knowledge-base"])


@router.get("", response_model=DomainKnowledgeBaseOut)
def get_knowledge_base(db: Session = Depends(get_db), _admin: str = Depends(require_admin)):
    return get_or_create_knowledge_base(db)


@router.put("", response_model=DomainKnowledgeBaseOut)
def update_knowledge_base(payload: DomainKnowledgeBaseUpdate, db: Session = Depends(get_db), _admin: str = Depends(require_admin)):
    knowledge_base = get_or_create_knowledge_base(db)
    knowledge_base.content = payload.content
    db.commit()
    db.refresh(knowledge_base)
    return knowledge_base
