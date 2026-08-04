from backend.routers import knowledge as knowledge_router
from tests.conftest import login_headers


def _create_knowledge_base(api, admin_headers, name="Restricted KB"):
    response = api.client.post(
        "/api/admin/knowledge-bases",
        headers=admin_headers,
        json={"name": name, "description": "Access-control test"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _member_id(api, admin_headers):
    response = api.client.get("/api/admin/users", headers=admin_headers)
    assert response.status_code == 200, response.text
    return next(item["id"] for item in response.json() if item["username"] == "member")


def test_direct_grant_controls_catalog_and_question_access(api, monkeypatch):
    admin_headers = login_headers(api.client, "admin", "Admin123!")
    member_headers = login_headers(api.client, "member", "Member123!")
    knowledge_base = _create_knowledge_base(api, admin_headers)
    user_id = _member_id(api, admin_headers)

    assert api.client.get(
        "/api/knowledge-bases", headers=member_headers
    ).json() == []
    denied = api.client.post(
        "/api/chat/ask",
        headers=member_headers,
        json={
            "collection_id": knowledge_base["collection_name"],
            "question": "What is restricted?",
        },
    )
    assert denied.status_code == 403

    granted = api.client.put(
        f"/api/admin/knowledge-bases/{knowledge_base['id']}/permissions/users/{user_id}",
        headers=admin_headers,
        json={"permission": "query"},
    )
    assert granted.status_code == 200, granted.text
    assert granted.json()["permission"] == "query"

    catalog = api.client.get("/api/knowledge-bases", headers=member_headers)
    assert [item["id"] for item in catalog.json()] == [knowledge_base["id"]]

    monkeypatch.setattr(
        knowledge_router,
        "answer_question",
        lambda collection_id, question: {"answer": "Authorized", "sources": []},
    )
    answered = api.client.post(
        "/api/chat/ask",
        headers=member_headers,
        json={
            "collection_id": knowledge_base["collection_name"],
            "question": "What is restricted?",
        },
    )
    assert answered.status_code == 200, answered.text
    assert answered.json()["answer"] == "Authorized"

    revoked = api.client.delete(
        f"/api/admin/knowledge-bases/{knowledge_base['id']}/permissions/users/{user_id}",
        headers=admin_headers,
    )
    assert revoked.status_code == 200
    assert api.client.get(
        "/api/knowledge-bases", headers=member_headers
    ).json() == []


def test_department_grant_and_disabled_department(api):
    admin_headers = login_headers(api.client, "admin", "Admin123!")
    member_headers = login_headers(api.client, "member", "Member123!")
    knowledge_base = _create_knowledge_base(api, admin_headers, "Department KB")
    user_id = _member_id(api, admin_headers)

    department = api.client.post(
        "/api/admin/departments",
        headers=admin_headers,
        json={"name": "Research", "code": "research"},
    )
    assert department.status_code == 201, department.text
    department_id = department.json()["id"]

    membership = api.client.put(
        f"/api/admin/users/{user_id}/departments",
        headers=admin_headers,
        json={"department_ids": [department_id]},
    )
    assert membership.status_code == 200, membership.text

    grant = api.client.put(
        f"/api/admin/knowledge-bases/{knowledge_base['id']}/permissions/departments/{department_id}",
        headers=admin_headers,
        json={"permission": "query"},
    )
    assert grant.status_code == 200, grant.text
    assert [item["id"] for item in api.client.get(
        "/api/knowledge-bases", headers=member_headers
    ).json()] == [knowledge_base["id"]]

    disabled = api.client.patch(
        f"/api/admin/departments/{department_id}",
        headers=admin_headers,
        json={"is_active": False},
    )
    assert disabled.status_code == 200, disabled.text
    assert api.client.get(
        "/api/knowledge-bases", headers=member_headers
    ).json() == []


def test_role_grant_and_admin_endpoints_are_protected(api):
    admin_headers = login_headers(api.client, "admin", "Admin123!")
    member_headers = login_headers(api.client, "member", "Member123!")
    knowledge_base = _create_knowledge_base(api, admin_headers, "Role KB")

    assert api.client.get(
        "/api/admin/departments", headers=member_headers
    ).status_code == 403
    assert api.client.put(
        f"/api/admin/knowledge-bases/{knowledge_base['id']}/permissions/roles/user",
        headers=member_headers,
        json={"permission": "query"},
    ).status_code == 403

    grant = api.client.put(
        f"/api/admin/knowledge-bases/{knowledge_base['id']}/permissions/roles/user",
        headers=admin_headers,
        json={"permission": "query"},
    )
    assert grant.status_code == 200, grant.text
    catalog = api.client.get("/api/knowledge-bases", headers=member_headers)
    assert [item["id"] for item in catalog.json()] == [knowledge_base["id"]]
