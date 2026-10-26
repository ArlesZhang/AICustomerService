import pytest

from src.customer_service.nodes import classify_intent


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("退款多久到账？", "refund"),
        ("申请退款的条件是什么？", "refund"),
        ("我要申请退款", "refund_action"),
        ("把我的钱退回来，现在就执行", "refund_action"),
        ("我的订单到哪了？", "order"),
        ("帮我查订单实时物流", "order"),
        ("下单后多久发货？", "unknown"),
        ("发货了吗？", "order"),
        ("这个商品适合敏感肌吗？", "product"),
        ("我要投诉", "complaint"),
        ("你好", "unknown"),
    ],
)
def test_classify_intent(question: str, expected: str):
    assert classify_intent({"question": question})["intent"] == expected
