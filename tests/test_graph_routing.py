from src.customer_service.dify_client import DifyChatResult
from src.customer_service.graph import build_graph


class FakeDifyClient:
    def __init__(self):
        self.calls = []

    def chat(self, **kwargs):
        self.calls.append(kwargs)
        return DifyChatResult(
            answer="Dify 知识回答",
            conversation_id="conv-dify",
            message_id="msg-dify",
            task_id="task-dify",
            mode="advanced-chat",
            metadata={},
            retriever_resources=[],
            usage={"total_tokens": 7},
            latency_ms=3.0,
        )


def invoke(
    question: str,
    *,
    use_dify: bool = True,
    client=None,
) -> dict:
    graph = build_graph(use_dify=use_dify, dify_client=client)
    return graph.invoke(
        {
            "user_id": "user_001",
            "session_id": "test-session",
            "question": question,
        }
    )


def test_product_intent_routes_to_dify():
    fake = FakeDifyClient()

    result = invoke("这个商品适合敏感肌吗？", client=fake)

    assert result["intent"] == "product"
    assert result["answer"] == "Dify 知识回答"
    assert result["dify_conversation_id"] == "conv-dify"
    assert len(fake.calls) == 1


def test_unknown_intent_routes_to_dify():
    fake = FakeDifyClient()

    result = invoke("今天天气怎么样？", client=fake)

    assert result["intent"] == "unknown"
    assert result["answer"] == "Dify 知识回答"
    assert len(fake.calls) == 1


def test_order_intent_stays_in_langgraph():
    fake = FakeDifyClient()

    result = invoke("我的订单到哪了？", client=fake)

    assert result["intent"] == "order"
    assert "ORDER-1001" in result["answer"]
    assert fake.calls == []


def test_refund_policy_routes_to_dify():
    fake = FakeDifyClient()

    result = invoke("退款多久到账？", client=fake)

    assert result["intent"] == "refund"
    assert result["answer"] == "Dify 知识回答"
    assert len(fake.calls) == 1


def test_refund_action_stays_in_langgraph():
    fake = FakeDifyClient()

    result = invoke("我要申请退款", client=fake)

    assert result["intent"] == "refund_action"
    assert result["handoff_required"] is True
    assert result["handoff_reason"] == "refund_requires_review"
    assert fake.calls == []


def test_shipping_policy_routes_to_dify():
    fake = FakeDifyClient()

    result = invoke("下单后多久发货？", client=fake)

    assert result["intent"] == "unknown"
    assert result["answer"] == "Dify 知识回答"
    assert len(fake.calls) == 1


def test_live_shipping_query_stays_in_langgraph():
    fake = FakeDifyClient()

    result = invoke("发货了吗？", client=fake)

    assert result["intent"] == "order"
    assert "ORDER-1001" in result["answer"]
    assert fake.calls == []


def test_local_mode_keeps_mock_product_node():
    result = invoke("这个商品适合敏感肌吗？", use_dify=False)

    assert result["intent"] == "product"
    assert "敏感肌" in result["answer"]
    assert "dify_conversation_id" not in result


def test_local_mode_unknown_uses_fallback():
    result = invoke("今天天气怎么样？", use_dify=False)

    assert result["intent"] == "unknown"
    assert result["handoff_required"] is False
    assert "补充" in result["answer"]


def test_local_mode_refund_policy_uses_mock_refund_node():
    result = invoke("退款多久到账？", use_dify=False)

    assert result["intent"] == "refund"
    assert result["handoff_required"] is True
    assert result["handoff_reason"] == "refund_requires_review"
