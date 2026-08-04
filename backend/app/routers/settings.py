from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import require_admin
from app.db import get_db
from app.models import AppSetting
from app.schemas import SettingOut, SettingUpdate
from app.services.settings_service import upsert_setting

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=list[SettingOut])
def list_settings(db: Session = Depends(get_db)) -> list[AppSetting]:
    return db.query(AppSetting).order_by(AppSetting.key).all()


@router.put("/{key}", response_model=SettingOut)
def update_setting(key: str, payload: SettingUpdate, db: Session = Depends(get_db), _admin: str = Depends(require_admin)) -> AppSetting:
    if key not in {"knowledge_base_auto_update_enabled"}:
        raise HTTPException(status_code=410, detail="Use the workspace settings endpoint")
    return upsert_setting(db, key, payload.value)
