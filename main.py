from src.customer_service.graph import build_graph

graph = build_graph()

result = graph.invoke({
    "user_id": "user_001",
    "session_id": "demo-001",
    "question": "我已经买了，现在想申请退款。",
})

print("意图：", result["intent"])
print("回复：", result["answer"])
print("是否转人工：", result["handoff_required"])
print("订单信息：", result.get("order_info"))
