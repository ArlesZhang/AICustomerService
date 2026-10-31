# 项目状态与下一步

> 最后更新：2026-10-31
> 当前阶段：V1 已完成并冻结（`v0.1.0`）；V2 输入已具备，评测脚本未开始

## 1. 当前进度

**已完成**

- **V1 知识问答基线**：Dify Chatflow（`advanced-chat`）+ LangGraph `knowledge` 节点；支持多轮 `conversation_id`、Dify 超时/报错/空答案降级转人工；FastAPI `POST /chat`、`GET /health` 与 CLI 入口；41 项测试通过；已提交并打 `v0.1.0` tag。
- **基准数据包**：`ecommerce_cs_mvp_dataset/ecommerce_cs_mvp_kit/`，含 50 条评测 case、6 份知识文档、订单/商品/物流/政策 mock 数据；版本 `xq-cs-benchmark-1.0`，政策版本 `2026-10-01`。
- **文档**：V1–V8 路线图（`docs/roadmap/`）、本状态文档；V1 接入约束见 `docs/roadmap/V1_BASELINE.md` 的「基线快照」。

**未开始**

- **V2 知识治理与评估闭环**：评测脚本、知识资产表、Bad Case 归因表、知识库/Prompt 版本记录均未落地；50 条测试集已具备（五项交付物完成 1 项）。
- **V3–V8**：全部未开始；V3 仅有 mock 数据，V4 仅有状态图骨架。

## 2. 下一步建议

按 **V2.1 → V2.3 → V2.2 → V2.4** 推进：

1. **V2.1 校准测试集**：审阅 50 条 case 的预期行为、关键事实与风险等级，必要时补充真实用户表达。
2. **V2.3 基线评估脚本**：编写 `scripts/evaluate.py`，输出意图准确率、检索 Recall@K、回答准确率、转人工率、P95 延迟、token 成本，生成 `eval_report.md`。
3. **V2.2 知识资产表**：为 6 份知识文档补齐元数据（id、分类、版本、生效/失效日期、负责人、状态），产出 `knowledge_inventory.csv`。
4. **V2.4 Bad Case 闭环**：建立 `badcase_log.csv` 与回归用例，把失败归因到知识/检索/上下文/Prompt/模型/工作流/工具/安全。

没有标准测试集和基线指标，RAG 调优与功能扩展都无法判断是否有效。

## 3. 注意事项与前置准备

**仓库与密钥**

- GitHub 仓库已于 2026-10-31 删除并重建（private）；旧提交 SHA 与旧 `.env` 不在新仓库中，未认证访问均为 404。
- `.env` 已从全部 git 历史移除，本地文件保留；`.env.example` 仅含占位符。
- 旧 `MODEL_API_KEY` 未轮换（你的决定），建议关注该 Key 的异常调用与账单。
- 重写前备份 `/home/arleszhang/AICustomerService-pre-rewrite-20261031.bundle` 含旧 `.env`，确认无误后删除。

**Dify 现状**

- blocking 模式，单次问答约 10–13 秒，无流式输出。
- 未开启“引用与归属”，`retriever_resources` 为空，暂无法评估检索来源。

**能力边界**

- 意图识别为规则版，无槽位提取、置信度、情绪识别。
- 无鉴权、租户隔离、限流、提示词注入防护、审计。
- 订单/退款为 mock，无真实业务 API。

**开始 V2 前需要你提供**

- Dify 检索配置：分段策略、Embedding 模型、Top-K、Score Threshold、是否混合检索 / Rerank、LLM 模型。
- 知识文档清单：文档名、业务分类、来源、负责人、生效/失效日期、当前版本。
- 退款、退货、发货、售后、投诉升级规则，含例外与生效时间。
- 目标指标：自助解决率、转人工率、回答准确率、P95 延迟、单次会话成本。
