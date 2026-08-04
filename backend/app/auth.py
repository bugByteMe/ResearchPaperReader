import base64
import hashlib
import hmac
import json
import time
from typing import Literal

from fastapi import Cookie, HTTPException, status

from app.config import settings


Role = Literal["admin", "reader"]


def _sign(value: str) -> str:
    return hmac.new(settings.session_secret.encode("utf-8"), value.encode("utf-8"), hashlib.sha256).hexdigest()


def _encode_payload(payload: dict[str, object]) -> str:
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _decode_payload(value: str) -> dict[str, object] | None:
    try:
        padded = value + "=" * (-len(value) % 4)
        raw = base64.urlsafe_b64decode(padded.encode("ascii"))
        return json.loads(raw.decode("utf-8"))
    except Exception:
        return None


def create_admin_session() -> str:
    payload = _encode_payload({"role": "admin", "exp": int(time.time()) + settings.session_max_age_seconds})
    return f"{payload}.{_sign(payload)}"


def get_current_role(apr_session: str | None = Cookie(default=None, alias=settings.session_cookie_name)) -> Role:
    if not apr_session or "." not in apr_session:
        return "reader"
    payload, signature = apr_session.rsplit(".", 1)
    if not hmac.compare_digest(_sign(payload), signature):
        return "reader"
    data = _decode_payload(payload)
    if not data or data.get("role") != "admin":
        return "reader"
    exp = data.get("exp")
    if not isinstance(exp, int) or exp < int(time.time()):
        return "reader"
    return "admin"


def require_admin(apr_session: str | None = Cookie(default=None, alias=settings.session_cookie_name)) -> Role:
    if get_current_role(apr_session) != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    return "admin"


def verify_admin_password(password: str) -> bool:
    if not settings.admin_password:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Admin password is not configured")
    return hmac.compare_digest(password, settings.admin_password)
