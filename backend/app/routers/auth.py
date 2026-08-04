from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.auth import create_admin_session, get_current_role, verify_admin_password
from app.config import settings
from app.schemas import CurrentUserOut, LoginRequest


router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me", response_model=CurrentUserOut)
def me(role: str = Depends(get_current_role)) -> CurrentUserOut:
    return CurrentUserOut(role=role)


@router.post("/login", response_model=CurrentUserOut)
def login(payload: LoginRequest, response: Response) -> CurrentUserOut:
    if not verify_admin_password(payload.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin password")
    response.set_cookie(
        key=settings.session_cookie_name,
        value=create_admin_session(),
        max_age=settings.session_max_age_seconds,
        httponly=True,
        samesite="lax",
        secure=settings.session_cookie_secure,
    )
    return CurrentUserOut(role="admin")


@router.post("/logout", response_model=CurrentUserOut)
def logout(response: Response) -> CurrentUserOut:
    response.delete_cookie(key=settings.session_cookie_name, httponly=True, samesite="lax", secure=settings.session_cookie_secure)
    return CurrentUserOut(role="reader")
