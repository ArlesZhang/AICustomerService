from typing import Literal, TypedDict
from pydantic import BaseModel, Field

Intent = Literal[
    "product",
    "order",
    "refund",
    "refund_action",
    "complaint",
    "unknown",
]


class CustomerServiceState(TypedDict, total=False):
    # 本轮客户输入
    user_id: str
    session_id: str
    question: str

    # Dify 知识问答：inputs 为 Dify 应用输入变量预留；
    # conversation_id 用于多轮上下文；result/error 用于观测与评估。
    dify_inputs: dict
    dify_conversation_id: str
    dify_message_id: str
    dify_result: dict
    dify_error: str

    # 流程中间状态
    intent: Intent
    order_info: dict
    product_info: dict
    refund_result: dict

    # 最终处理结果
    answer: str
    handoff_required: bool
    handoff_reason: str


# 定义模型输出结构化结果

class IntentResult(BaseModel):
    intent: Literal[
        "product",
        "order",
        "refund",
        "complaint",
        "unknown",
    ] = Field(description="客户本轮问题的主要业务意图")

    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="模型对本次分类的置信程度",
    )

    needs_human: bool = Field(
        description="是否需要转人工处理",
    )

    reason: str = Field(
        description="分类理由，简要说明判断依据",
    )
