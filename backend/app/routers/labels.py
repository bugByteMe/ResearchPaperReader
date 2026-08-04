from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import require_admin
from app.db import get_db
from app.models import LabelDefinition, PaperLabel
from app.schemas import LabelDefinitionCreate, LabelDefinitionOut, LabelDefinitionUpdate

router = APIRouter(prefix="/labels", tags=["labels"])


@router.get("", response_model=list[LabelDefinitionOut])
def list_labels(type: str | None = None, db: Session = Depends(get_db)) -> list[LabelDefinition]:
    query = db.query(LabelDefinition)
    if type:
        query = query.filter(LabelDefinition.type == type)
    return query.order_by(LabelDefinition.type, LabelDefinition.name).all()


@router.post("", response_model=LabelDefinitionOut)
def create_label(payload: LabelDefinitionCreate, db: Session = Depends(get_db), _admin: str = Depends(require_admin)) -> LabelDefinition:
    if payload.type not in {"category", "tech_route"}:
        raise HTTPException(status_code=400, detail="type must be category or tech_route")
    label = LabelDefinition(type=payload.type, name=payload.name, description=payload.description)
    db.add(label)
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail="Label already exists or is invalid") from exc
    db.refresh(label)
    return label


@router.patch("/{label_id}", response_model=LabelDefinitionOut)
def update_label(label_id: int, payload: LabelDefinitionUpdate, db: Session = Depends(get_db), _admin: str = Depends(require_admin)) -> LabelDefinition:
    label = db.get(LabelDefinition, label_id)
    if not label:
        raise HTTPException(status_code=404, detail="Label not found")
    if payload.name is not None:
        label.name = payload.name
    if payload.description is not None:
        label.description = payload.description
    db.commit()
    db.refresh(label)
    return label


@router.delete("/{label_id}")
def delete_label(label_id: int, db: Session = Depends(get_db), _admin: str = Depends(require_admin)) -> dict[str, str]:
    label = db.get(LabelDefinition, label_id)
    if not label:
        raise HTTPException(status_code=404, detail="Label not found")
    db.query(PaperLabel).filter(PaperLabel.label_id == label_id).delete()
    db.delete(label)
    db.commit()
    return {"message": "deleted"}
