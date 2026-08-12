from fastapi import HTTPException

from backend.services import evaluation_service
from tests.conftest import login_headers


def _create_dataset_with_case(api, headers):
    knowledge_base = api.client.post(
        "/api/admin/knowledge-bases",
        headers=headers,
        json={"name": "质量评估知识库", "description": "用于自动回归"},
    )
    assert knowledge_base.status_code == 201, knowledge_base.text
    dataset = api.client.post(
        "/api/admin/evaluations/datasets",
        headers=headers,
        json={
            "name": "客服标准问题集",
            "description": "检查退款政策回答",
            "knowledge_base_id": knowledge_base.json()["id"],
        },
    )
    assert dataset.status_code == 201, dataset.text
    case = api.client.post(
        f"/api/admin/evaluations/datasets/{dataset.json()['id']}/cases",
        headers=headers,
        json={
            "question": "退款期限是多少天？",
            "expected_answer_keywords": ["7天", "退款"],
            "expected_source_names": ["产品FAQ.txt"],
            "notes": "核心售后问题",
        },
    )
    assert case.status_code == 201, case.text
    return dataset.json(), case.json()


def test_regular_user_cannot_access_quality_evaluation(api):
    headers = login_headers(api.client, "member", "Member123!")
    assert api.client.get("/api/admin/evaluations/summary", headers=headers).status_code == 403
    assert api.client.get("/api/admin/evaluations/datasets", headers=headers).status_code == 403


def test_evaluation_dataset_run_and_manual_review(api, monkeypatch):
    headers = login_headers(api.client, "admin", "Admin123!")
    dataset, case = _create_dataset_with_case(api, headers)

    def fake_answer(_collection_id: str, question: str):
        assert question == "退款期限是多少天？"
        return {
            "answer": "符合条件的订单可在 7天 内申请退款。",
            "sources": [
                {
                    "text": "退款期限为七天。",
                    "metadata": {"source_name": "产品FAQ.txt", "page": 1},
                    "score": 0.93,
                }
            ],
        }

    monkeypatch.setattr(evaluation_service, "answer_question", fake_answer)
    run = api.client.post(
        f"/api/admin/evaluations/datasets/{dataset['id']}/runs",
        headers=headers,
    )
    assert run.status_code == 201, run.text
    payload = run.json()
    assert payload["status"] == "completed"
    assert payload["total_cases"] == payload["completed_cases"] == 1
    assert payload["answer_hit_count"] == 1
    assert payload["source_hit_count"] == 1
    assert payload["results"][0]["answer_keyword_hits"] == ["7天", "退款"]
    assert payload["results"][0]["source_hits"] == ["产品FAQ.txt"]

    result_id = payload["results"][0]["id"]
    reviewed = api.client.patch(
        f"/api/admin/evaluations/runs/{payload['id']}/results/{result_id}/review",
        headers=headers,
        json={"review_status": "passed", "review_note": "回答与引用均正确"},
    )
    assert reviewed.status_code == 200, reviewed.text
    assert reviewed.json()["review_status"] == "passed"
    assert reviewed.json()["reviewer_id"] is not None

    detail = api.client.get(
        f"/api/admin/evaluations/datasets/{dataset['id']}", headers=headers
    )
    assert detail.status_code == 200
    assert detail.json()["case_count"] == 1
    assert detail.json()["run_count"] == 1
    assert detail.json()["cases"][0]["id"] == case["id"]

    summary = api.client.get("/api/admin/evaluations/summary", headers=headers)
    assert summary.status_code == 200
    assert summary.json()["latest_answer_hit_rate"] == 100.0
    assert summary.json()["latest_source_hit_rate"] == 100.0


def test_evaluation_records_failed_case_and_continues(api, monkeypatch):
    headers = login_headers(api.client, "admin", "Admin123!")
    dataset, _ = _create_dataset_with_case(api, headers)

    api.client.post(
        f"/api/admin/evaluations/datasets/{dataset['id']}/cases",
        headers=headers,
        json={
            "question": "客服电话是什么？",
            "expected_answer_keywords": ["400"],
            "expected_source_names": ["客服手册.pdf"],
        },
    )

    def fake_answer(_collection_id: str, question: str):
        if "退款" in question:
            raise HTTPException(status_code=503, detail="模型额度不足")
        return {
            "answer": "客服电话是 400-000-0000。",
            "sources": [
                {
                    "text": "客服电话",
                    "metadata": {"source_name": "客服手册.pdf"},
                    "score": 0.9,
                }
            ],
        }

    monkeypatch.setattr(evaluation_service, "answer_question", fake_answer)
    run = api.client.post(
        f"/api/admin/evaluations/datasets/{dataset['id']}/runs",
        headers=headers,
    )
    assert run.status_code == 201, run.text
    payload = run.json()
    assert payload["status"] == "completed"
    assert payload["completed_cases"] == 2
    assert payload["error_message"] == "1 道题执行失败"
    assert len(payload["results"]) == 2
    assert sum(result["error_message"] is not None for result in payload["results"]) == 1
    assert payload["answer_hit_count"] == 1
    assert payload["source_hit_count"] == 1
