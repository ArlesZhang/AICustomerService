"""Manual smoke-test entry point.

Usage:
    uv run python main.py "退款多久到账？"
    uv run python main.py "那需要等多久？" <conversation_id>
"""

import sys

from src.customer_service.graph import build_graph


def main() -> None:
    question = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "退款多久到账？"
    )
    conversation_id = sys.argv[2] if len(sys.argv) > 2 else None

    state = {
        "user_id": "user_001",
        "session_id": "demo-001",
        "question": question,
    }
    if conversation_id:
        state["dify_conversation_id"] = conversation_id

    result = build_graph().invoke(state)
    dify_result = result.get("dify_result") or {}

    print("意图：", result.get("intent"))
    print("回复：", result.get("answer"))
    print("是否转人工：", result.get("handoff_required"))
    print("转人工原因：", result.get("handoff_reason"))
    print("Dify conversation_id：", result.get("dify_conversation_id"))
    print("Dify message_id：", result.get("dify_message_id"))
    print("Dify 耗时(ms)：", dify_result.get("latency_ms"))
    if result.get("dify_error"):
        print("Dify 错误：", result["dify_error"])


if __name__ == "__main__":
    main()
