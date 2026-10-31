# V3：业务 API 接入

## 目标

构建模拟订单、物流、商品、售后和工单服务，先打通只读工具调用，再接入真实系统。通过 API 查询订单、物流和工单状态，加入身份验证、权限校验及操作审计。涉及退款等有实际影响的操作时，应加入明确授权和必要的人工确认。

## V3.1 先定义业务工具，而不是先写 Agent

第一版建议实现五类工具：

|工具|类型|第一版能力|
|---|---|---|
|`get_order`|只读|查询订单状态|
|`get_tracking`|只读|查询物流轨迹|
|`get_product`|只读|查询商品信息|
|`get_after_sales_policy`|只读|查询适用售后规则|
|`create_ticket`|写入|创建人工客服工单|

随后再增加 `request_refund` 等有实际影响的操作。退款不应只是一个模型可以任意调用的普通函数。

## V3.2 定义统一工具协议

每个工具都应该有：

- 明确的输入 Schema
- 明确的输出 Schema
- 身份与权限检查
- 超时和错误处理
- 审计日志
- 可测试的业务规则

例如，订单查询工具：
```

from pydantic import BaseModel, Field


class OrderQuery(BaseModel):
    order_id: str = Field(min_length=6, max_length=40)


class OrderResult(BaseModel):
    order_id: str
    status: str
    payment_status: str
    fulfillment_status: str
```

这里的 Schema 只负责约束数据格式。真实系统还必须检查当前用户是否有权查看这个订单。

## V3.3 创建可运行的模拟业务 API

先用模拟数据，不需要真实电商平台账号，也不要在练习阶段直接调用真实退款接口。

在你的 Ubuntu 环境中，使用 Python 3.11、`uv` 和 FastAPI 建立服务。
```
mkdir -p ~/customer-service-agent
cd ~/customer-service-agent

uv init --python 3.11
uv add fastapi "uvicorn[standard]" pydantic httpx
uv add langgraph langchain-core langchain-openai
uv add --dev pytest ruff

mkdir -p app tests data
```

创建 `app/mock_business_api.py`：
```

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="Mock Ecommerce Business API")

# 仅用于本地演示。真实项目应使用数据库和身份系统。
ORDERS = {
    "ORD100001": {
        "order_id": "ORD100001",
        "owner_id": "demo_user_1",
        "status": "shipped",
        "payment_status": "paid",
        "fulfillment_status": "in_transit",
    },
    "ORD100002": {
        "order_id": "ORD100002",
        "owner_id": "demo_user_1",
        "status": "paid",
        "payment_status": "paid",
        "fulfillment_status": "awaiting_shipment",
    },
}

TRACKING = {
    "ORD100001": [
        {"time": "2026-10-24 09:00", "event": "包裹已揽收"},
        {"time": "2026-10-24 18:00", "event": "包裹运输中"},
    ]
}


class OrderQuery(BaseModel):
    order_id: str = Field(min_length=6, max_length=40)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/tools/get_order")
def get_order(
    query: OrderQuery,
    x_demo_user_id: str = Header(default=""),
):
    order = ORDERS.get(query.order_id)

    if not order:
        raise HTTPException(status_code=404, detail="order_not_found")

    # 演示用权限检查。生产环境必须从已验证的身份中
    # 获取用户 ID，不能信任客户端随意传入的用户 ID。
    if order["owner_id"] != x_demo_user_id:
        raise HTTPException(status_code=403, detail="forbidden")

    return {
        key: value
        for key, value in order.items()
        if key != "owner_id"
    }


@app.post("/tools/get_tracking")
def get_tracking(
    query: OrderQuery,
    x_demo_user_id: str = Header(default=""),
):
    order = ORDERS.get(query.order_id)

    if not order:
        raise HTTPException(status_code=404, detail="order_not_found")

    if order["owner_id"] != x_demo_user_id:
        raise HTTPException(status_code=403, detail="forbidden")

    return {
        "order_id": query.order_id,
        "events": TRACKING.get(query.order_id, []),
    }
```

启动服务：
```
uv run uvicorn app.mock_business_api:app \
  --host 127.0.0.1 \
  --port 8000 \
  --reload
```

打开 `http://127.0.0.1:8000/docs`，即可通过 FastAPI 的交互式文档测试接口。

验证健康检查：
```
curl http://127.0.0.1:8000/health
```

预期返回：
```
{"status":"ok"}
```

测试订单查询：
```
curl -X POST \
  http://127.0.0.1:8000/tools/get_order \
  -H 'Content-Type: application/json' \
  -H 'X-Demo-User-Id: demo_user_1' \
  -d '{"order_id":"ORD100001"}'
```

预期返回的订单状态应为 `shipped`，而不是由大模型生成的猜测。

这套服务只适用于本地演示。`X-Demo-User-Id` 是模拟身份机制，不能直接用作生产环境的鉴权方案。

## V3.4 把业务 API 接入 Dify

先用 Dify 的 HTTP Request 节点，或创建一个自定义工具插件，调用 FastAPI 服务。

在 Dify Chatflow 中建立类似链路：

```
Start
  ↓
Question Classifier
  ├─ 普通政策问题 → Knowledge Retrieval → LLM → Answer
  ├─ 订单查询 → 参数校验 → get_order → LLM → Answer
  ├─ 物流查询 → 参数校验 → get_tracking → LLM → Answer
  └─ 高风险操作 → 安全提示 / 人工确认
```

对于工具调用，重点不是让模型生成一段 JSON，而是确保：

1. 模型或工作流提取的参数通过 Schema 校验。
2. 订单号来自用户输入或可信的会话状态。
3. API 端再次校验身份与资源权限。
4. 工具失败时返回明确错误码，而不是让 LLM 猜测。
5. 只有收到真实成功结果后，才能告诉用户操作已经完成。

Dify 的工作流节点可以调用工具和 HTTP 接口，也可以通过条件分支控制执行路径。


### V3 验收标准

- 至少两个只读业务工具可以独立调用并返回结构化结果。
- 正常查询、订单不存在、无权访问和服务异常均有测试。
- LLM 只负责组织回答，不能伪造 API 返回值。
- 所有工具调用都有可追踪的请求 ID、结果状态和耗时。
- 所有写入类工具都具有授权、幂等和审计设计；退款等操作默认不自动执行。