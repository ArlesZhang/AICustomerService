from langgraph.graph import END, START, StateGraph

from .nodes import (
    classify_intent,
    complaint_node,
    fallback_node,
    order_node,
    product_node,
    refund_node,
)
from .state import CustomerServiceState


def route_by_intent(state: CustomerServiceState) -> str:
    return state.get("intent", "unknown")


def build_graph():
    builder = StateGraph(CustomerServiceState)

    # 注册节点
    builder.add_node("classify", classify_intent)
    builder.add_node("product", product_node)
    builder.add_node("order", order_node)
    builder.add_node("refund", refund_node)
    builder.add_node("complaint", complaint_node)
    builder.add_node("fallback", fallback_node)

    # 固定入口
    builder.add_edge(START, "classify")

    # 按意图分流
    builder.add_conditional_edges(
        "classify",
        route_by_intent,
        {
            "product": "product",
            "order": "order",
            "refund": "refund",
            "complaint": "complaint",
            "unknown": "fallback",
        },
    )

    # 所有业务分支结束后终止
    for node_name in [
        "product",
        "order",
        "refund",
        "complaint",
        "fallback",
    ]:
        builder.add_edge(node_name, END)

    return builder.compile()
