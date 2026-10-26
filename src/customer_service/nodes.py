import logging
import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from .dify_client import DifyClient, DifyError, get_dify_client
from .tools import (
    check_refund_eligibility,
    get_order,
    search_product,
)

load_dotenv()

logger = logging.getLogger(__name__)


def get_llm():
    return ChatOpenAI(
        model=os.environ["MODEL_NAME"],
        api_key=os.environ["MODEL_API_KEY"],
        base_url=os.environ["MODEL_BASE_URL"],
        temperature=0,
    )


# 知识型问题的常见标记：出现这些词时，优先按“问规则/流程”处理，
# 而不是直接触发业务操作。
_KNOWLEDGE_MARKERS = (
    "怎么",
    "如何",
    "多久",
    "多长时间",
    "什么",
    "哪些",
    "条件",
    "规则",
    "政策",
    "流程",
    "能否",
    "可以吗",
    "什么时候",
    "到账",
)

_REFUND_WORDS = ("退款", "退货", "退钱")

_REFUND_ACTION_MARKERS = (
    "我要退款",
    "我要退货",
    "想退款",
    "想退货",
    "帮我退款",
    "帮我退货",
    "给我退款",
    "给我退货",
    "申请退款",
    "申请退货",
    "执行退款",
    "马上退",
    "现在就退",
    "把钱退",
    "退回来",
    "退款吧",
    "要退款",
    "要退货",
)

# 明确指向“这个用户的实时订单”的标记，优先级最高。
_ORDER_LIVE_MARKERS = (
    "我的订单",
    "订单号",
    "订单状态",
    "查订单",
    "查询订单",
    "实时",
)

# 物流/发货类问题：带“怎么/多久”等词时是知识问题，
# 不带时才按实时订单查询处理。
_ORDER_TOPIC_MARKERS = ("物流", "快递", "发货", "到哪")

_PRODUCT_WORDS = ("商品", "材质", "敏感肌", "参数")


def classify_intent(state: dict) -> dict:
    """
    先用规则完成基础分流。
    后续再替换为大模型结构化意图识别。

    V1 的关键区分：
    - “退款多久到账”是知识问题 -> 交给 Dify；
    - “我要申请退款”是业务操作 -> 留给 LangGraph。
    """
    question = state["question"]

    if any(word in question for word in ["投诉", "人工", "客服经理"]):
        return {"intent": "complaint"}

    is_refund_related = any(
        word in question for word in _REFUND_WORDS
    ) or any(
        marker in question for marker in _REFUND_ACTION_MARKERS
    )

    if is_refund_related:
        is_action = any(
            marker in question for marker in _REFUND_ACTION_MARKERS
        )
        asks_policy = any(
            marker in question for marker in _KNOWLEDGE_MARKERS
        )
        intent = (
            "refund_action"
            if is_action and not asks_policy
            else "refund"
        )
        return {"intent": intent}

    if any(word in question for word in _ORDER_LIVE_MARKERS):
        return {"intent": "order"}

    if any(word in question for word in _ORDER_TOPIC_MARKERS):
        asks_policy = any(
            marker in question for marker in _KNOWLEDGE_MARKERS
        )
        if not asks_policy:
            return {"intent": "order"}

    if any(word in question for word in _PRODUCT_WORDS):
        return {"intent": "product"}

    return {"intent": "unknown"}


def knowledge_node(
    state: dict,
    *,
    client: DifyClient | None = None,
) -> dict:
    """
    将知识型问题交给 Dify Chatflow（RAG + 意图识别 + LLM）。

    Dify 不可用、返回空答案或调用异常时统一转人工，
    避免把不确定的答案直接返回给客户。
    """
    question = (state.get("question") or "").strip()
    user_id = (state.get("user_id") or "").strip() or "anonymous"

    if not question:
        return {
            "answer": "请补充一下你的具体问题，我再帮你查询。",
            "handoff_required": False,
            "handoff_reason": "",
            "dify_error": "",
        }

    try:
        dify = client or get_dify_client()
        result = dify.chat(
            query=question,
            user=user_id,
            conversation_id=state.get("dify_conversation_id") or None,
            inputs=state.get("dify_inputs") or {},
        )
    except DifyError as exc:
        logger.warning(
            "Dify knowledge call failed category=%s code=%s: %s",
            exc.category,
            exc.code,
            exc,
        )
        return {
            "answer": "知识库服务暂时不可用，已为你转接人工客服。",
            "handoff_required": True,
            "handoff_reason": f"dify_{exc.category}",
            "dify_error": str(exc),
            "dify_result": {"error": exc.to_dict()},
        }
    except Exception as exc:  # defensive: integration bugs must not break the graph
        logger.exception("Unexpected error while calling Dify")
        return {
            "answer": "知识库服务暂时不可用，已为你转接人工客服。",
            "handoff_required": True,
            "handoff_reason": "dify_unexpected_error",
            "dify_error": str(exc),
            "dify_result": {
                "error": {
                    "category": "unexpected",
                    "message": str(exc),
                }
            },
        }

    logger.info(
        "Dify knowledge call ok conversation_id=%s message_id=%s "
        "latency_ms=%.0f answer_chars=%d",
        result.conversation_id,
        result.message_id,
        result.latency_ms,
        len(result.answer),
    )

    if not result.answer.strip():
        return {
            "answer": "暂时没有查到可靠答案，已为你转接人工客服。",
            "handoff_required": True,
            "handoff_reason": "dify_empty_answer",
            "dify_conversation_id": result.conversation_id,
            "dify_message_id": result.message_id,
            "dify_result": result.to_dict(),
            "dify_error": "",
        }

    return {
        "answer": result.answer.strip(),
        "handoff_required": False,
        "handoff_reason": "",
        "dify_conversation_id": result.conversation_id,
        "dify_message_id": result.message_id,
        "dify_result": result.to_dict(),
        "dify_error": "",
    }


def make_knowledge_node(client: DifyClient | None = None):
    """Bind an optional Dify client for tests or dependency injection."""

    def knowledge(state: dict) -> dict:
        return knowledge_node(state, client=client)

    return knowledge


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
            "已完成初步售后规则检查："
            f"{str(result['reason']).rstrip('。')}。"
            "当前尚未执行退款操作。"
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
