from src.customer_service.dify_client import (
    DifyAPIError,
    DifyChatResult,
)
from src.customer_service.nodes import knowledge_node


def make_result(answer: str = "Dify answer") -> DifyChatResult:
    return DifyChatResult(
        answer=answer,
        conversation_id="conv-2",
        message_id="msg-2",
        task_id="task-2",
        mode="advanced-chat",
        metadata={},
        retriever_resources=[],
        usage={"total_tokens": 10},
        latency_ms=12.5,
    )


class FakeDifyClient:
    def __init__(self, *, result=None, error=None):
        self.result = result
        self.error = error
        self.calls = []

    def chat(self, **kwargs):
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return self.result


def test_knowledge_node_passes_conversation_and_inputs():
    fake = FakeDifyClient(result=make_result())

    result = knowledge_node(
        {
            "question": "  退款多久到账？ ",
            "user_id": "user-001",
            "dify_conversation_id": "conv-1",
            "dify_inputs": {"channel": "web"},
        },
        client=fake,
    )

    assert fake.calls == [
        {
            "query": "退款多久到账？",
            "user": "user-001",
            "conversation_id": "conv-1",
            "inputs": {"channel": "web"},
        }
    ]
    assert result["answer"] == "Dify answer"
    assert result["handoff_required"] is False
    assert result["dify_conversation_id"] == "conv-2"
    assert result["dify_message_id"] == "msg-2"
    assert result["dify_result"]["usage"] == {"total_tokens": 10}


def test_knowledge_node_uses_defaults_for_optional_state():
    fake = FakeDifyClient(result=make_result())

    knowledge_node({"question": "你好"}, client=fake)

    assert fake.calls == [
        {
            "query": "你好",
            "user": "anonymous",
            "conversation_id": None,
            "inputs": {},
        }
    ]


def test_knowledge_node_hands_off_on_dify_error():
    fake = FakeDifyClient(
        error=DifyAPIError(
            "bad key", status_code=401, code="unauthorized"
        )
    )

    result = knowledge_node(
        {"question": "退款多久到账？", "user_id": "user-001"},
        client=fake,
    )

    assert result["handoff_required"] is True
    assert result["handoff_reason"] == "dify_api"
    assert "bad key" in result["dify_error"]
    assert result["dify_result"]["error"]["category"] == "api"


def test_knowledge_node_hands_off_on_empty_answer():
    fake = FakeDifyClient(result=make_result(answer="   "))

    result = knowledge_node(
        {"question": "退款多久到账？", "user_id": "user-001"},
        client=fake,
    )

    assert result["handoff_required"] is True
    assert result["handoff_reason"] == "dify_empty_answer"
    assert result["dify_conversation_id"] == "conv-2"


def test_knowledge_node_asks_for_clarification_without_calling_dify():
    fake = FakeDifyClient(result=make_result())

    result = knowledge_node(
        {"question": "   ", "user_id": "user-001"},
        client=fake,
    )

    assert fake.calls == []
    assert result["handoff_required"] is False
    assert "补充" in result["answer"]
