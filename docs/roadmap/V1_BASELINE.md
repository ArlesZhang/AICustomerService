# V1：知识问答基线

## 目标

Dify、知识库、RAG、提示词、兜底、Web App。下一步先冻结当前版本，建立可重复测试的基线。

当前状态：Dify 侧已完成；LangGraph 侧已新增 `knowledge` 节点接入 Dify Chatflow，详见 [docs/SOP-dify-integration.md](docs/SOP-dify-integration.md)。

## 验收标准

- [x] Dify 应用可独立完成知识问答（RAG + 意图识别 + LLM）
- [x] LangGraph `knowledge` 节点可调用 Dify，并返回 `answer` / `conversation_id`
- [x] Dify 超时、报错、空答案时统一转人工，不把异常抛给客户
- [x] 多轮会话可通过 `conversation_id` 继续上下文
- [x] 相关单测、真实连通性测试与多轮冒烟测试通过
- [x] 接入说明沉淀到 `docs/SOP-dify-integration.md`