# 第一阶段使用模拟数据。
# 后续把这些函数替换成经过授权的真实业务 API。

ORDERS = {
    "user_001": {
        "order_id": "ORDER-1001",
        "status": "shipped",
        "tracking_status": "运输中",
        "amount": 129.0,
    },
    "user_002": {
        "order_id": "ORDER-1002",
        "status": "paid",
        "tracking_status": "尚未发货",
        "amount": 299.0,
    },
}


def get_order(user_id: str) -> dict | None:
    """按当前登录用户查询订单。"""
    return ORDERS.get(user_id)


def search_product(question: str) -> dict:
    """模拟商品知识检索。"""
    if "敏感肌" in question:
        return {
            "found": True,
            "product_name": "示例护肤产品",
            "answer": (
                "当前模拟知识库没有足够证据确认"
                "该商品是否适合所有敏感肌用户。"
            ),
        }

    return {
        "found": True,
        "product_name": "示例商品",
        "answer": "该商品的详细参数请以商品页面为准。",
    }


def check_refund_eligibility(
    order: dict | None,
) -> dict:
    """模拟退款资格检查，不执行退款。"""
    if order is None:
        return {
            "eligible": False,
            "reason": "未查询到订单，需核对订单信息。",
        }

    if order["status"] == "shipped":
        return {
            "eligible": False,
            "reason": "订单已发货，需要进一步核对售后规则。",
        }

    return {
        "eligible": True,
        "reason": "模拟规则初步允许进入退款审核。",
    }
