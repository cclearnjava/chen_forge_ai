# TASK：Knowledge Retrieval & Citation Pack MVP 产品与开发实现清单

## 背景

ChenForge AI 当前平台化路线是：

```text
P0：Workspace MVP
P1：Event & Notification Center MVP
P2：Service Catalog MVP
P3：Workspace Knowledge Engine MVP
P4：Context Builder 接入 Sales Reply Agent
P5：External Connector MVP
P6：Vector RAG / 文档上传 / pgvector
```

当前已经完成：

```text
Knowledge Engine
  -> KnowledgeSource / KnowledgeItem
  -> Admin Knowledge UI
  -> active / draft / archived 状态

Context Builder
  -> 读取 Opportunity / Customer / Contact / Message
  -> 匹配 Service Catalog
  -> 简单匹配 active KnowledgeItem
  -> Sales Reply Agent 使用 Context Pack

Knowledge Document Upload
  -> 上传 TXT / Markdown / PDF / DOCX
  -> 解析文本
  -> 切分为 draft KnowledgeItem
  -> 用户审核后启用
```

这说明用户已经可以把自己的资料放进系统，Agent 也已经有能力读取 active KnowledgeItem。

但目前还有一个关键缺口：

> 知识检索逻辑还只是 Context Builder 内部的一段轻量匹配代码，没有形成独立的 Retrieval Contract，也没有把“为什么命中、引用了哪些来源、Agent 使用了哪些依据”稳定地结构化输出。

因此 P6.3 要做的是：

> 新增 Knowledge Retriever，并生成 Citation Pack，让 Agent 使用知识时有稳定的检索结果和可展示的引用依据。

这一步仍然不做 embedding / pgvector。它是 pgvector 前的接口冻结层。

## 产品目标

作为私有化部署用户，我希望系统在回复客户时，不只是“泛泛地参考知识库”，而是能明确告诉我：

- 这次 Agent 用了哪些知识条目。
- 这些知识为什么被选中。
- 它们来自哪个上传文档或手工知识。
- 命中内容大概是什么。
- 如果没有命中知识，系统也要明确说明。

目标链路：

```text
Customer Message / Opportunity
  -> Context Builder
  -> Knowledge Retriever
     -> active KnowledgeItems only
     -> service-linked boost
     -> keyword / tag / title / summary / content matching
     -> ranked Knowledge Hits
     -> Citation Pack
  -> Sales Reply Agent
  -> customer_reply_draft Artifact
     -> metadata.context_usage
     -> metadata.citations
  -> Admin UI shows evidence used by Agent
```

完成后，系统从“Agent 可以读取知识”升级为“Agent 使用知识可追踪、可解释、可展示”。

## 这一步解决什么场景

### 场景 1：客户问一个具体业务问题

客户说：

```text
我们想做一个企业内部知识库问答系统，先做 PoC 可以吗？
```

系统应该从当前 Workspace 的 active KnowledgeItem 中命中：

- RAG PoC 推荐范围。
- 文档质量要求。
- PoC 验收标准。
- 不建议第一期直接接生产系统的风险提示。

Agent 回复草稿应该参考这些知识，而 Artifact metadata 中应该记录 citation：

```json
{
  "knowledge_item_id": "ki_001",
  "title": "RAG PoC 验收标准",
  "source_type": "delivery_sop",
  "score": 18,
  "match_reasons": ["content", "service_link"],
  "excerpt": "PoC 阶段建议先覆盖 20-50 个高频问题..."
}
```

### 场景 2：客户需求触发合同或报价边界

客户说：

```text
我们希望你们承诺准确率 99%，并且直接上线到生产。
```

Retriever 应该优先命中：

- 合同边界。
- 风险规则。
- 交付 SOP。
- 报价规则。

Citation Pack 应该让人类审批者一眼看出 Agent 回复为什么偏谨慎。

### 场景 3：上传文档生成的知识被引用

用户上传：

```text
RAG 项目交付 SOP.docx
```

文档生成 draft KnowledgeItem，用户审核为 active。

之后客户咨询 RAG 项目交付流程时，Retriever 应该能命中这些条目，并在 citation 中保留来源信息：

```text
source_type = external_doc
metadata.document_id = xxx
metadata.chunk_index = 2
```

前端应展示：

```text
来源：外部文档 / RAG 项目交付 SOP.docx / 片段 2
```

### 场景 4：没有命中知识时 fail-soft

如果当前 Workspace 没有 active KnowledgeItem，或者没有匹配结果：

- Agent 仍然可以生成基础回复。
- Citation Pack 为空。
- Artifact metadata 记录 `knowledge_hit_count = 0`。
- 前端显示“本次回复未命中 Workspace 知识”。

### 场景 5：跨 Workspace 数据不能泄漏

Retriever 必须只读取当前 Opportunity 所属 Workspace 的 active KnowledgeItem。

任何其他 Workspace 的知识，即使关键词完全匹配，也不能进入 citation。

## MVP 范围

### In Scope

- 新增后端 `knowledge_retriever` service。
- 定义 `KnowledgeQuery` / `KnowledgeHit` / `CitationPack` 的内部结构。
- 支持基于 Opportunity + recent messages + matched services 的检索。
- 支持 KnowledgeItem 的 title / summary / content_markdown / tags_json 匹配。
- 支持 service_id 关联 boost。
- 只返回 active KnowledgeItem。
- 返回可解释字段：
  - score
  - match_reasons
  - excerpt
  - source_type
  - service_id
  - document_id
  - chunk_index
- Context Builder 改为调用 Knowledge Retriever。
- Sales Reply Artifact metadata 中记录 citation pack。
- Admin UI 展示本次 Agent 使用的知识依据。
- 后端测试覆盖排序、状态过滤、workspace 隔离、无命中 fail-soft。
- 前端测试或构建验证覆盖 metadata 展示不崩溃。

### Out of Scope

- 不做 embedding。
- 不做 pgvector。
- 不做 OpenAI embedding API。
- 不做语义相似度召回。
- 不做混合检索。
- 不做知识问答独立页面。
- 不做文档原文预览。
- 不做点击 citation 跳转到原始文件定位。
- 不做 OCR。
- 不做异步索引任务。
- 不引入新的数据库表，除非实现时发现现有 metadata 不足。

## 为什么这一步先于 pgvector

pgvector 是底层检索实现，不是产品闭环本身。

如果现在直接做 pgvector，容易出现三个问题：

1. Agent Workflow 不知道如何消费检索结果。
2. 前端不知道如何展示引用依据。
3. 后续从关键词检索切到向量检索时，业务层接口还会再次重构。

正确顺序应该是：

```text
KnowledgeItem exists
  -> Retriever contract
  -> Citation Pack
  -> Context Builder consumes Retriever
  -> UI shows citations
  -> replace keyword retrieval with pgvector later
```

P6.3 的重点不是“检索多聪明”，而是“检索结果的形状稳定”。

## 核心概念

### Knowledge Query

Knowledge Query 是 Retriever 的输入。

建议内部结构：

```text
KnowledgeQuery
  workspace_id
  opportunity_id
  query_text
  matched_service_ids
  max_hits
  include_source_types
  require_active
```

字段说明：

- `workspace_id`：强制隔离边界。
- `opportunity_id`：用于追踪本次检索来自哪个商机。
- `query_text`：Opportunity + recent messages + customer need 的组合文本。
- `matched_service_ids`：Context Builder 已匹配的 Service，用于 boost。
- `max_hits`：默认 5。
- `include_source_types`：MVP 可选，默认不限。
- `require_active`：MVP 固定 true。

### Knowledge Hit

Knowledge Hit 是单条命中结果。

建议结构：

```text
KnowledgeHit
  knowledge_item_id
  title
  summary
  source_type
  service_id
  score
  match_reasons
  excerpt
  tags
  source
```

其中 `source` 用于引用追踪：

```text
source
  source_type
  source_name
  document_id
  document_filename
  chunk_index
```

### Citation Pack

Citation Pack 是传给 Agent 和前端的引用依据包。

建议结构：

```text
CitationPack
  retriever_version
  query_summary
  hit_count
  hits
  no_hit_reason
```

示例：

```json
{
  "retriever_version": "knowledge_retriever.keyword_v1",
  "query_summary": "企业内部知识库问答系统 PoC 文档质量 验收标准",
  "hit_count": 2,
  "no_hit_reason": null,
  "hits": [
    {
      "knowledge_item_id": "ki_001",
      "title": "RAG PoC 验收标准",
      "source_type": "delivery_sop",
      "score": 18,
      "match_reasons": ["title", "content", "service_link"],
      "excerpt": "PoC 阶段建议先覆盖 20-50 个高频问题..."
    }
  ]
}
```

### Match Reason

`match_reasons` 用于解释为什么这条知识被选中。

MVP 支持：

```text
title
summary
content
tags
service_link
source_type_priority
```

## 检索策略

### 查询文本构建

Context Builder 负责构建 query text：

```text
Opportunity.title
Opportunity.problem_summary
Opportunity.desired_outcome
recent customer messages
matched service names
matched service positioning
```

Retriever 不直接依赖前端输入，它只接收后端构造好的 query。

### 基础打分

MVP 使用确定性关键词 / CJK bigram 规则。

建议权重：

```text
title match：+8
summary match：+5
tags match：+5
content match：+2 per overlap unit
service_link：+6
source_type_priority：+1 to +3
```

其中：

- `contract_boundary`、`pricing_rule`、`delivery_sop` 在销售回复场景中可有轻微优先级。
- `external_doc` 不天然低权重，避免上传文档被忽略。

### 排序

排序规则：

```text
score desc
updated_at desc
id asc
```

这样测试结果稳定，不受数据库默认顺序影响。

### Excerpt 生成

MVP 生成 160-240 字左右 excerpt：

1. 优先截取命中关键词附近文本。
2. 如果无法定位关键词，则使用 `summary`。
3. 如果 summary 为空，则使用 `content_markdown` 开头。

不需要做复杂高亮，但可以在 metadata 中保留 excerpt。

### 状态过滤

Retriever 只能读取：

```text
KnowledgeItem.status = active
KnowledgeItem.workspace_id = current_workspace_id
```

不能读取：

```text
draft
archived
other workspace
```

## 后端实现清单

### BE-01：新增 Knowledge Retriever service

新增文件：

```text
backend/app/services/knowledge_retriever.py
```

建议常量：

```text
KNOWLEDGE_RETRIEVER_VERSION = "knowledge_retriever.keyword_v1"
DEFAULT_MAX_HITS = 5
EXCERPT_LEN = 220
```

建议函数：

```python
def retrieve_knowledge_for_sales_reply(
    db: Session,
    *,
    workspace_id: str,
    query_text: str,
    matched_service_ids: list[str] | None = None,
    max_hits: int = DEFAULT_MAX_HITS,
) -> dict:
    ...
```

返回 Citation Pack dict。

### BE-02：抽出 scoring 函数

建议函数：

```python
def score_knowledge_item(item: KnowledgeItem, query_text: str, matched_service_ids: list[str]) -> tuple[int, list[str]]:
    ...
```

要求：

- title 命中记录 `title`。
- summary 命中记录 `summary`。
- content 命中记录 `content`。
- tags 命中记录 `tags`。
- service_id 命中记录 `service_link`。
- score 为 0 的 item 不返回。

### BE-03：构建 citation source

KnowledgeItem 可能来自手工录入，也可能来自上传文档。

上传文档生成的 KnowledgeItem 当前 metadata 中应包含：

```text
document_id
chunk_index
```

Retriever 应该尽量返回：

```text
document_id
chunk_index
document_filename
```

如果当前实现拿不到 `document_filename`，MVP 可以先只返回 `document_id/chunk_index`，前端展示为：

```text
外部文档 / 片段 2
```

如果能够通过 `KnowledgeDocument` 查询到 filename，则展示：

```text
外部文档 / RAG 项目交付 SOP.docx / 片段 2
```

### BE-04：Context Builder 接入 Retriever

修改：

```text
backend/app/services/context_builder.py
```

当前 `_match_knowledge` 逻辑应被替换为：

```text
retrieve_knowledge_for_sales_reply(...)
```

Context Pack 保持兼容：

```text
relevant_knowledge_items
usage.used_knowledge_item_ids
usage.knowledge_hit_count
```

同时新增：

```text
citation_pack
usage.citation_count
usage.retriever_version
```

### BE-05：Sales Reply Workflow 写入 Artifact metadata

修改：

```text
backend/app/services/sales_reply_workflow.py
```

生成 `customer_reply_draft` Artifact 时，metadata 应包含：

```json
{
  "context_usage": {
    "used_service_ids": [],
    "used_knowledge_item_ids": [],
    "knowledge_hit_count": 0,
    "citation_count": 0,
    "context_builder_version": "...",
    "retriever_version": "knowledge_retriever.keyword_v1"
  },
  "citations": {
    "retriever_version": "knowledge_retriever.keyword_v1",
    "hit_count": 0,
    "hits": []
  }
}
```

注意：

- 没有命中时 `hits=[]`，不要省略字段。
- metadata 结构要稳定，前端可直接读取。

### BE-06：事件记录

如果当前系统已有 Event Center，建议在 Agent 运行完成时记录：

```text
sales_reply.knowledge_retrieved
```

metadata：

```json
{
  "opportunity_id": "...",
  "knowledge_hit_count": 3,
  "retriever_version": "knowledge_retriever.keyword_v1"
}
```

MVP 不要求单独建检索日志表。

### BE-07：后端测试

新增测试文件：

```text
backend/tests/test_knowledge_retriever.py
```

覆盖：

1. 能按 title 命中 KnowledgeItem。
2. 能按 summary 命中 KnowledgeItem。
3. 能按 content_markdown 命中 KnowledgeItem。
4. 能按 tags_json 命中 KnowledgeItem。
5. service_id 关联会提高排序。
6. draft KnowledgeItem 不返回。
7. archived KnowledgeItem 不返回。
8. other workspace KnowledgeItem 不返回。
9. 没有命中时返回 empty citation pack。
10. 返回结构包含 retriever_version / hit_count / hits。
11. external_doc metadata 中的 document_id / chunk_index 能进入 citation source。

修改测试文件：

```text
backend/tests/test_context_builder_sales_reply.py
backend/tests/test_sales_reply_workflow.py
```

覆盖：

1. Context Pack 包含 citation_pack。
2. Artifact metadata 包含 citations。
3. 没有知识命中时 Sales Reply 仍然成功。
4. workspace 隔离仍然成立。

## 前端实现清单

### FE-01：Admin API 类型补齐

修改：

```text
frontend/src/lib/admin-api.ts
```

新增类型：

```ts
export type KnowledgeCitationHit = {
  knowledge_item_id: string;
  title: string;
  summary?: string | null;
  source_type: string;
  service_id?: string | null;
  score: number;
  match_reasons: string[];
  excerpt: string;
  source?: {
    source_type?: string | null;
    source_name?: string | null;
    document_id?: string | null;
    document_filename?: string | null;
    chunk_index?: number | null;
  };
};

export type CitationPack = {
  retriever_version: string;
  query_summary?: string | null;
  hit_count: number;
  no_hit_reason?: string | null;
  hits: KnowledgeCitationHit[];
};
```

如果 Artifact metadata 目前是 `Record<string, unknown>`，前端可以先在组件内做轻量类型收窄。

### FE-02：Agent Workbench 展示引用依据

修改：

```text
frontend/src/components/admin/agent-workbench.tsx
```

在 `customer_reply_draft` Artifact 的 context / evidence 区域展示：

```text
使用知识依据
  - RAG PoC 验收标准
    来源：交付 SOP
    命中：title / content / service_link
    摘要：PoC 阶段建议先覆盖...
```

没有命中时展示：

```text
本次回复未命中 Workspace 知识。
```

展示原则：

- 这是后台工作台，不做营销式卡片。
- 用紧凑列表或小型 evidence panel。
- 最多展示 5 条。
- score 可以展示为调试信息，但不要让它成为主视觉。

### FE-03：Opportunity Detail 展示引用依据

如果 Opportunity Detail 已经展示 Agent Artifact，则同样展示 Citation Pack。

优先复用 Agent Workbench 中的 evidence component，避免重复 UI。

建议新增组件：

```text
frontend/src/components/admin/citation-pack.tsx
```

Props：

```ts
type CitationPackProps = {
  citations?: CitationPack | null;
};
```

### FE-04：样式

修改：

```text
frontend/src/app/globals.css
```

新增样式保持后台风格：

```text
.citation-pack
.citation-list
.citation-item
.citation-meta
.citation-excerpt
.citation-empty
```

要求：

- 不做大卡片嵌套。
- 文本不能溢出。
- 长 excerpt 使用正常换行。
- match reason 使用小型 tag 样式。

## 数据结构兼容

### Artifact metadata

当前 metadata 可能已经包含：

```text
context_usage
```

本任务应该扩展，不破坏旧字段。

建议最终形态：

```json
{
  "context_usage": {
    "used_service_ids": ["svc_1"],
    "used_knowledge_item_ids": ["ki_1", "ki_2"],
    "service_hit_count": 1,
    "knowledge_hit_count": 2,
    "citation_count": 2,
    "context_builder_version": "context_builder.sales_reply.v1",
    "retriever_version": "knowledge_retriever.keyword_v1",
    "context_pack_summary": "匹配服务 1 个；命中知识 2 条"
  },
  "citations": {
    "retriever_version": "knowledge_retriever.keyword_v1",
    "query_summary": "企业内部知识库问答 PoC",
    "hit_count": 2,
    "no_hit_reason": null,
    "hits": []
  }
}
```

### relevant_knowledge_items 兼容

Context Pack 里已有：

```text
relevant_knowledge_items
```

P6.3 不删除这个字段，避免影响现有 Sales Reply 逻辑。

可以由 Citation Pack 转换得到：

```text
relevant_knowledge_items = citation_pack.hits mapped to old shape
```

## API 变化

MVP 不新增公开 API。

原因：

- Retriever 是 Context Builder 的内部能力。
- 前端通过已有 Agent Artifact metadata 看到 citations。
- Knowledge 页面仍然使用现有 Knowledge API。

如后续需要单独调试检索，可再新增：

```text
POST /api/v1/admin/knowledge/retrieve-preview
```

但本任务不做，避免扩大范围。

## 事件与通知

本任务不强制发送第三方通知。

但建议记录内部事件：

```text
knowledge.retrieved
```

或复用 Agent Run 完成事件 metadata。

未来 Event & Notification Center 可根据条件提醒：

- Agent 回复未命中任何知识。
- 命中高风险合同边界。
- 命中低质量或过期知识。

## 失败策略

### Retriever 异常

Retriever 不应该让 Sales Reply 整体失败，除非数据库或 Workspace 边界异常。

策略：

```text
正常无命中 -> fail-soft，hit_count=0
Knowledge 查询异常 -> fail-soft，metadata 标记 retriever_error
Opportunity 缺失 -> 沿用现有 fail-closed
Workspace 缺失 -> fail-closed
```

### No Hit

无命中返回：

```json
{
  "retriever_version": "knowledge_retriever.keyword_v1",
  "hit_count": 0,
  "no_hit_reason": "no_active_knowledge_matched",
  "hits": []
}
```

如果 Workspace 没有任何 active KnowledgeItem：

```text
no_hit_reason = no_active_knowledge
```

## 安全与隔离

### Workspace 隔离

所有查询必须带：

```text
KnowledgeItem.workspace_id == current_workspace_id
KnowledgeItem.status == active
```

禁止使用全局 KnowledgeItem 查询后再在 Python 层过滤 Workspace。

### 私有化部署

本任务不引入外部服务，不会把用户知识发送给第三方 embedding 或 LLM API。

这符合当前平台策略：

```text
用户私有数据留在私有化部署环境
通用能力抽象在产品内
外部模型接入后续由部署方配置
```

## 测试验收标准

### 后端验收

1. Retriever 能返回稳定 Citation Pack。
2. active KnowledgeItem 可以被检索。
3. draft KnowledgeItem 不进入 Citation Pack。
4. archived KnowledgeItem 不进入 Citation Pack。
5. 其他 Workspace 的 KnowledgeItem 不进入 Citation Pack。
6. service_id 关联 KnowledgeItem 排序靠前。
7. title / summary / content / tags 命中能记录 match_reasons。
8. external_doc 的 document_id / chunk_index 能进入 source。
9. 无 active knowledge 时 Sales Reply 不失败。
10. 无匹配 knowledge 时 Sales Reply 不失败。
11. Artifact metadata 包含 citations。
12. 后端全量测试通过。

### 前端验收

1. Agent Workbench 能展示 citation list。
2. 没有 citation 时展示空状态。
3. citation 展示 title / source_type / match_reasons / excerpt。
4. external_doc citation 能展示文档来源信息。
5. 旧 Artifact 没有 citations metadata 时页面不崩溃。
6. `npm run lint` 通过。
7. `npm run build` 通过。

## 实现顺序建议

### Step 1：后端 Retriever 单元测试

先写：

```text
backend/tests/test_knowledge_retriever.py
```

用最小数据构造：

- Workspace A / B。
- active / draft / archived KnowledgeItem。
- service-linked KnowledgeItem。
- external_doc KnowledgeItem。

先让测试失败，锁定 contract。

### Step 2：实现 knowledge_retriever.py

实现：

- query 构建之外的纯检索逻辑。
- scoring。
- match_reasons。
- citation source。
- no_hit_reason。

### Step 3：Context Builder 接入

替换 `context_builder.py` 中当前 `_match_knowledge` 逻辑。

保持旧字段兼容：

```text
relevant_knowledge_items
usage.used_knowledge_item_ids
usage.knowledge_hit_count
```

新增：

```text
citation_pack
usage.citation_count
usage.retriever_version
```

### Step 4：Sales Reply Workflow metadata

把 citation pack 写入 `customer_reply_draft` Artifact metadata。

### Step 5：前端 Citation Pack 组件

新增或复用 evidence panel：

```text
frontend/src/components/admin/citation-pack.tsx
```

接入 Agent Workbench。

### Step 6：验证

运行：

```text
cd backend && .venv/bin/python -m pytest tests/test_knowledge_retriever.py -q
cd backend && .venv/bin/python -m pytest tests/test_context_builder_sales_reply.py tests/test_sales_reply_workflow.py -q
cd backend && .venv/bin/python -m pytest -q
cd frontend && npm run lint
cd frontend && npm run build
```

## 不建议本阶段做的事

- 不建议现在接 pgvector。
- 不建议新增独立检索预览页面。
- 不建议把所有 KnowledgeItem 原文都塞进 Agent prompt。
- 不建议让 draft 知识参与检索。
- 不建议自动发送带 citation 的客户消息。
- 不建议为了 citation 新增复杂审计表。

## 完成定义

本任务完成时，应该满足：

1. 有独立 Knowledge Retriever service。
2. Retriever 返回稳定 Citation Pack。
3. Context Builder 使用 Retriever，而不是自己散落匹配 KnowledgeItem。
4. Sales Reply Artifact metadata 包含 citations。
5. 前端能展示 Agent 使用的知识依据。
6. 无知识或无命中时 fail-soft。
7. Workspace 隔离测试覆盖。
8. 后端全量测试通过。
9. 前端 lint / build 通过。

完成 P6.3 后，下一步可以进入：

```text
P6.4 Knowledge Review / Activation 体验优化
  -> 批量审核上传生成的 draft KnowledgeItem
  -> 质量检查
  -> 来源文档筛选

P6.5 Vector RAG / pgvector
  -> 在不改 Agent / UI contract 的前提下替换 Retriever 底层实现
```
