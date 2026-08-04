from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.auth import get_current_role, require_admin
from app.config import settings
from app.routers import auth as auth_router


def make_client(monkeypatch):
    monkeypatch.setattr(settings, "admin_password", "secret")
    monkeypatch.setattr(settings, "session_secret", "test-session-secret")
    monkeypatch.setattr(settings, "session_cookie_name", "apr_session")
    app = FastAPI()
    app.include_router(auth_router.router, prefix="/api")

    @app.post("/api/protected")
    def protected(_admin: str = Depends(require_admin)):
        return {"ok": True}

    @app.get("/api/role")
    def role(current_role: str = Depends(get_current_role)):
        return {"role": current_role}

    return TestClient(app)


def test_readers_can_check_current_role(monkeypatch):
    client = make_client(monkeypatch)

    response = client.get("/api/auth/me")

    assert response.status_code == 200
    assert response.json() == {"role": "reader"}


def test_readers_cannot_access_admin_endpoint(monkeypatch):
    client = make_client(monkeypatch)

    response = client.post("/api/protected")

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin privileges required"


def test_bad_admin_password_is_rejected(monkeypatch):
    client = make_client(monkeypatch)

    response = client.post("/api/auth/login", json={"password": "wrong"})

    assert response.status_code == 401


def test_admin_login_grants_access_and_logout_returns_to_reader(monkeypatch):
    client = make_client(monkeypatch)

    login = client.post("/api/auth/login", json={"password": "secret"})

    assert login.status_code == 200
    assert login.json() == {"role": "admin"}
    assert client.get("/api/role").json() == {"role": "admin"}
    assert client.post("/api/protected").status_code == 200

    logout = client.post("/api/auth/logout")

    assert logout.status_code == 200
    assert logout.json() == {"role": "reader"}
    assert client.get("/api/role").json() == {"role": "reader"}
    assert client.post("/api/protected").status_code == 403
