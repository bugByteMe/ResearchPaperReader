from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import require_admin
from app.db import get_db
from app.models import Prompt
from app.schemas import PromptOut, PromptUpdate
from app.seed import PROMPT_TYPES as DEFAULT_PROMPT_TYPES

router = APIRouter(prefix="/prompts", tags=["prompts"])

SUPPORTED_PROMPT_TYPES = set(DEFAULT_PROMPT_TYPES)


@router.get("", response_model=list[PromptOut])
def list_prompts(db: Session = Depends(get_db), _admin: str = Depends(require_admin)) -> list[Prompt]:
    return db.query(Prompt).filter(Prompt.is_active.is_(True)).order_by(Prompt.type).all()


@router.put("/{prompt_type}", response_model=PromptOut)
def update_prompt(prompt_type: str, payload: PromptUpdate, db: Session = Depends(get_db), _admin: str = Depends(require_admin)) -> Prompt:
    if prompt_type not in SUPPORTED_PROMPT_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported prompt_type")
    prompt = db.query(Prompt).filter(Prompt.type == prompt_type, Prompt.is_active.is_(True)).first()
    if not prompt:
        prompt = Prompt(type=prompt_type, content=payload.content, is_active=True)
        db.add(prompt)
    else:
        prompt.content = payload.content
    db.commit()
    db.refresh(prompt)
    return prompt
