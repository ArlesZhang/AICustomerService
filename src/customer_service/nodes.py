import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from .tools import (
    check_refund_eligibility,
    get_order,
    search_product,
)

load_dotenv()

def get_llm():
    return ChatOpenAI(
        model=os.environ["MODEL_NAME"],
        api_key=os.environ["MODEL_API_KEY"],
        base_url=os.environ["MODEL_BASE_URL"],
        temperature=0,
    )

def classify_intent(state: dict) -> dict:
    """
    先用规则完成基础分流。
    后续再替换为大模型结构化意图识别。
    """
    question = state["question"]

    if any(word in question for word in ["投诉", "人工", "客服经理"]):
        intent = "complaint"
    elif any(word in question for word in ["退款", "退货", "退钱"]):
        intent = "refund"
    elif any(word in question for word in ["订单", "物流", "发货"]):
        intent = "order"
    elif any(word in question for word in ["商品", "材质", "敏感肌", "参数"]):
        intent = "product"
    else:
        intent = "unknown"

    return {"intent": intent}


def product_node(state: dict) -> dict:
    result = search_product(state["question"])

    answer = (
        result["answer"]
        if result["found"]
        else "暂时没有找到相关商品信息，我为你转接人工客服。"
    )

    return {
        "product_info": result,
        "answer": answer,
        "handoff_required": not result["found"],
    }


def order_node(state: dict) -> dict:
    order = get_order(state["user_id"])

    if order is None:
        return {
            "order_info": {},
            "answer": "暂时没有查询到你的订单，请核对账号或联系人工客服。",
            "handoff_required": True,
            "handoff_reason": "order_not_found",
        }

    if order["status"] == "shipped":
        answer = (
            f"订单 {order['order_id']} 当前状态为"
            f"「{order['tracking_status']}」。"
        )
    else:
        answer = (
            f"订单 {order['order_id']} 当前状态为"
            f"「{order['tracking_status']}」。"
        )

    return {
        "order_info": order,
        "answer": answer,
        "handoff_required": False,
    }


def refund_node(state: dict) -> dict:
    order = get_order(state["user_id"])
    result = check_refund_eligibility(order)

    return {
        "order_info": order or {},
        "refund_result": result,
        "answer": (
            f"已完成初步售后规则检查：{result['reason']}"
            "。当前尚未执行退款操作。"
        ),
        "handoff_required": True,
        "handoff_reason": "refund_requires_review",
    }


def complaint_node(state: dict) -> dict:
    return {
        "answer": "理解你的诉求，我会将问题转交人工客服进一步处理。",
        "handoff_required": True,
        "handoff_reason": "customer_complaint",
    }


def fallback_node(state: dict) -> dict:
    return {
        "answer": "我暂时无法准确判断你的问题，可以补充一下具体情况吗？",
        "handoff_required": False,
    }
