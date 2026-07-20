import logging

from backend.routers import health
from tests.conftest import login_headers


def test_sensitive_endpoints_require_authentication(api):
    checks = [
        ("get", "/api/auth/me", None),
        ("get", "/api/admin/users", None),
        ("get", "/api/admin/knowledge-bases", None),
        ("get", "/api/knowledge-bases", None),
        ("post", "/api/chat/ask", {"collection_id": "test", "question": "hello"}),
    ]

    for method, path, payload in checks:
        kwargs = {"json": payload} if payload is not None else {}
        response = getattr(api.client, method)(path, **kwargs)
        assert response.status_code == 401, (method, path, response.text)


def test_compatibility_upload_requires_admin(api):
    headers = login_headers(api.client, "member", "Member123!")
    response = api.client.post(
        "/upload",
        headers=headers,
        files={"files": ("note.txt", b"protected", "text/plain")},
    )
    assert response.status_code == 403


def test_readiness_reports_database_and_chroma(api, monkeypatch):
    monkeypatch.setattr(health, "_database_status", lambda: "ok")
    monkeypatch.setattr(health, "_chroma_status", lambda: "ok")

    response = api.client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "components": {"database": "ok", "chroma": "ok"},
    }


def test_readiness_returns_503_when_a_dependency_fails(api, monkeypatch):
    def failed_check():
        raise RuntimeError("unavailable")

    monkeypatch.setattr(health, "_database_status", lambda: "ok")
    monkeypatch.setattr(health, "_chroma_status", failed_check)

    response = api.client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "degraded"
    assert response.json()["components"] == {"database": "ok", "chroma": "error"}


def test_login_audit_does_not_log_password_or_token(api, caplog):
    caplog.set_level(logging.INFO, logger="pdf_ai_assistant.audit")

    failed = api.client.post(
        "/login",
        json={"username": "admin", "password": "WrongPassword123!"},
    )
    assert failed.status_code == 401

    login_headers(api.client, "admin", "Admin123!")

    assert "event=login outcome=failed" in caplog.text
    assert "event=login outcome=success" in caplog.text
    assert "WrongPassword123!" not in caplog.text
    assert "Admin123!" not in caplog.text
    assert "access_token" not in caplog.text
