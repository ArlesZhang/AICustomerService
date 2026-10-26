from langgraph.graph import END, START, StateGraph

from .dify_client import DifyClient
from .nodes import (
    classify_intent,
    complaint_node,
    fallback_node,
    make_knowledge_node,
    order_node,
    product_node,
    refund_node,
)
from .state import CustomerServiceState

_KNOWN_INTENTS = {
    "product",
    "order",
    "refund",
    "refund_action",
    "complaint",
    "unknown",
}


def route_by_intent(state: CustomerServiceState) -> str:
    intent = state.get("intent", "unknown")
    return intent if intent in _KNOWN_INTENTS else "unknown"


def build_graph(
    *,
    use_dify: bool = True,
    dify_client: DifyClient | None = None,
):
    """
    构建客服工作流。

    use_dify=True：product / refund / unknown 走 Dify Chatflow
    知识问答；refund_action 才进入退款业务节点。
    use_dify=False：保留 V1 的本地模拟节点，用于离线演示和测试。
    """
    builder = StateGraph(CustomerServiceState)

    # 注册节点
    builder.add_node("classify", classify_intent)
    builder.add_node("order", order_node)
    builder.add_node("refund", refund_node)
    builder.add_node("complaint", complaint_node)

    if use_dify:
        builder.add_node("knowledge", make_knowledge_node(dify_client))
        intent_routes = {
            "product": "knowledge",
            "order": "order",
            "refund": "knowledge",
            "refund_action": "refund",
            "complaint": "complaint",
            "unknown": "knowledge",
        }
        terminal_nodes = ["knowledge", "order", "refund", "complaint"]
    else:
        builder.add_node("product", product_node)
        builder.add_node("fallback", fallback_node)
        intent_routes = {
            "product": "product",
            "order": "order",
            "refund": "refund",
            "refund_action": "refund",
            "complaint": "complaint",
            "unknown": "fallback",
        }
        terminal_nodes = [
            "product",
            "fallback",
            "order",
            "refund",
            "complaint",
        ]

    # 固定入口
    builder.add_edge(START, "classify")

    # 按意图分流
    builder.add_conditional_edges(
        "classify",
        route_by_intent,
        intent_routes,
    )

    # 所有业务分支结束后终止
    for node_name in terminal_nodes:
        builder.add_edge(node_name, END)

    return builder.compile()
