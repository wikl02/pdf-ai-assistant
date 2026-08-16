from fastapi import HTTPException

from backend.routers import knowledge as knowledge_router
from tests.conftest import login_headers


def _prepare_member_knowledge_base(api):
    admin_headers = login_headers(api.client, "admin", "Admin123!")
    member_headers = login_headers(api.client, "member", "Member123!")
    created = api.client.post(
        "/api/admin/knowledge-bases",
        headers=admin_headers,
        json={"name": "Conversation KB", "description": "History tests"},
    )
    assert created.status_code == 201, created.text
    users = api.client.get("/api/admin/users", headers=admin_headers).json()
    member_id = next(item["id"] for item in users if item["username"] == "member")
    granted = api.client.put(
        f"/api/admin/knowledge-bases/{created.json()['id']}/permissions/users/{member_id}",
        headers=admin_headers,
        json={"permission": "query"},
    )
    assert granted.status_code == 200, granted.text
    return admin_headers, member_headers, created.json()


def test_conversation_history_continues_and_is_owned(api, monkeypatch):
    admin_headers, member_headers, knowledge_base = _prepare_member_knowledge_base(api)
    monkeypatch.setattr(
        knowledge_router,
        "answer_question",
        lambda collection_id, question: {
            "answer": f"Answer: {question}",
            "sources": [
                {
                    "text": "source text",
                    "metadata": {"source_name": "guide.txt"},
                    "score": 0.91,
                }
            ],
            "llm_model": "deepseek-chat",
            "prompt_tokens": 120,
            "completion_tokens": 30,
            "total_tokens": 150,
        },
    )

    first = api.client.post(
        "/api/chat/ask",
        headers=member_headers,
        json={
            "collection_id": knowledge_base["collection_name"],
            "question": "First question",
        },
    )
    assert first.status_code == 200, first.text
    conversation_id = first.json()["conversation_id"]
    assert conversation_id
    assert first.json()["user_message_id"]
    assert first.json()["assistant_message_id"]

    second = api.client.post(
        "/api/chat/ask",
        headers=member_headers,
        json={
            "collection_id": knowledge_base["collection_name"],
            "question": "Second question",
            "conversation_id": conversation_id,
        },
    )
    assert second.status_code == 200, second.text
    assert second.json()["conversation_id"] == conversation_id

    history = api.client.get(
        "/api/chat/conversations", headers=member_headers
    )
    assert history.status_code == 200, history.text
    assert history.json()[0]["message_count"] == 4
    assert history.json()[0]["title"] == "First question"

    detail = api.client.get(
        f"/api/chat/conversations/{conversation_id}", headers=member_headers
    )
    assert detail.status_code == 200, detail.text
    assert [item["role"] for item in detail.json()["messages"]] == [
        "user",
        "assistant",
        "user",
        "assistant",
    ]
    assert detail.json()["messages"][1]["sources"][0]["metadata"]["source_name"] == "guide.txt"
    assert detail.json()["messages"][1]["llm_model"] == "deepseek-chat"
    assert detail.json()["messages"][1]["prompt_tokens"] == 120
    assert detail.json()["messages"][1]["completion_tokens"] == 30
    assert detail.json()["messages"][1]["total_tokens"] == 150

    summary = api.client.get(
        "/api/admin/audit-logs/summary", headers=admin_headers
    ).json()
    assert summary["prompt_tokens"] == 240
    assert summary["completion_tokens"] == 60
    assert summary["total_tokens"] == 300

    audit = api.client.get(
        "/api/admin/audit-logs",
        headers=admin_headers,
        params={"event": "question_answered"},
    ).json()
    assert audit["items"][0]["details"]["total_tokens"] == 150

    assert api.client.get(
        f"/api/chat/conversations/{conversation_id}", headers=admin_headers
    ).status_code == 404

    deleted = api.client.delete(
        f"/api/chat/conversations/{conversation_id}", headers=member_headers
    )
    assert deleted.status_code == 200
    assert api.client.get(
        f"/api/chat/conversations/{conversation_id}", headers=member_headers
    ).status_code == 404


def test_failed_answer_is_persisted_and_audited(api, monkeypatch):
    admin_headers, member_headers, knowledge_base = _prepare_member_knowledge_base(api)

    def fail_answer(collection_id, question):
        raise HTTPException(status_code=503, detail="AI service unavailable")

    monkeypatch.setattr(knowledge_router, "answer_question", fail_answer)
    response = api.client.post(
        "/api/chat/ask",
        headers=member_headers,
        json={
            "collection_id": knowledge_base["collection_name"],
            "question": "Fail safely",
        },
    )
    assert response.status_code == 503

    history = api.client.get(
        "/api/chat/conversations", headers=member_headers
    ).json()
    detail = api.client.get(
        f"/api/chat/conversations/{history[0]['id']}", headers=member_headers
    ).json()
    assert detail["messages"][-1]["status"] == "failed"
    assert detail["messages"][-1]["content"] == "AI service unavailable"

    audit = api.client.get(
        "/api/admin/audit-logs",
        headers=admin_headers,
        params={"event": "question_answered", "outcome": "failed"},
    )
    assert audit.status_code == 200, audit.text
    assert audit.json()["total"] == 1
    assert audit.json()["items"][0]["details"]["error_status"] == 503


def test_unexpected_answer_error_is_hidden_and_persisted(api, monkeypatch):
    admin_headers, member_headers, knowledge_base = _prepare_member_knowledge_base(api)

    def fail_unexpectedly(collection_id, question):
        raise RuntimeError("internal provider secret")

    monkeypatch.setattr(knowledge_router, "answer_question", fail_unexpectedly)
    response = api.client.post(
        "/api/chat/ask",
        headers=member_headers,
        json={
            "collection_id": knowledge_base["collection_name"],
            "question": "Do not expose internals",
        },
    )
    assert response.status_code == 503
    assert response.json()["detail"] == "AI 服务暂时不可用，请稍后重试。"
    assert "internal provider secret" not in response.text

    history = api.client.get(
        "/api/chat/conversations", headers=member_headers
    ).json()
    detail = api.client.get(
        f"/api/chat/conversations/{history[0]['id']}", headers=member_headers
    ).json()
    assert detail["messages"][-1]["status"] == "failed"
    assert detail["messages"][-1]["content"] == "AI 服务暂时不可用，请稍后重试。"

    audit = api.client.get(
        "/api/admin/audit-logs",
        headers=admin_headers,
        params={"event": "question_answered", "outcome": "failed"},
    )
    assert audit.status_code == 200, audit.text
    assert audit.json()["items"][0]["details"]["error_status"] == 500


def test_audit_summary_is_admin_only(api):
    admin_headers = login_headers(api.client, "admin", "Admin123!")
    member_headers = login_headers(api.client, "member", "Member123!")

    assert api.client.get(
        "/api/admin/audit-logs", headers=member_headers
    ).status_code == 403
    summary = api.client.get(
        "/api/admin/audit-logs/summary", headers=admin_headers
    )
    assert summary.status_code == 200, summary.text
    assert summary.json()["audit_event_count"] >= 2
    assert summary.json()["active_user_count"] >= 2
