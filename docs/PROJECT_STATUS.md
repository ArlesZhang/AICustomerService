# 项目状态与下一步

> 最后更新：2026-10-28  
> 当前阶段：V1 已完成并冻结基线（`v0.1.0`）；V2 输入已具备（50 条评测集 + 6 份知识文档），评测脚本未开始  
> 维护方式：每次任务结束后更新本文件，规则见 `CLAUDE.md` 的“文档维护规范”。

## 0. 一句话结论

V1 知识问答基线已完成：Dify 负责 RAG 知识问答，LangGraph 已能调用 Dify，并支持多轮会话、异常降级、FastAPI 入口和自动化测试。V2 的知识治理与评估闭环尚未开始。下一步应优先建立标准测试集和基线评估，而不是继续堆功能。

---

## 1. 任务前状态（本次 Dify 节点接入之前）

### 1.1 已完成

- **Dify 侧**：`AICustomerService` Chatflow（`advanced-chat`）已部署，包含 RAG、Question Classifier、Knowledge Retrieval、LLM 等节点；`.env` 已配置 Dify API Key 和 URL；Dify 应用本身可以独立回答知识问题。
- **LangGraph 侧**：已有 `state.py`、`nodes.py`、`graph.py`、`tools.py` 骨架；`classify_intent` 为规则分流；`order/product/refund/complaint/fallback` 为模拟节点；`api.py` 为空。
- **文档**：README 已列出 V1–V8 阶段，V1 标记为已完成。

### 1.2 当时的缺口

- LangGraph 没有任何 Dify 调用，Dify 的知识能力没有进入编排流程。
- `退款多久到账？` 这类知识问题会被规则判成 `refund`，直接进入模拟退款节点，到不了 Dify。
- 没有多轮 `conversation_id` 管理、Dify 异常降级、API 入口和自动化测试。
- V2 所需资产全部为空：无测试集、知识资产表、Bad Case 表、评估脚本、版本记录。

---

## 2. 本次任务完成内容（Dify 节点接入）

| 交付物 | 内容 | 验证 |
| --- | --- | --- |
| `dify_client.py` | 封装 `POST /chat-messages`；配置、超时、重试、错误分类、响应归一化 | 客户端单测通过 |
| `knowledge` 节点 | 把知识型问题交给 Dify；空答案/异常/超时统一转人工 | 节点单测 + 真实 E2E |
| 路由细化 | `product/refund/unknown` → Dify；`order` → 订单节点；`refund_action` → 退款节点；`complaint` → 投诉节点 | 参数化路由测试 |
| 多轮会话 | Dify 返回的 `conversation_id` 写入 state，并在下一轮透传 | 真实两轮对话验证 |
| State 扩展 | `dify_inputs`、`dify_conversation_id`、`dify_message_id`、`dify_result`、`dify_error` | 节点/API 测试 |
| FastAPI | `POST /chat`、`GET /health`，支持 `conversation_id` 和 `inputs` | API 测试 |
| CLI | `uv run python main.py "<问题>" [conversation_id]` | 手工冒烟 |
| 配置模板 | `.env.example` 增加 Dify 配置项 | 可复现 |
| 测试 | 客户端、节点、路由、API，共 41 项 | `41 passed` |
| SOP | 接入方案、复现步骤、实测记录、排错与后续钩子 | `docs/SOP-dify-integration.md` |

### 2.1 关键行为变化

- **退款问题分流**：`退款` 表示“问退款规则”，走 Dify；`refund_action` 表示“要执行退款/退货”，走 LangGraph 业务节点。
- **物流问题分流**：明确指向当前用户实时订单的问题走 `order`；问发货/物流规则的问题走 Dify。
- **失败降级**：Dify 4xx、超时、连接失败、空答案、响应格式异常都会转人工，不会把异常抛给客户。
- **重试策略**：自动重试 `429/5xx` 和连接错误；读超时默认不重试，避免 Dify 侧产生重复消息。

---

## 3. 当前状态（任务后）

### 3.1 阶段判断

| 阶段 | 状态 | 说明 |
| --- | --- | --- |
| V1 知识问答基线 | 已完成 | Dify + LangGraph `knowledge` 节点 + 多轮 + API + 测试 |
| V2 知识治理与评估闭环 | 未开始 | 5 项核心交付物均为空，见 3.3 |
| V3 业务 API 接入 | 未开始（有 mock） | 只有 `order` / `refund` 模拟节点 |
| V4 LangGraph 任务编排 | 未开始（有骨架） | 有图、状态和路由，无槽位、审批、恢复 |
| V5 客服工作台与人机协同 | 未开始 | 无工作台、无接管上下文流转 |
| V6 安全与可靠性 | 未开始（有部分降级） | 有超时/重试/转人工；无鉴权、隔离、限流、审计 |
| V7 上线、灰度和监控 | 未开始 | 无 Trace、看板、告警、回滚 |
| V8 商业效果验证 | 未开始 | 无指标、A/B、ROI |

**结论：当前项目是“可运行的知识问答 MVP”，不是生产级客服系统。**

### 3.2 已验证

- `uv run pytest -q`：**41 passed**。
- 真实 Dify 端到端：`退款多久到账？` → `intent=refund` → Dify 正常回答，未转人工，耗时约 10s。
- 多轮续聊：带上一轮 `conversation_id` 提问“那需要等多久？”，Dify 正确沿用退款上下文。
- 退款操作：`我要申请退款`、`把我的钱退回来，现在就执行` 均走 `refund_action`，不调用 Dify，正确转人工。
- V1 基线已冻结：代码已提交并打 `v0.1.0` tag（2026-10-26）。
- `.env` 已从 git 索引移除并加入 `.gitignore`，真实密钥不再进入后续提交。

### 3.3 V2 交付物完成度

| V2 交付物 | 当前状态 |
| --- | --- |
| 标准测试集 `eval_dataset.jsonl`（50+ 条） | ✅ 已具备：`ecommerce_cs_mvp_dataset/.../data/eval_dataset.jsonl` 共 50 条（`xq-cs-benchmark-1.0`）；待接入评测脚本 |
| 知识资产表 `knowledge_inventory.csv` | 未开始：6 份知识文档已提供，但缺元数据与资产表 |
| Bad Case 归因表 `badcase_log.csv` | 未开始 |
| 检索与回答评估脚本 | 未开始：已有 `evaluation_rubric.md` 评估口径，尚无脚本 |
| 知识库 / Prompt 版本记录 | 部分具备：`manifest.json` 记录 dataset/policy 版本；Dify 知识库与 Prompt 版本未记录 |

**按“完全具备”口径：V2 为 1/5 完成，另有 2 项部分具备。**

### 3.4 当前限制

- Dify 使用 blocking 模式，单次问答约 10–13 秒；没有流式输出。
- Dify 应用未开启“引用与归属”，`retriever_resources` 为空。
- 意图识别仍为规则版；没有实体/槽位提取、置信度、情绪识别。
- 没有鉴权、租户隔离、限流、提示词注入防护、审计。
- 订单/退款仍是 mock；没有真实订单、物流、售后、工单 API。
- 没有指标看板、Trace、告警；只在 state 中保留 usage/latency。
- 有 50 条评测集，但没有评估脚本、Bad Case 闭环和回归测试。

### 3.5 版本库与密钥

- `.env` 已从 git 索引移除（`git rm --cached`）并加入 `.gitignore`，本地文件保留；后续提交不会再包含真实密钥。
- **初始提交 `387d3ae` 中仍包含早期的 `.env`（含 `MODEL_API_KEY`）。** 若该仓库曾经推送或共享，建议轮换该密钥；如需彻底清除历史，需要重写历史，应作为单独任务执行。
- `.env.example` 仅含占位符，可安全提交。

### 3.6 基准数据包（2026-10-27 加入）

- 位置：`ecommerce_cs_mvp_dataset/ecommerce_cs_mvp_kit/`，版本 `xq-cs-benchmark-1.0`，政策版本 `2026-10-01`。
- 内容：50 条评测 case（`data/eval_dataset.jsonl`）、评估口径、6 份知识文档、订单/商品/物流/政策 mock 数据。
- 定位：V2 的回归集与知识治理输入，V3 的只读工具数据源。
- 现状：尚未接入评估脚本，尚未确认是否已导入 Dify；该目录尚未纳入 git 跟踪。

---

## 4. 建议的下一步任务

| 优先级 | 任务 | 产出 | 验收标准 | 依赖 |
| --- | --- | --- | --- | --- |
| P0 | 冻结 V1 基线 | ✅ 代码已提交 + `v0.1.0` tag；⏳ Dify 配置/版本快照待补 | 当前问答效果可复现 | 代码已完成（2026-10-26）；快照待用户提供 |
| P1 | **V2.1 接入并审阅测试集** | 校准现有 50 条 `eval_dataset.jsonl`，必要时扩充 | 覆盖 FAQ、同义改写、多轮、组合、越界、冲突、对抗、工具异常 | ✅ 50 条已提供（`xq-cs-benchmark-1.0`） |
| P1 | **V2.3 基线评估脚本** | `scripts/evaluate.py` + `eval_report.md` | 输出意图准确率、检索 Recall@K、回答准确率、转人工率、延迟、token 成本 | V2.1 + Dify 检索配置 |
| P1 | V2.2 知识资产表 | `knowledge_inventory.csv` + 元数据/版本 | 每条知识有 id、分类、意图、版本、生效/失效日期、负责人、状态 | 知识文档清单 |
| P2 | V2.3 RAG 调优实验 | E1–E6 实验记录 | 每次只改一类变量，指标可对比 | 评估脚本 + Dify 配置权限 |
| P2 | V2.4 Bad Case 归因闭环 | `badcase_log.csv` + 回归用例 | 每条失败归因到知识/检索/上下文/Prompt/模型/工作流/工具/安全 | 真实或构造 Bad Case |
| P3 | V3 只读业务 API | 模拟订单/物流/商品/售后 API | 只读工具调用 + 权限校验 + 审计 | V2 基线 + API schema |
| P3 | V4 LangGraph 编排增强 | 槽位、重试、审批、流程恢复 | 多轮任务可恢复、可审批 | V3 |

### 推荐顺序

**P0 → V2.1 → V2.3 → V2.2 → V2.4。**

原因：没有标准测试集，就无法判断 RAG 调优是否有效，也无法做 Bad Case 归因。先把“可测量”建立起来，再谈优化和扩展。

---

## 5. 下一步前需要你补充/手动完成

- [ ] 确认下一步按 **V2.1 → V2.3 → V2.2 → V2.4** 推进，或调整优先级。
- [ ] 提供/确认 Dify 知识库文档清单：文档名、业务分类、来源、负责人、生效/失效日期、当前版本（6 份知识文档已随数据包提供，仍需补齐元数据）。
- [ ] 提供 Dify 检索配置：分段策略、Embedding 模型、Top-K、Score Threshold、是否混合检索/ Rerank、LLM 模型。
- [ ] 提供退款、退货、发货、售后、投诉升级规则，包含例外和生效时间。
- [x] 已提供 50 条基准测试集（`ecommerce_cs_mvp_dataset/.../data/eval_dataset.jsonl`）；待你确认是否直接采用，以及是否需要补充真实用户表达。
- [ ] 确认每条测试的预期行为、关键事实、风险等级；可以先由我起草。
- [ ] 提供脱敏的真实会话、差评、人工纠正记录（如有）。
- [ ] 明确目标指标：自助解决率、转人工率、回答准确率、P95 延迟、单次会话成本。
- [ ] 明确人工接管规则：哪些意图、风险等级或低置信度场景必须转人工。
- [ ] 确认是否开启 Dify “引用与归属”，以便评估检索来源。
- [x] 已确认并完成：提交当前代码并打 `v0.1.0` 标签（2026-10-26）。
- [ ] 确认是否只使用当前 Dify 应用，还是需要区分测试/生产两个应用。

---

## 6. 变更记录

| 日期 | 任务 | 结果 | 更新文档 |
| --- | --- | --- | --- |
| 2026-10-25 | 在 LangGraph 中接入 Dify `knowledge` 节点 | V1 完整闭环；41 项测试通过；真实 E2E、多轮、退款操作均验证 | 本文件、`PROJECT_GAP_ANALYSIS.md`、`SOP-dify-integration.md` |
| 2026-10-26 | 冻结 V1 基线 | 提交代码并打 `v0.1.0` tag；`.env` 移出版本控制；41 项测试通过 | 本文件、`PROJECT_GAP_ANALYSIS.md` |
| 2026-10-28 | 补录基准数据包并同步 README 结构 | 确认 `ecommerce_cs_mvp_dataset/` 含 50 条评测集、6 份知识文档和 mock 数据；V2 由 0/5 调整为 1/5 完成 + 2 项部分具备 | 本文件、`PROJECT_GAP_ANALYSIS.md`、`README.md` |
