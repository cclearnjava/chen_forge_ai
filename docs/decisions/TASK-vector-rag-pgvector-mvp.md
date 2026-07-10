# TASK：Vector RAG / pgvector MVP 产品与开发实现清单

## 背景

ChenForge AI 当前平台化路线是：

```text
P0：Workspace MVP
P1：Event & Notification Center MVP
P2：Service Catalog MVP
P3：Workspace Knowledge Engine MVP
P4：Context Builder 接入 Sales Reply Agent
P5：External Connector MVP
P6：Workspace Knowledge Ingestion & RAG
```

当前 P6 已经完成：

```text
P6.1 Knowledge Document Upload
  -> 上传 TXT / Markdown
  -> 保存原始文件
  -> 解析文本
  -> 切分为 draft KnowledgeItem

P6.2 Parser Enhancement
  -> 支持 PDF / DOCX
  -> 扫描版 PDF / 加密文件 fail-closed

P6.3 Knowledge Retrieval & Citation Pack
  -> Retriever 输出稳定 Citation Pack
  -> Sales Reply Agent 记录 citations
  -> 前端展示 Agent 使用依据

P6.4 Knowledge Review / Activation
  -> Review Queue
  -> Quality Flags
  -> 批量启用 / 归档 / 绑定服务
  -> 只有 active KnowledgeItem 被 Retriever 使用
```

下一步 Roadmap 已经插入一个必要前置步骤：

```text
P6.5 Knowledge Quality Pipeline
  -> 自动清洗解析文本
  -> 去噪 / 去重 / 结构化
  -> 元数据补全
  -> 质量信号增强
  -> 生成更可靠的 draft KnowledgeItem
```

原因是：向量库只解决“怎么找”，不解决“被找的内容是否干净、结构是否合理、元数据是否足够”。如果直接把低质量切片向量化，召回结果仍然会不稳定。

因此本文覆盖的是 P6.6：

> 在 P6.5 Knowledge Quality Pipeline 和 P6.4 Review / Activation 之后，引入 Knowledge Vector Index 和 Hybrid Retrieval，让 Retriever 可以同时使用关键词检索和向量检索。

完整知识链路应该变成：

```text
上传资料
  -> 解析文本
  -> Knowledge Quality Pipeline
  -> 生成更可靠的 draft
  -> 人工审核 active
  -> Hybrid Retriever 检索
  -> Citation Pack
  -> Agent 使用并展示依据
```

在这个阶段引入向量检索是合适的，因为：

- 未审核的 draft 不会被向量化污染检索结果。
- Citation Pack contract 已经稳定，前端和 Agent 不需要推翻重做。
- Knowledge Quality Pipeline 和 Review / Activation 已经提高知识入库质量。
- 关键词检索在知识量变大后会遇到召回不足，需要语义检索补强。

## 产品目标

作为私有化部署用户，我希望系统在知识库越来越大以后，仍然能根据客户表达的自然语言找到相关知识。即使客户没有说中知识条目的标题或关键词，Agent 也能通过语义相似度找到合适的案例、SOP、报价规则或合同边界。

目标链路：

```text
active KnowledgeItem
  -> embedding job
  -> KnowledgeVector / vector index
  -> Hybrid Retriever
     -> keyword candidates
     -> vector candidates
     -> service-linked boost
     -> source/type/risk boost
  -> Citation Pack
  -> Sales Reply Agent
  -> Agent Workbench citations
```

完成后，用户感知应该是：

- Agent 引用的知识更相关。
- 客户表达和知识库措辞不一致时，也能命中。
- 前端仍然展示相同的 citations。
- 私有化部署可以选择 mock embedding、本地 embedding 或 OpenAI-compatible embedding provider。

## 这一步解决什么场景

### 场景 1：客户表达和知识标题不一致

知识库里有条目：

```text
标题：RAG PoC 验收标准
内容：PoC 阶段建议先覆盖高频问题、文档质量、召回准确性和人工验收流程。
```

客户说：

```text
我们想先验证一下企业知识库问答效果，要怎么判断这个方案算成功？
```

关键词检索可能只能弱命中“知识库问答”。向量检索应该能通过语义找到“PoC 验收标准”。

### 场景 2：行业用户用不同术语表达相同问题

不同行业会有自己的说法：

```text
IT：RAG 知识库
法律：合同条款问答
医美：项目咨询话术
制造业：设备维护知识库
教培：课程答疑助手
```

系统不能写死行业词典。向量检索要补上同义表达、近义需求和跨行业措辞差异。

### 场景 3：大文档拆成很多 KnowledgeItem 后，关键词召回变弱

一份 PDF 可能被切成几十个 KnowledgeItem。

用户问的问题可能只和其中一小段相关。

Hybrid Retriever 应该：

- 用关键词召回明确命中的条目。
- 用向量召回语义相关的条目。
- 合并排序后输出同一个 Citation Pack。

### 场景 4：私有化部署不想把数据发给外部服务

有些用户可以接受 OpenAI-compatible embedding API。

有些用户要求所有数据留在本地。

因此 P6.6 必须设计 provider 抽象：

```text
mock_embedding
local_embedding
openai_compatible_embedding
```

MVP 先实现 deterministic mock provider，保证本地测试和 CI 稳定；生产接入真实 provider 放在配置层。

### 场景 5：本地 MVP 使用 SQLite，生产使用 Postgres / pgvector

当前本地开发数据库是 SQLite。

生产更合适的是：

```text
Postgres
  + pgvector extension
  + object storage
```

P6.6 不能要求开发者立刻切 PostgreSQL 才能跑测试。

MVP 要支持三层过渡：

```text
本地 SQLite：embedding 存 JSON，Python 内存 cosine 检索
私有化轻量部署：Postgres 普通表 + JSON embedding，可运行但不适合大规模
生产部署：Postgres + pgvector，使用 vector index 检索
```

## MVP 范围

### In Scope

- 新增 `KnowledgeVector` 或 `KnowledgeEmbedding` 模型。
- 新增 embedding provider 抽象。
- 实现 deterministic mock embedding provider。
- 支持为 active KnowledgeItem 生成 embedding。
- draft KnowledgeItem 不生成 embedding。
- archived KnowledgeItem 不进入 vector retrieval。
- 支持 content hash，内容变化后标记 embedding stale。
- 支持手动 reindex 单条 KnowledgeItem。
- 支持批量 reindex 当前 Workspace 的 active KnowledgeItem。
- Retriever 增加 hybrid retrieval：
  - keyword candidates
  - vector candidates
  - merge / dedupe / score normalize
  - 输出现有 Citation Pack
- Citation Pack 增加可选字段：
  - `retrieval_mode`
  - `vector_score`
  - `keyword_score`
  - `embedding_model`
- Admin Knowledge 页面展示索引状态：
  - not_indexed
  - indexed
  - stale
  - failed
- 后端测试覆盖 provider、index job、状态过滤、hybrid retrieval、workspace 隔离。
- 前端 lint / build 通过。

### Out of Scope

- 不强制本地开发切换到 Postgres。
- 不要求第一版必须启用真实 pgvector。
- 不接真实 OpenAI embedding API。
- 不下载本地 embedding 模型。
- 不做异步任务队列。
- 不做后台 worker。
- 不做大规模向量索引性能优化。
- 不做 ANN 参数调优。
- 不做多模型 embedding 对比。
- 不做 reranker。
- 不做向量检索可视化。
- 不做用户上传后的自动后台索引队列。
- 不做跨 Workspace 共享向量索引。

## 核心设计原则

### 原则 1：Citation Pack contract 不变

P6.3 已经把 Agent 和前端依赖稳定在 Citation Pack 上。

P6.6 不能让前端和 Agent 感知底层是关键词还是向量。

```text
Retriever input 不变
Citation Pack output 兼容
内部召回方式可替换
```

### 原则 2：只索引 active KnowledgeItem

知识进入 Agent 前必须经过 Review / Activation。

因此：

```text
draft -> 不索引
active -> 可索引
archived -> 不参与检索
```

如果 active 变 archived，已有 embedding 可以保留，但 vector retrieval 查询时必须排除 archived。

### 原则 3：本地可测，生产可升级

不能为了 pgvector 让本地测试变复杂。

推荐分层：

```text
Embedding Provider
  -> mock provider for tests
  -> real provider later

Vector Store
  -> sqlite_json for local
  -> pgvector for production

Hybrid Retriever
  -> consumes vector candidates through interface
```

### 原则 4：私有化部署优先

用户的数据可能非常敏感。

系统必须允许：

- 不启用真实 embedding。
- 使用本地 embedding provider。
- 使用企业自有 OpenAI-compatible endpoint。
- 在配置中关闭 vector retrieval，回退 keyword retrieval。

## 核心概念

### KnowledgeVector

表示一个 KnowledgeItem 的向量索引记录。

建议模型：

```text
KnowledgeVector
  id
  workspace_id
  knowledge_item_id
  embedding_model
  provider
  content_hash
  vector_json
  vector_dim
  status
  error_message
  indexed_at
  created_at
  updated_at
```

状态：

```text
not_indexed
indexed
stale
failed
```

说明：

- `vector_json` 用于 SQLite 本地 MVP。
- 生产 pgvector 可以后续新增 `embedding vector(n)` 字段或独立表。
- `content_hash` 用于判断 KnowledgeItem 内容是否变化。
- `workspace_id` 必须冗余保存，方便隔离查询。

### Embedding Provider

Embedding Provider 负责把文本转成向量。

接口建议：

```python
class EmbeddingProvider(Protocol):
    name: str
    model: str
    dim: int

    def embed_text(self, text: str) -> list[float]:
        ...
```

MVP provider：

```text
mock_hash_embedding_v1
```

规则：

- 输入相同文本，输出相同向量。
- 不访问网络。
- 维度固定，例如 64。
- 用于测试 hybrid retrieval 的可重复行为。

后续 provider：

```text
openai_compatible_embedding
local_sentence_transformer
bge_m3_local
```

### Vector Store

Vector Store 负责保存和检索向量。

接口建议：

```python
class VectorStore(Protocol):
    def upsert_vector(...)
    def search(...)
    def mark_stale(...)
```

MVP 可先不单独抽象完整类，但代码边界必须清晰：

```text
knowledge_vectors.py
  -> index item
  -> search vectors
  -> cosine similarity
```

生产 pgvector 时替换 `search_vectors` 内部实现。

### Hybrid Retrieval

Hybrid Retrieval 合并两个候选来源：

```text
keyword hits from current retriever
vector hits from KnowledgeVector
```

最终仍输出：

```text
CitationPack
```

每条 hit 可以扩展：

```text
score
keyword_score
vector_score
match_reasons
retrieval_mode
```

`retrieval_mode` 建议值：

```text
keyword
vector
hybrid
```

## 数据模型设计

### BE-01：新增 KnowledgeVector 模型

修改：

```text
backend/app/models.py
```

新增：

```text
KnowledgeVector
  id: str
  workspace_id: str
  knowledge_item_id: str
  provider: str
  embedding_model: str
  content_hash: str
  vector_json: JSON
  vector_dim: int
  status: str
  error_message: str | None
  indexed_at: datetime | None
  created_at: datetime
  updated_at: datetime
```

索引建议：

```text
workspace_id
knowledge_item_id
status
embedding_model
```

约束建议：

```text
unique(workspace_id, knowledge_item_id, embedding_model)
```

SQLite 本地可先不强制复杂约束，但 service 层必须按这个唯一性 upsert。

### BE-02：Schemas

修改：

```text
backend/app/schemas.py
```

新增：

```text
KnowledgeVectorOut
KnowledgeVectorStatusOut
KnowledgeVectorReindexRequest
KnowledgeVectorReindexOut
KnowledgeVectorSearchDebugOut
```

MVP 前端只需要：

```text
knowledge_item_id
status
embedding_model
indexed_at
error_message
stale
```

## Embedding 与索引服务

### BE-03：Embedding Provider

新增文件：

```text
backend/app/services/embedding_provider.py
```

实现：

```text
get_embedding_provider()
MockHashEmbeddingProvider
```

Mock provider 行为：

```text
text -> normalized tokens / chars -> stable hash buckets -> vector -> L2 normalize
```

要求：

- 不访问网络。
- 输出稳定。
- 空文本 fail-closed。
- dim 固定。

### BE-04：Knowledge Vector Service

新增文件：

```text
backend/app/services/knowledge_vectors.py
```

建议函数：

```python
def knowledge_item_embedding_text(item: KnowledgeItem) -> str:
    ...

def compute_content_hash(text: str) -> str:
    ...

def get_vector_status(db: Session, workspace_id: str, item_id: str) -> dict:
    ...

def index_knowledge_item(db: Session, workspace_id: str, item_id: str) -> KnowledgeVector:
    ...

def reindex_active_knowledge(db: Session, workspace_id: str, limit: int = 100) -> dict:
    ...

def search_vectors(
    db: Session,
    workspace_id: str,
    query_text: str,
    *,
    max_hits: int = 5,
) -> list[dict]:
    ...
```

### 索引文本

Embedding 文本建议拼接：

```text
title
summary
tags
source_type
content_markdown
```

不建议把 metadata、document filename、系统字段塞进 embedding。

### Content Hash

hash 输入：

```text
title
summary
content_markdown
tags_json
source_type
service_id
```

如果 hash 变化：

- existing vector 标记 stale。
- 重新 index 后变 indexed。

### Index Rules

规则：

```text
item missing -> fail-closed
item workspace mismatch -> fail-closed
item status != active -> fail-closed / skip
empty embedding text -> failed
provider error -> failed
success -> indexed
```

## API 设计

### BE-05：Knowledge Vector API

修改：

```text
backend/app/api/knowledge.py
```

新增接口：

```text
GET /api/v1/admin/knowledge/{knowledge_id}/vector
POST /api/v1/admin/knowledge/{knowledge_id}/vector/reindex
POST /api/v1/admin/knowledge/vectors/reindex-active
```

注意路由顺序：

```text
/vectors/reindex-active
```

必须放在：

```text
/{knowledge_id}
```

之前，避免被 path capture。

### GET /admin/knowledge/{knowledge_id}/vector

返回：

```json
{
  "knowledge_item_id": "ki_1",
  "status": "indexed",
  "embedding_model": "mock_hash_embedding_v1",
  "provider": "mock",
  "vector_dim": 64,
  "content_hash": "abc",
  "stale": false,
  "indexed_at": "2026-07-10T..."
}
```

### POST /admin/knowledge/{knowledge_id}/vector/reindex

行为：

- 只允许 current workspace。
- 只允许 active item。
- 生成或更新 KnowledgeVector。

返回：

```json
{
  "knowledge_item_id": "ki_1",
  "status": "indexed",
  "embedding_model": "mock_hash_embedding_v1"
}
```

### POST /admin/knowledge/vectors/reindex-active

请求：

```json
{
  "limit": 100
}
```

返回：

```json
{
  "indexed_count": 12,
  "skipped_count": 3,
  "failed_count": 1
}
```

MVP 不做后台任务，接口同步执行，limit 最大 100。

## Retriever 改造

### BE-06：Hybrid Retrieval 接入

修改：

```text
backend/app/services/knowledge_retriever.py
```

当前版本：

```text
RETRIEVER_VERSION = "knowledge_retriever.keyword_v1"
```

P6.6 建议：

```text
RETRIEVER_VERSION = "knowledge_retriever.hybrid_v1"
```

但要保持 output 兼容。

内部流程：

```text
keyword_hits = score keyword candidates
vector_hits = search_vectors(...)
merged = merge by knowledge_item_id
apply service boost
sort by final score
build Citation Pack
```

### Score 合并

建议 MVP：

```text
final_score = keyword_score + vector_score_normalized + service_boost + source_type_bonus
```

其中：

```text
keyword_score：沿用当前 score
vector_score_normalized：cosine similarity * 20
service_boost：沿用当前 service_link
source_type_bonus：沿用当前 source_type_priority
```

### Match Reasons

新增：

```text
vector
hybrid
```

如果只由向量命中：

```text
match_reasons = ["vector"]
retrieval_mode = "vector"
```

如果关键词和向量都命中：

```text
match_reasons 包含 keyword reason + "vector"
retrieval_mode = "hybrid"
```

### No Vector Fallback

如果当前 workspace 没有任何 indexed vector：

```text
Retriever 仍然使用 keyword retrieval
Citation Pack 正常返回
metadata.vector_enabled = false
```

不能因为向量未准备好导致 Sales Reply 失败。

## 前端实现清单

### FE-01：Admin API 类型

修改：

```text
frontend/src/lib/admin-api.ts
```

新增：

```ts
export type KnowledgeVectorStatusOut = {
  knowledge_item_id: string;
  status: "not_indexed" | "indexed" | "stale" | "failed";
  provider?: string | null;
  embedding_model?: string | null;
  vector_dim?: number | null;
  indexed_at?: string | null;
  error_message?: string | null;
  stale: boolean;
};
```

新增 API：

```ts
getKnowledgeVectorStatus(id)
reindexKnowledgeItem(id)
reindexActiveKnowledge(input)
```

### FE-02：Knowledge 页面索引状态

修改：

```text
frontend/src/app/admin/knowledge/page.tsx
```

MVP 展示：

- indexed
- not indexed
- stale
- failed

可先在 Knowledge 列表行上展示状态 badge。

### FE-03：手动索引操作

支持：

```text
单条：重新索引
批量：索引当前 Workspace active 知识
```

位置建议：

- Knowledge 列表 active tab 顶部。
- 单条 row 操作区。

### FE-04：Citation Pack 显示 retrieval mode

修改：

```text
frontend/src/components/admin/citation-pack.tsx
```

在 citation meta 中展示：

```text
关键词命中
语义命中
混合命中
```

旧 Artifact 没有字段时不崩溃。

### FE-05：样式

修改：

```text
frontend/src/app/globals.css
```

新增：

```text
.vector-status-badge
.vector-status-indexed
.vector-status-stale
.vector-status-failed
.retrieval-mode-tag
```

设计原则：

- 后台工具风格，低调清晰。
- 不把 vector 状态做成主视觉。
- 失败状态要可读，但不要破坏列表密度。

## 配置与部署策略

### 本地开发

默认：

```text
VECTOR_STORE=sqlite_json
EMBEDDING_PROVIDER=mock
EMBEDDING_MODEL=mock_hash_embedding_v1
```

优点：

- 不需要 Postgres。
- 不需要网络。
- 测试稳定。

### 私有化部署

推荐配置：

```text
VECTOR_STORE=pgvector
EMBEDDING_PROVIDER=openai_compatible 或 local
EMBEDDING_BASE_URL=https://客户自己的模型网关
EMBEDDING_MODEL=bge-m3 / text-embedding-3-small / 企业自定义模型
```

用户数据流向由部署方决定。

### 生产部署

推荐：

```text
Postgres + pgvector
Object Storage
OpenAI-compatible embedding provider
Hybrid Retriever
```

但 P6.6 MVP 不要求一次性完成生产 pgvector 查询优化。

## 安全与隔离

### Workspace 隔离

所有 KnowledgeVector 查询必须带：

```text
KnowledgeVector.workspace_id == current_workspace_id
KnowledgeItem.workspace_id == current_workspace_id
```

禁止：

- 全局向量检索后 Python 层过滤 workspace。
- 一个 workspace 使用另一个 workspace 的 vector。
- 用 draft item 生成 vector。

### 数据外发控制

真实 embedding provider 会把文本发送给模型服务。

因此必须通过配置显式开启：

```text
EMBEDDING_PROVIDER=mock
```

默认值应保持本地 mock。

后续接真实 provider 时，必须在 README / env 文档说明：

```text
启用真实 embedding provider 会发送 KnowledgeItem 文本到配置的 embedding endpoint。
```

### Error Handling

Embedding 失败不能影响 Sales Reply。

规则：

```text
indexing failed -> KnowledgeVector.status = failed
vector search failed -> Retriever fallback keyword
provider unavailable -> fallback keyword
```

## 后端测试清单

新增测试文件：

```text
backend/tests/test_vector_rag_mvp.py
```

覆盖：

1. Mock provider 相同文本输出稳定向量。
2. Mock provider 空文本 fail-closed。
3. active KnowledgeItem 可以被索引。
4. draft KnowledgeItem 不能被索引。
5. archived KnowledgeItem 不参与 vector retrieval。
6. content_hash 变化后 status 可识别 stale。
7. reindex 单条 item 成功。
8. reindex-active 只索引当前 workspace active items。
9. 跨 workspace item 不能索引。
10. vector search 只返回当前 workspace items。
11. Hybrid Retriever 能返回 vector-only hit。
12. Hybrid Retriever 能合并 keyword + vector hit。
13. Citation Pack 保持 hits 结构兼容。
14. 无 vector 时 Retriever fallback keyword。
15. provider 失败时 Retriever fallback keyword。

相关回归：

```text
backend/tests/test_knowledge_retriever.py
backend/tests/test_context_builder_sales_reply.py
backend/tests/test_sales_reply_workflow.py
```

## 前端验收标准

1. Knowledge 页面能展示 vector index 状态。
2. active item 可以触发单条 reindex。
3. 可以触发当前 workspace active knowledge 批量 reindex。
4. failed / stale 状态有明确展示。
5. Citation Pack 能展示 retrieval mode。
6. 旧 citations 无 retrieval_mode 时不崩溃。
7. `npm run lint` 通过。
8. `npm run build` 通过。

## 实现顺序建议

### Step 1：模型与 schema

新增 KnowledgeVector 模型和 schema。

先让数据库能保存 embedding metadata。

### Step 2：Mock Embedding Provider

实现 deterministic mock provider。

先不接任何外部服务。

### Step 3：Knowledge Vector Service

实现：

- index single item
- reindex active items
- content_hash
- vector search with cosine similarity

### Step 4：API

新增：

```text
GET /knowledge/{id}/vector
POST /knowledge/{id}/vector/reindex
POST /knowledge/vectors/reindex-active
```

### Step 5：Retriever Hybrid

把 `knowledge_retriever.py` 改成 hybrid。

保持 Citation Pack 兼容。

### Step 6：前端最小可见

Knowledge 页面展示索引状态和 reindex 操作。

Citation Pack 展示 retrieval mode。

### Step 7：验证

运行：

```text
cd backend && .venv/bin/python -m pytest tests/test_vector_rag_mvp.py -q
cd backend && .venv/bin/python -m pytest tests/test_knowledge_retriever.py tests/test_context_builder_sales_reply.py tests/test_sales_reply_workflow.py -q
cd backend && .venv/bin/python -m pytest -q
cd frontend && npm run lint
cd frontend && npm run build
```

## 不建议本阶段做的事

- 不建议直接把本地开发切到 Postgres。
- 不建议第一版接真实 OpenAI embedding。
- 不建议在没有 Review / Activation 的情况下自动索引 draft。
- 不建议重写 Citation Pack。
- 不建议做复杂 reranker。
- 不建议做独立 RAG 问答页面。
- 不建议做大型异步 worker。

## 完成定义

本任务完成时，应该满足：

1. 系统有 KnowledgeVector 模型。
2. active KnowledgeItem 可以生成 mock embedding。
3. draft KnowledgeItem 不会生成 embedding。
4. archived KnowledgeItem 不参与向量检索。
5. Retriever 可以返回 vector-only hit。
6. Retriever 可以合并 keyword + vector hit。
7. Citation Pack 结构保持向后兼容。
8. Sales Reply Agent 不需要改业务流程即可使用 hybrid retrieval。
9. Knowledge 页面能看到索引状态。
10. 用户可以手动 reindex 单条或批量 active knowledge。
11. 没有 vector 或 provider 失败时系统 fallback keyword。
12. 后端全量测试通过。
13. 前端 lint / build 通过。

完成 P6.6 后，后续可以继续：

```text
P6.7 Real Embedding Provider
  -> OpenAI-compatible embedding
  -> local embedding model
  -> provider config / secret management

P6.8 Production pgvector
  -> vector column
  -> ivfflat / hnsw index
  -> migration docs
  -> performance tests
```
