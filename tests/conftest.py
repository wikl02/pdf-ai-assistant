from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.core.security import hash_password
from backend.database import Base, get_db
from backend.main import app
from backend.models import User, UserRole
from backend.services import management_service


@pytest.fixture()
def api(tmp_path, monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(engine)

    with TestingSession() as db:
        db.add_all(
            [
                User(
                    username="admin",
                    password_hash=hash_password("Admin123!"),
                    display_name="Administrator",
                    role=UserRole.ADMIN.value,
                    is_active=True,
                ),
                User(
                    username="member",
                    password_hash=hash_password("Member123!"),
                    display_name="Member",
                    role=UserRole.USER.value,
                    is_active=True,
                ),
            ]
        )
        db.commit()

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    vector_chunks: dict[str, dict[int, list[dict]]] = {}

    def fake_index(collection_name: str, document_id: int, chunks: list[dict]):
        vector_chunks.setdefault(collection_name, {})[document_id] = chunks

    def fake_delete(collection_name: str, document_id: int):
        vector_chunks.setdefault(collection_name, {}).pop(document_id, None)

    app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setattr(
        management_service,
        "settings",
        SimpleNamespace(upload_storage_dir=tmp_path / "uploads"),
    )
    monkeypatch.setattr(management_service, "index_document_chunks", fake_index)
    monkeypatch.setattr(management_service, "delete_document_chunks", fake_delete)

    client = TestClient(app)
    yield SimpleNamespace(
        client=client,
        session_factory=TestingSession,
        vector_chunks=vector_chunks,
        upload_dir=tmp_path / "uploads",
    )
    client.close()
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)


def login_headers(client: TestClient, username: str, password: str) -> dict[str, str]:
    response = client.post(
        "/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}
