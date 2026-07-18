from tests.conftest import login_headers


def test_active_user_can_list_knowledge_catalog(api):
    headers = login_headers(api.client, "member", "Member123!")

    response = api.client.get("/api/knowledge-bases", headers=headers)

    assert response.status_code == 200
    assert response.json() == []


def test_catalog_requires_login(api):
    response = api.client.get("/api/knowledge-bases")

    assert response.status_code == 401
