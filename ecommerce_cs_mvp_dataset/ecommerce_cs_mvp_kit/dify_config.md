## RAG 与大模型配置表


| 配置维度      | 配置项                      | 当前设定值                         |
| --------- | ------------------------ | ----------------------------- |
| **大模型生成** | 系统推理模型 (LLM)             | `Qwen/Qwen3.5-4B`             |
| **高级参数**  | 温度 (Temperature)         | **默认 (当前为 0)**                |
| **高级参数**  | 最大Token (Max Tokens)     | **默认 (当前为 512)**              |
| **高级参数**  | 核采样 (Top P)              | **默认 (当前为 1)**                |
| **高级参数**  | 词频采样 (Top K)             | **默认 (当前为 0)**                |
| **高级参数**  | 重复惩罚 (Frequency Penalty) | **默认 (当前为 0)**                |
| **高级参数**  | 响应格式 (Response Format)   | **默认 (Text 文本)**              |
| **高级参数**  | 停止词 (Stop Sequences)     | **未设置**                       |
| **知识库分段** | 分段策略 (Chunk Strategy)    | **【待补充】**                     |
| **索引方式**  | 索引模式 (Index Method)      | 高质量索引 (High Quality)          |
| **向量化**   | Embedding 模型             | `BAAI/bge-m3`                 |
| **检索策略**  | 检索模式 (Retrieval Mode)    | **向量检索 (Vector Search)**      |
| **重排**    | Rerank 模型                | `BAAI/bge-reranker-v2-m3`     |
| **召回过滤**  | 检索召回数 (Top-K)            | `3`                           |
| **召回过滤**  | 分数阈值 (Score Threshold)   | **未开启**                       |
| **语音能力**  | 语音转文本 (STT)              | `FunAudioLLM/SenseVoiceSmall` |
| **语音能力**  | 文本转语音 (TTS)              | `FunAudioLLM/CosyVoice2-0.5B` |

