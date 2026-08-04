from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import require_admin
from app.db import get_db
from app.schemas import SetupRequest, WorkspaceOut, WorkspaceUpdate
from app.services.workspace_service import create_workspace, get_workspace, update_workspace

router = APIRouter(prefix="/workspace", tags=["workspace"])


@router.get("", response_model=WorkspaceOut | None)
def read_workspace(db: Session = Depends(get_db)):
    return get_workspace(db)


@router.post("/setup", response_model=WorkspaceOut)
def setup_workspace(payload: SetupRequest, db: Session = Depends(get_db), _admin: str = Depends(require_admin)):
    try:
        return create_workspace(
            db, **payload.model_dump(exclude={"knowledge_base", "labels"}), knowledge_base=payload.knowledge_base,
            labels=[(label.type, label.name, label.description) for label in payload.labels],
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("", response_model=WorkspaceOut)
def edit_workspace(payload: WorkspaceUpdate, db: Session = Depends(get_db), _admin: str = Depends(require_admin)):
    workspace = get_workspace(db)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace has not been configured")
    try:
        return update_workspace(db, workspace, **payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
