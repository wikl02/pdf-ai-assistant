from pathlib import Path

from backend.models import User, UserRole
from tests.conftest import login_headers


def test_regular_user_cannot_access_admin_endpoints(api):
    headers = login_headers(api.client, "member", "Member123!")

    assert api.client.get("/api/admin/knowledge-bases", headers=headers).status_code == 403
    assert api.client.get("/api/admin/users", headers=headers).status_code == 403


def test_knowledge_base_document_lifecycle_and_precise_vector_delete(api):
    headers = login_headers(api.client, "admin", "Admin123!")
    created = api.client.post(
        "/api/admin/knowledge-bases",
        headers=headers,
        json={"name": "产品知识库", "description": "测试知识库"},
    )
    assert created.status_code == 201, created.text
    knowledge_base = created.json()
    knowledge_base_id = knowledge_base["id"]
    collection_name = knowledge_base["collection_name"]

    uploaded = api.client.post(
        f"/api/admin/knowledge-bases/{knowledge_base_id}/documents",
        headers=headers,
        files=[
            ("files", ("faq.txt", b"refund policy is seven days", "text/plain")),
            ("files", ("manual.txt", b"support email is help@example.com", "text/plain")),
        ],
    )
    assert uploaded.status_code == 201, uploaded.text
    documents = uploaded.json()["documents"]
    assert len(documents) == 2
    assert all(document["status"] == "ready" for document in documents)
    assert all(Path(document["storage_path"]).is_file() for document in documents)
    assert set(api.vector_chunks[collection_name]) == {item["id"] for item in documents}

    first_id, second_id = documents[0]["id"], documents[1]["id"]
    deleted = api.client.delete(
        f"/api/admin/knowledge-bases/{knowledge_base_id}/documents/{first_id}",
        headers=headers,
    )
    assert deleted.status_code == 200, deleted.text
    assert first_id not in api.vector_chunks[collection_name]
    assert second_id in api.vector_chunks[collection_name]

    listed = api.client.get(
        f"/api/admin/knowledge-bases/{knowledge_base_id}/documents",
        headers=headers,
    )
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [second_id]

    reindexed = api.client.post(
        f"/api/admin/knowledge-bases/{knowledge_base_id}/documents/{second_id}/reindex",
        headers=headers,
    )
    assert reindexed.status_code == 200, reindexed.text
    assert reindexed.json()["status"] == "ready"


def test_compatibility_upload_keeps_streamlit_response_shape(api):
    headers = login_headers(api.client, "admin", "Admin123!")
    response = api.client.post(
        "/upload",
        headers=headers,
        files={"files": ("legacy.txt", b"legacy streamlit content", "text/plain")},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert set(payload) == {"collection_id", "document_count", "chunk_count", "documents"}
    assert payload["document_count"] == 1
    assert payload["documents"][0]["name"] == "legacy.txt"


def test_admin_user_management(api):
    headers = login_headers(api.client, "admin", "Admin123!")
    created = api.client.post(
        "/api/admin/users",
        headers=headers,
        json={
            "username": "analyst",
            "password": "Analyst123!",
            "display_name": "Analyst",
            "role": "user",
        },
    )
    assert created.status_code == 201, created.text
    user_id = created.json()["id"]

    role_changed = api.client.patch(
        f"/api/admin/users/{user_id}/role",
        headers=headers,
        json={"role": "admin"},
    )
    assert role_changed.status_code == 200
    assert role_changed.json()["role"] == "admin"

    disabled = api.client.patch(
        f"/api/admin/users/{user_id}/status",
        headers=headers,
        json={"is_active": False},
    )
    assert disabled.status_code == 200
    assert disabled.json()["is_active"] is False

    enabled = api.client.patch(
        f"/api/admin/users/{user_id}/status",
        headers=headers,
        json={"is_active": True},
    )
    assert enabled.status_code == 200

    reset = api.client.post(
        f"/api/admin/users/{user_id}/reset-password",
        headers=headers,
        json={"password": "Changed123!"},
    )
    assert reset.status_code == 200
    assert login_headers(api.client, "analyst", "Changed123!")

    with api.session_factory() as db:
        user = db.get(User, user_id)
        assert user.role == UserRole.ADMIN.value
