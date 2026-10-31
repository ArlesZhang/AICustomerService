# V1：知识问答基线

## 目标

Dify、知识库、RAG、提示词、兜底、Web App。下一步先冻结当前版本，建立可重复测试的基线。

当前状态：Dify 侧已完成；LangGraph 侧已新增 `knowledge` 节点接入 Dify Chatflow，关键约束见下文「基线快照」。

## 验收标准

- [x] Dify 应用可独立完成知识问答（RAG + 意图识别 + LLM）
- [x] LangGraph `knowledge` 节点可调用 Dify，并返回 `answer` / `conversation_id`
- [x] Dify 超时、报错、空答案时统一转人工，不把异常抛给客户
- [x] 多轮会话可通过 `conversation_id` 继续上下文
- [x] 相关单测、真实连通性测试与多轮冒烟测试通过
- [x] 接入方式、失败策略与实测基线记录在本文件「基线快照」

## 基线快照（2026-10-25）

- **Dify 应用**：`advanced-chat`，`POST /chat-messages`，`response_mode=blocking`；`inputs={}`；未开启“引用与归属”，`retriever_resources` 为空。
- **多轮**：Dify 返回 `conversation_id`，下一轮原样带回；API 与 CLI 均支持透传。
- **失败策略**：4xx、超时、连接失败、配置缺失、响应格式异常、空答案统一转人工；`handoff_reason` 分别为 `dify_api` / `dify_timeout` / `dify_connection` / `dify_configuration` / `dify_response` / `dify_empty_answer`。
- **重试**：仅重试 429/5xx 与连接错误；读超时默认不重试，避免 Dify 侧产生重复消息（`DIFY_RETRY_ON_TIMEOUT` 可开启）。
- **实测**：单次问答 10–13 秒；`41 passed`。
- **完整实施记录**（路由设计、代码改动清单、排错表）保留在 git 历史：`git show fb80b53:docs/runbooks/SOP-dify-integration.md`。