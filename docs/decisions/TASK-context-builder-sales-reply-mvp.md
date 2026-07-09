# TASK：Context Builder 接入 Sales Reply Agent MVP 产品与开发实现清单

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

P0 到 P3 已经完成三块关键地基：

```text
Workspace：数据属于哪个经营主体
Service Catalog：这个 Workspace 能卖什么服务
Knowledge Engine：这个 Workspace 有哪些私有知识、案例、FAQ、报价规则和交付经验
```

但目前这些能力主要还是后台可维护的数据。Sales Reply Agent 在生成客户回复草稿时，仍然主要依赖 Opportunity、Customer、Contact、Conversation 等基础上下文，以及确定性 mock agent 的通用规则。

本任务要完成 P4 的第一步：

> 把 Opportunity、Service Catalog、Knowledge Engine 组装成 Agent 可使用的 Context Pack，并接入 Sales Reply Agent。

完成后，Sales Reply Agent 生成 `customer_reply_draft` 时，应该能够体现当前 Workspace 的服务目录和知识库，而不是只输出通用回复。

## 产品目标

作为一人公司或小团队负责人，我希望系统在回复客户时，能够自动参考我维护过的服务目录和私有知识库，这样回复更贴近我的真实业务能力、交付边界和风险判断。

目标链路：

```text
Opportunity
  -> Context Builder
     -> Customer / Contact / Conversation
     -> Matching Services
     -> Relevant KnowledgeItems
     -> Risk Boundaries
  -> Sales Reply Agent
  -> customer_reply_draft Artifact
  -> Decision(waiting)
  -> Human Approval
```

这一步不是做真正 RAG，也不是接真实 LLM。它要先把结构化上下文流转打通，让系统从“有服务目录和知识库”升级为“Agent 能使用服务目录和知识库”。

## 这一步解决什么场景

### 场景 1：客户咨询某项服务

客户说：

```text
我们想做一个内部知识库问答系统，能不能先做 PoC？
```

系统应该能从 Service Catalog 找到相关服务，比如：

```text
RAG 知识库系统
AI Agent 落地咨询
```

再从 Knowledge Engine 找到相关知识，比如：

```text
RAG 项目常见验收标准
文档质量不足时的风险说明
PoC 第一阶段推荐范围
```

Agent 回复时应该体现：

- 推荐先做 PoC。
- 需要客户提供文档、FAQ、典型问题。
- 不直接承诺生产可用效果。
- 下一步建议做需求和资料盘点。

### 场景 2：客户需求触发风险边界

客户说：

```text
我们希望 Agent 直接操作生产数据库和业务系统。
```

如果 Knowledge Engine 或 Service Catalog 里有相关风险规则，回复草稿应该体现：

- 不能直接承诺生产自动操作。
- 建议先做只读 PoC。
- 所有生产操作需人工审批或明确安全边界。

### 场景 3：没有知识库也要 fail-soft

新用户可能还没有维护 KnowledgeItem。系统不能因此无法回复。

当没有可用知识时：

- Sales Reply Agent 仍然可以基于 Opportunity 生成基础回复。
- Artifact metadata 中记录未使用 Workspace Knowledge。
- 前端可以提示“当前回复未使用 Workspace 知识”。

### 场景 4：跨 Workspace 数据不能泄漏

Context Builder 必须严格只读取当前 Opportunity 所属 Workspace 的 Service 和 KnowledgeItem。

任何其他 Workspace 的 Service / KnowledgeItem 都不能进入 Context Pack。

## MVP 范围

### In Scope

- 新增 Context Builder service。
- 从 Opportunity 构建 Sales Reply Context Pack。
- Context Pack 包含匹配 Service 和相关 KnowledgeItem。
- Sales Reply Workflow 使用 Context Pack。
- `customer_reply_draft` Artifact 记录使用过的 service / knowledge。
- mock Sales Reply 输出能体现 service / knowledge 上下文。
- 后端测试覆盖 context、workflow、workspace 隔离和 fail-soft。
- 前端在 Opportunity 详情或 Agent Workbench 展示本次使用的 context 摘要。

### Out of Scope

- 不做向量检索。
- 不做 embedding。
- 不做 pgvector。
- 不做文档上传。
- 不接真实 LLM。
- 不改 Proposal / Quote / SOW Agent。
- 不做自动发送。
- 不做复杂服务匹配算法。
- 不做跨 Workspace 知识共享。

## 核心概念

### Context Pack

Context Pack 是传给 Agent 的结构化上下文包。

建议结构：

```text
ContextPack
  opportunity
  customer
  primary_contact
  recent_messages
  matched_services
  relevant_knowledge_items
  risk_notes
  context_summary
  usage
```

其中：

- `matched_services` 来自 Service Catalog。
- `relevant_knowledge_items` 来自 Knowledge Engine。
- `risk_notes` 来自 Service risk notes、Risk Rules、KnowledgeItem。
- `usage` 用于 Artifact 追踪。

### Context Usage

用于记录这次 Agent 使用了哪些业务资料。

建议字段：

```text
used_service_ids
used_knowledge_item_ids
context_pack_summary
context_builder_version
knowledge_hit_count
service_hit_count
```

后续前端和审计可以展示 Agent 回复依据。

## 匹配策略

MVP 不做复杂语义匹配。使用轻量确定性规则：

### Service 匹配

优先级：

1. 如果 Opportunity 已有明确 service_id，优先使用该 Service。
2. 否则用 Opportunity 的 `problem`、`desired_outcome`、最近 Message 关键词，匹配 Service 的：
   - name
   - positioning
   - target_customer
   - pain_points_json
   - outcomes_json
3. 如果没有匹配，返回 active services 的前 3 条作为候选。

### Knowledge 匹配

优先级：

1. 如果匹配到 Service，优先取 `service_id` 对应的 active KnowledgeItem。
2. 用 Opportunity 文本关键词匹配 KnowledgeItem：
   - title
   - summary
   - content_markdown
   - tags_json
3. 只返回 active KnowledgeItem。
4. 默认最多返回 5 条。

### Fail-soft

如果没有匹配到 KnowledgeItem：

- Context Pack 仍然返回。
- `relevant_knowledge_items = []`。
- `knowledge_hit_count = 0`。
- Sales Reply Agent 继续生成基础回复。

## 后端实现清单

### BE-1：新增 Context Builder service

建议新增文件：

```text
backend/app/services/context_builder.py
```

核心函数：

```python
def build_sales_reply_context_pack(db: Session, opportunity_id: str) -> dict:
    ...
```

职责：

- 读取 Opportunity。
- fail-closed：Opportunity 不存在返回 404/异常。
- 读取同 Workspace 下 Customer / Contact / Conversation / Message。
- 匹配同 Workspace 下 active Service。
- 匹配同 Workspace 下 active KnowledgeItem。
- 组装 Context Pack。

### BE-2：Context Pack 输出结构

建议输出：

```python
{
  "opportunity": {...},
  "customer": {...},
  "primary_contact": {...},
  "messages": [...],
  "matched_services": [
    {
      "id": "...",
      "name": "...",
      "positioning": "...",
      "target_customer": "...",
      "typical_duration": "...",
      "price_min": ...,
      "price_max": ...,
      "risk_notes": "..."
    }
  ],
  "relevant_knowledge_items": [
    {
      "id": "...",
      "title": "...",
      "summary": "...",
      "source_type": "...",
      "tags_json": [...],
      "content_excerpt": "..."
    }
  ],
  "risk_notes": [...],
  "context_summary": "...",
  "usage": {
    "used_service_ids": [...],
    "used_knowledge_item_ids": [...],
    "service_hit_count": 0,
    "knowledge_hit_count": 0,
    "context_builder_version": "context_builder.sales_reply.v1"
  }
}
```

### BE-3：接入 Sales Reply Workflow

当前 workflow：

```text
backend/app/services/sales_reply_workflow.py
```

需要调整：

- 在 `run_sales_reply_workflow` 中调用新的 `build_sales_reply_context_pack`。
- 保留原有 Opportunity 基础上下文。
- 将 Context Pack 传给 `generate_sales_reply`。
- AgentRun `allowed_tools` 保持 `context_builder`。
- AgentRun input/output 中记录 context usage 摘要。

### BE-4：增强 mock Sales Reply Agent

当前 mock：

```text
backend/app/services/mock_agents.py
```

需要让 `generate_sales_reply(context)` 支持：

- 如果有 matched_services，在回复中引用服务名称和交付方向。
- 如果有 relevant_knowledge_items，在回复中体现知识依据。
- 如果有 risk_notes，在回复中体现边界和谨慎表达。
- 如果没有 knowledge，仍然生成基础回复。

注意：

- 不要输出“我查阅了内部知识库”这种对客户不自然的表达。
- 可以自然表达为“基于类似 PoC 项目的经验，建议先...”。

### BE-5：Artifact metadata / content_json 追踪

在生成 `customer_reply_draft` Artifact 时，记录：

```text
content_json.context_usage.used_service_ids
content_json.context_usage.used_knowledge_item_ids
content_json.context_usage.context_pack_summary
content_json.context_usage.service_hit_count
content_json.context_usage.knowledge_hit_count
```

如果当前 Artifact 模型没有 metadata 字段，优先放进 `content_json`。

### BE-6：事件记录

可选但建议记录：

```text
context_pack.built
```

第一版可以不生成 Notification。

如果记录 Event：

- workspace_id = opportunity.workspace_id
- subject_type = opportunity
- subject_id = opportunity_id
- details_json 包含 service_hit_count / knowledge_hit_count

### BE-7：后端测试

新增或扩展：

```text
backend/tests/test_context_builder_sales_reply.py
backend/tests/test_sales_reply_workflow.py
```

测试清单：

- 有 active Service 时，Context Pack 返回 matched_services。
- 有 active KnowledgeItem 时，Context Pack 返回 relevant_knowledge_items。
- archived KnowledgeItem 不进入 Context Pack。
- draft KnowledgeItem 不进入 Context Pack。
- KnowledgeItem 关联 Service 时，优先被匹配。
- 没有 KnowledgeItem 时 fail-soft，仍可生成 customer_reply_draft。
- 不存在 Opportunity 时 fail-closed。
- 其他 Workspace 的 Service 不进入 Context Pack。
- 其他 Workspace 的 KnowledgeItem 不进入 Context Pack。
- Sales Reply Artifact content_json 记录 used_service_ids。
- Sales Reply Artifact content_json 记录 used_knowledge_item_ids。
- customer_reply_draft 文本体现匹配服务或知识摘要。
- 后端全量测试通过。

## 前端实现清单

### FE-1：Opportunity 详情展示 Context Usage

在 Opportunity 详情页或 Agent Workbench 中展示最近一次 Sales Reply 使用的上下文。

建议位置：

```text
Opportunity Detail
  -> Agent Workbench
     -> Latest Context Usage
```

展示内容：

- 使用了几个 Service。
- 使用了几个 KnowledgeItem。
- Service 名称列表。
- KnowledgeItem 标题列表。
- 如果没有使用知识，提示：

```text
当前回复未使用 Workspace 知识。可以先到 Knowledge 页面维护 FAQ、案例、报价规则或交付 SOP。
```

### FE-2：Artifact 读取 context_usage

当前前端已有 Artifact 展示逻辑。需要支持读取：

```text
artifact.content_json.context_usage
```

并展示：

```text
Context Builder v1
服务命中：N
知识命中：N
```

### FE-3：跳转入口

如果 context usage 中有 knowledge_item_ids，MVP 可以只展示标题；后续再做跳转。

如果没有知识命中，提供跳转：

```text
去维护知识库 -> /admin/knowledge
```

### FE-4：不新增复杂页面

本任务不新增 `/admin/context` 页面。

Context Builder 是后台服务能力，前端只展示 Agent 使用依据。

## 验收标准

### 产品验收

- Sales Reply Agent 回复客户时，可以使用 Workspace 的服务目录和知识条目。
- 回复草稿能自然体现服务能力、交付建议和风险边界。
- 没有知识条目时仍能生成基础回复。
- 负责人能看到本次回复使用了哪些服务和知识。
- 不会读取其他 Workspace 的服务和知识。

### 后端验收

- `build_sales_reply_context_pack` 可用。
- Context Pack 包含 Opportunity 基础上下文。
- Context Pack 包含 matched_services。
- Context Pack 包含 relevant_knowledge_items。
- archived / draft KnowledgeItem 不会进入 Context Pack。
- 跨 Workspace 数据不会进入 Context Pack。
- Sales Reply Workflow 使用 Context Pack。
- customer_reply_draft Artifact 记录 context_usage。
- 后端专项测试通过。
- 后端全量测试通过。

### 前端验收

- Opportunity 详情页或 Agent Workbench 能展示 context usage。
- 能展示 service hit count 和 knowledge hit count。
- 没有知识命中时有明确提示和 `/admin/knowledge` 入口。
- `npm run lint` 通过。
- `npm run build` 通过。

## 推荐实现顺序

### Step 1：后端 Context Builder

先实现 `backend/app/services/context_builder.py`，只返回 Context Pack，不接 workflow。

### Step 2：Context Builder 测试

先覆盖匹配 Service、匹配 Knowledge、排除 archived/draft、workspace 隔离。

### Step 3：接入 Sales Reply Workflow

让 `run_sales_reply_workflow` 使用新的 Context Pack。

### Step 4：增强 mock Sales Reply

让 mock 输出能体现服务和知识上下文。

### Step 5：Artifact context_usage

把 used_service_ids、used_knowledge_item_ids 和 summary 写入 Artifact content_json。

### Step 6：前端展示

在 Agent Workbench 或 Opportunity Detail 展示 context usage。

### Step 7：验证

运行：

```text
backend tests/test_context_builder_sales_reply.py
backend tests/test_sales_reply_workflow.py
backend full pytest
frontend npm run lint
frontend npm run build
```

## 不建议现在做的事

- 不建议引入 embedding。
- 不建议接 pgvector。
- 不建议为了 Context Builder 新增复杂 UI 页面。
- 不建议把所有 Agent 一次性改掉。
- 不建议自动发送客户回复。
- 不建议把 KnowledgeItem 原文全部塞进客户可见文本。
- 不建议做复杂机器学习匹配算法。

## 完成定义

当以下条件全部满足时，本任务完成：

```text
1. Context Builder 能根据 Opportunity 构建 Context Pack。
2. Context Pack 能匹配当前 Workspace 的 active Service。
3. Context Pack 能匹配当前 Workspace 的 active KnowledgeItem。
4. archived / draft KnowledgeItem 被排除。
5. 跨 Workspace 数据不会进入 Context Pack。
6. Sales Reply Agent 使用 Context Pack。
7. customer_reply_draft Artifact 记录 context_usage。
8. 前端能展示 context usage。
9. 没有 KnowledgeItem 时 Sales Reply fail-soft。
10. 后端专项测试通过。
11. 后端全量测试通过。
12. 前端 lint/build 通过。
```

