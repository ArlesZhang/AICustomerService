from fastapi.testclient import TestClient

from src.customer_service.api import create_app
from src.customer_service.dify_client import DifyChatResult


class FakeDifyClient:
    def __init__(self):
        self.calls = []

    def chat(self, **kwargs):
        self.calls.append(kwargs)
        return DifyChatResult(
            answer="商品知识回答",
            conversation_id="conv-new",
            message_id="msg-new",
            task_id="task-new",
            mode="advanced-chat",
            metadata={},
            retriever_resources=[],
            usage={"total_tokens": 11},
            latency_ms=8.0,
        )


def test_chat_endpoint_returns_dify_result_and_conversation_id():
    fake = FakeDifyClient()
    client = TestClient(create_app(dify_client=fake))

    response = client.post(
        "/chat",
        json={
            "user_id": "user-001",
            "session_id": "session-1",
            "question": "商品材质是什么？",
            "conversation_id": "conv-old",
            "inputs": {"channel": "web"},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "商品知识回答"
    assert body["intent"] == "product"
    assert body["conversation_id"] == "conv-new"
    assert body["message_id"] == "msg-new"
    assert body["usage"] == {"total_tokens": 11}
    assert body["latency_ms"] == 8.0
    assert fake.calls[0]["conversation_id"] == "conv-old"
    assert fake.calls[0]["inputs"] == {"channel": "web"}


def test_chat_endpoint_keeps_conversation_id_for_business_intent():
    fake = FakeDifyClient()
    client = TestClient(create_app(dify_client=fake))

    response = client.post(
        "/chat",
        json={
            "user_id": "user_001",
            "question": "我的订单到哪了？",
            "conversation_id": "conv-keep",
        },
    )

    assert response.status_code == 200
    assert response.json()["conversation_id"] == "conv-keep"
    assert fake.calls == []


def test_health_endpoint():
    client = TestClient(create_app(use_dify=False))

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
