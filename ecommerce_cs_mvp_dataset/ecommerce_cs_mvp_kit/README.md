# 星桥优选智能客服 MVP 数据包

## 重要说明
本包是一套**人工设计、内部一致的合成基准数据**，并非声称来自真实商家或真实用户的会话。它用于先跑通 V1–V8 的工程闭环。公开真实语料链接见 `SOURCES.md`，可后续用于补充真实用户表达，不应直接替代带标准答案的业务测试集。

商家：星桥优选（虚构）
数据版本：`xq-cs-benchmark-1.1.1`（基准集）
政策版本：`2026-10-01`
案例数：50（基准集）
覆盖类目：服装、数码电子、家居、美妆个护、图书、食品、宠物用品、运动用品、数字商品、交易、物流、安全、知识治理、端到端。

## 文件
- `data/eval_dataset.jsonl`：基准集（golden set），一行一个 JSON case；只在评分口径变化时升版本。
- `data/regression_dataset.jsonl`：回归集，从 Bad Case / 线上样本追加，只增不升版本。
- `data/manifest.json`：数据集身份与统计（版本、sha256、分布、历史版本 → git tag）。
- `data/eval_dataset.csv`：1.0 人工审阅版（只读）。
- `data/evaluation_rubric.md`：评估口径。
- `knowledge_base/`：建议导入 Dify 的知识文档。
- `mock_api/merchant_policy.json`：统一规则的结构化源文件。
- `mock_api/products.json`：商品/SKU/库存。
- `mock_api/orders.json`：演示订单，含测试验证码。
- `mock_api/tracking.json`：演示物流。
- `SOURCES.md`：真实公开语料来源与使用边界。
- `reports/`：用于保存基线与回归测试结果。

## 建议的 V1–V8 用法
- V1：只导入 `knowledge_base/`，运行不依赖 API 的 FAQ/政策问题。
- V2：将 50 条作为固定回归集，记录召回、证据完整性、答案正确性、Bad Case 标签。
- V3：将 `mock_api/` 做成只读/受控写入的 FastAPI mock 服务，工具结果必须覆盖静态知识里的动态状态。
- V4：LangGraph 做意图路由、槽位收集、核验、工具调用、重试与人工接管。
- V5：增加工单、交接上下文、处理结果回流字段。
- V6：跑隐私、提示词注入、越权、未知属性、冲突规则测试。
- V7：为每次运行记录 dataset_version、policy_version、prompt_version、retriever_config、model、trace_id，并支持回归比较。
- V8：在可控流量或离线模拟中评估解决率、转人工率、响应时延、单次成本；合成数据只能证明工程能力，不能证明真实商业 ROI。

## Dify 知识库导入建议
先按文件导入，检查分段预览。建议将每份 Markdown 作为单独文档，保留标题。第一轮不要同时调多个变量。
- 基线 A：普通分段，保留标题/章节边界。
- 对比 B：父子分段（若当前 Dify 知识库模式支持）。
- FAQ 可单独整理为问答分段或一问一答知识单元。
使用同一批固定 case 对比，避免因为同时改 prompt、top-k 和分段导致无法归因。

## 先跑的 10 个 case
CS001、CS004、CS007、CS013、CS017、CS029、CS031、CS034、CS043、CS048。
它们分别覆盖基本规则、例外、未知属性、实时库存、类目例外、退款时效、优惠券规则、发票、隐私安全、知识版本治理。

## 数据纪律
- 基准集与回归集分开：Bad Case 只追加到 `regression_dataset.jsonl`，不要改写基准集，否则历史分数不可比。
- 不要改写原始 case 后仍沿用相同 dataset_version；变更时升版本。
- 旧版本不复制文件，用 git tag 保存（如 `benchmark-1.0`）；评估报告记录 `dataset_version` + `git_commit` + `sha256`。
- 新增/修改规则时同步更新知识文档、mock 数据、expected_behavior 和回归结果。
- 订单号、验证码仅为本地模拟数据，禁止用于真实系统。
- 所有数据均为演示用虚构数据；日期逻辑需在测试运行时固定 `as_of_date`，不要将当前日期硬编码进 RAG 文档。
