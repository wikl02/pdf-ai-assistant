from pathlib import Path

from backend.models.knowledge import (
    Document,
    DocumentIndexTask,
    DocumentStatus,
    IndexTaskStatus,
    IndexTaskTrigger,
)

from backend.services import management_service
from tests.conftest import login_headers


def _create_knowledge_base(api, headers, name="Lifecycle KB"):
    response = api.client.post(
        "/api/admin/knowledge-bases",
        headers=headers,
        json={"name": name, "description": "Document lifecycle tests"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_document_versions_and_index_tasks_are_recorded(api):
    headers = login_headers(api.client, "admin", "Admin123!")
    knowledge_base = _create_knowledge_base(api, headers)
    base_url = f"/api/admin/knowledge-bases/{knowledge_base['id']}/documents"

    uploaded = api.client.post(
        base_url,
        headers=headers,
        files={"files": ("handbook.txt", b"version one content", "text/plain")},
    )
    assert uploaded.status_code == 201, uploaded.text
    document = uploaded.json()["documents"][0]
    document_id = document["id"]
    first_path = Path(document["storage_path"])
    assert document["current_version_number"] == 1

    reindexed = api.client.post(
        f"{base_url}/{document_id}/reindex", headers=headers
    )
    assert reindexed.status_code == 200, reindexed.text

    versioned = api.client.post(
        f"{base_url}/{document_id}/versions",
        headers=headers,
        files={"file": ("handbook.txt", b"version two changed content", "text/plain")},
    )
    assert versioned.status_code == 200, versioned.text
    assert versioned.json()["current_version_number"] == 2
    second_path = Path(versioned.json()["storage_path"])
    assert first_path.is_file()
    assert second_path.is_file()

    lifecycle = api.client.get(
        f"{base_url}/{document_id}/lifecycle", headers=headers
    )
    assert lifecycle.status_code == 200, lifecycle.text
    payload = lifecycle.json()
    assert [item["version_number"] for item in payload["versions"]] == [2, 1]
    assert [item["trigger"] for item in payload["index_tasks"]] == [
        "version_upload",
        "reindex",
        "upload",
    ]
    assert all(item["status"] == "succeeded" for item in payload["index_tasks"])
    assert all(item["duration_ms"] is not None for item in payload["index_tasks"])

    deleted = api.client.delete(f"{base_url}/{document_id}", headers=headers)
    assert deleted.status_code == 200, deleted.text
    assert not first_path.exists()
    assert not second_path.exists()


def test_failed_index_keeps_failure_reason_and_task(api, monkeypatch):
    headers = login_headers(api.client, "admin", "Admin123!")
    knowledge_base = _create_knowledge_base(api, headers, "Failed Lifecycle KB")
    base_url = f"/api/admin/knowledge-bases/{knowledge_base['id']}/documents"

    def fail_index(*args, **kwargs):
        raise RuntimeError("embedding service unavailable")

    monkeypatch.setattr(management_service, "index_document_chunks", fail_index)
    uploaded = api.client.post(
        base_url,
        headers=headers,
        files={"files": ("broken.txt", b"index failure content", "text/plain")},
    )
    assert uploaded.status_code == 400
    documents = api.client.get(base_url, headers=headers).json()
    assert len(documents) == 1
    assert documents[0]["status"] == "failed"

    lifecycle = api.client.get(
        f"{base_url}/{documents[0]['id']}/lifecycle", headers=headers
    ).json()
    assert lifecycle["versions"][0]["status"] == "failed"
    assert "embedding service unavailable" in lifecycle["versions"][0]["error_message"]
    assert lifecycle["index_tasks"][0]["status"] == "failed"
    assert lifecycle["index_tasks"][0]["duration_ms"] is not None


def test_startup_recovery_marks_unfinished_reindex_as_interrupted(api):
    headers = login_headers(api.client, "admin", "Admin123!")
    knowledge_base = _create_knowledge_base(api, headers, "Interrupted Lifecycle KB")
    base_url = f"/api/admin/knowledge-bases/{knowledge_base['id']}/documents"
    uploaded = api.client.post(
        base_url,
        headers=headers,
        files={"files": ("policy.txt", b"existing searchable content", "text/plain")},
    )
    document = uploaded.json()["documents"][0]

    with api.session_factory() as db:
        stored_document = db.get(Document, document["id"])
        stored_document.status = DocumentStatus.PROCESSING.value
        db.add(
            DocumentIndexTask(
                document_id=document["id"],
                knowledge_base_id=knowledge_base["id"],
                version_number=1,
                trigger=IndexTaskTrigger.REINDEX.value,
                status=IndexTaskStatus.PROCESSING.value,
                started_at=management_service.datetime.now(
                    management_service.timezone.utc
                ),
            )
        )
        db.commit()
        assert management_service.recover_interrupted_index_tasks(db) == 1

    lifecycle = api.client.get(
        f"{base_url}/{document['id']}/lifecycle", headers=headers
    ).json()
    assert lifecycle["document"]["status"] == "ready"
    assert lifecycle["index_tasks"][0]["status"] == "interrupted"
    assert "服务重启前任务未正常结束" in lifecycle["index_tasks"][0]["error_message"]


def test_second_index_request_is_rejected_while_a_task_is_active(api):
    headers = login_headers(api.client, "admin", "Admin123!")
    first_kb = _create_knowledge_base(api, headers, "Busy KB One")
    second_kb = _create_knowledge_base(api, headers, "Busy KB Two")
    second_base_url = f"/api/admin/knowledge-bases/{second_kb['id']}/documents"
    second_document = api.client.post(
        second_base_url,
        headers=headers,
        files={"files": ("second.txt", b"second document", "text/plain")},
    ).json()["documents"][0]

    with api.session_factory() as db:
        db.add(
            DocumentIndexTask(
                document_id=second_document["id"],
                knowledge_base_id=first_kb["id"],
                version_number=1,
                trigger=IndexTaskTrigger.REINDEX.value,
                status=IndexTaskStatus.PROCESSING.value,
                started_at=management_service.datetime.now(
                    management_service.timezone.utc
                ),
            )
        )
        db.commit()

    response = api.client.post(
        f"{second_base_url}/{second_document['id']}/reindex", headers=headers
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "当前已有文档正在建立索引，请等待该任务完成后再试。"


def test_super_admin_and_admin_soft_delete_permissions(api):
    root_headers = login_headers(api.client, "root_admin", "RootAdmin123!")
    admin_headers = login_headers(api.client, "admin", "Admin123!")

    denied_admin_create = api.client.post(
        "/api/admin/users",
        headers=admin_headers,
        json={
            "username": "another_admin",
            "password": "AnotherAdmin123!",
            "role": "admin",
        },
    )
    assert denied_admin_create.status_code == 403

    created = api.client.post(
        "/api/admin/users",
        headers=admin_headers,
        json={
            "username": "temporary_user",
            "password": "Temporary123!",
            "role": "user",
        },
    )
    assert created.status_code == 201, created.text
    user_id = created.json()["id"]

    assert api.client.delete(
        "/api/admin/users/1", headers=admin_headers
    ).status_code == 403
    deleted = api.client.delete(
        f"/api/admin/users/{user_id}", headers=admin_headers
    )
    assert deleted.status_code == 200, deleted.text
    assert deleted.json()["deleted_at"] is not None
    assert deleted.json()["is_active"] is False
    assert api.client.post(
        "/login",
        json={"username": "temporary_user", "password": "Temporary123!"},
    ).status_code == 401

    restored = api.client.post(
        f"/api/admin/users/{user_id}/restore", headers=admin_headers
    )
    assert restored.status_code == 200, restored.text
    assert restored.json()["deleted_at"] is None
    assert restored.json()["is_active"] is True
    assert login_headers(api.client, "temporary_user", "Temporary123!")

    promoted = api.client.patch(
        f"/api/admin/users/{user_id}/role",
        headers=root_headers,
        json={"role": "admin"},
    )
    assert promoted.status_code == 200, promoted.text
    assert api.client.delete(
        f"/api/admin/users/{user_id}", headers=admin_headers
    ).status_code == 403
    assert api.client.delete(
        f"/api/admin/users/{user_id}", headers=root_headers
    ).status_code == 200

    root_user_id = next(
        item["id"]
        for item in api.client.get("/api/admin/users", headers=root_headers).json()
        if item["username"] == "root_admin"
    )
    assert api.client.delete(
        f"/api/admin/users/{root_user_id}", headers=root_headers
    ).status_code == 400
