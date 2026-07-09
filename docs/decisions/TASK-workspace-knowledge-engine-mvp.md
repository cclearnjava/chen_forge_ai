# TASK：Workspace Knowledge Engine MVP 产品与开发实现清单

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

P0 已经解决数据属于哪个 Workspace。P1 已经让系统具备事件和通知中枢。P2 已经让 Workspace 能结构化表达“自己能卖什么服务”。下一步 P3 要解决的问题是：

> 用户自己的知识、案例、方法论、FAQ、合同边界、报价规则和交付经验，如何进入系统，并成为 Agent 可使用的 Workspace 私有知识？

这是私有化部署路线里的核心能力。ChenForge AI 未来不是要求用户把最重要的客户资料和行业知识上传到中心 SaaS，而是提供一套通用系统，让用户在自己的部署环境里沉淀自己的知识库。

本 MVP 暂时不直接实现复杂 Vector RAG、文档解析、embedding 或 pgvector。第一阶段先完成轻量结构化 Knowledge Engine：

```text
Workspace
  -> KnowledgeSource
  -> KnowledgeItem
  -> Admin Knowledge UI
  -> Simple Search / Filter
```

先证明系统能保存、管理、搜索和隔离 Workspace 私有知识，再进入 Context Builder 和 Vector RAG。

## 产品定位

Workspace Knowledge Engine 不是传统文档网盘，也不是第一版就做完整 RAG 平台。

它是 Workspace 的“业务知识操作台”：

```text
服务目录：我能卖什么
知识引擎：我凭什么能卖、怎么交付、有哪些边界
Context Builder：把服务和知识组装给 Agent
```

产品上，它回答五个问题：

```text
我的业务知识放在哪里？
这些知识属于哪个 Workspace？
这些知识适用于哪些服务、客户或场景？
哪些知识可以被 Agent 使用？
哪些知识已经过期或不应再使用？
```

研发上，它提供一个稳定数据结构，让后续 Sales Reply Agent、Proposal Agent、Quote/SOW Agent 不再只依赖提示词，而是能读取 Workspace 自己维护的业务知识。

## 这一步解决什么场景

### 场景 1：用户私有知识进入系统

不同用户会有不同的核心资料：

- 行业 FAQ。
- 服务方法论。
- 客户案例。
- 报价规则。
- 合同边界。
- 交付 SOP。
- 验收标准。
- 售前问答模板。
- 风险和不承接规则。

这些资料在不同行业中名称不同，但本质上都是 Workspace 的私有知识资产。

Knowledge Engine MVP 要允许用户先用手工录入或结构化录入的方式，把这些知识保存进系统。

### 场景 2：让 Agent 有稳定可查的业务依据

如果没有 Knowledge Engine，Agent 只能根据当前商机、Service Catalog 和通用提示词生成回复。

这会导致：

- 回复不够贴近用户真实业务。
- 方案容易泛化。
- 报价和风险边界不稳定。
- 用户的行业经验无法复用。

Knowledge Engine MVP 先提供可检索知识条目，为下一步 Context Builder 接入 Sales Reply Agent 打基础。

### 场景 3：支持跨行业私有部署

ChenForge AI 未来用户可能来自 AI 咨询、软件开发、设计、法律、财税、培训、制造、医疗服务等行业。

因此 Knowledge Engine 不能写死成“AI 咨询资料库”，而要抽象成跨行业可用的知识条目：

```text
KnowledgeItem
  -> title
  -> content
  -> source_type
  -> tags
  -> status
  -> linked service
  -> confidence / visibility
```

具体行业知识由用户自己维护，系统只提供通用组织方式。

### 场景 4：为 Vector RAG 留好路径

第一版不直接做 embedding，但模型要能自然升级：

```text
KnowledgeItem
  -> later KnowledgeChunk
  -> later Embedding
  -> later Vector Index
  -> later Citation / Source Trace
```

也就是说，当前结构化知识条目不是临时方案，而是未来 RAG 的上游真相源。

## MVP 范围

### In Scope

- 后端新增 KnowledgeSource / KnowledgeItem 模型。
- KnowledgeItem 支持 workspace 隔离。
- KnowledgeItem 支持 list / create / detail / update / archive。
- KnowledgeItem 支持简单搜索和筛选。
- Admin 后台新增 `/admin/knowledge` 页面。
- 前端支持知识列表、新增、编辑、归档。
- 支持按 status、source_type、tag、service_id 筛选。
- 后端和前端验证。

### Out of Scope

- 不做文件上传。
- 不做 PDF / DOCX / Markdown 解析。
- 不做 embedding。
- 不做 pgvector。
- 不做向量相似度检索。
- 不做 Agent 自动使用 KnowledgeItem。
- 不做复杂权限系统。
- 不做知识版本 diff。
- 不做跨 Workspace 共享知识。

## 核心概念

### KnowledgeSource

表示知识来源。

示例：

```text
手工录入
客户案例
FAQ
报价规则
合同条款
交付 SOP
Service Catalog 派生
外部文档
```

第一版可以轻量实现为模型，也可以先用枚举字段表达。建议建模型，为后续文档上传和来源追踪留空间。

### KnowledgeItem

表示一条可管理、可搜索、可被 Agent 使用的知识。

示例：

```text
RAG 项目常见验收标准
AI Agent PoC 不包含生产系统自动操作
报价低于 3 万不建议承接定制开发
客户没有资料时应先做诊断服务
某行业知识库项目案例总结
```

### Knowledge Status

建议状态：

```text
draft
active
archived
```

含义：

- `draft`：草稿，还不应被 Agent 使用。
- `active`：有效知识，可被检索和后续 Context Builder 使用。
- `archived`：已归档，默认列表和检索不展示。

### Source Type

建议 source_type：

```text
manual
faq
case_study
methodology
pricing_rule
contract_boundary
delivery_sop
service_note
external_doc
```

第一版允许字符串枚举，后续可扩展。

## 后端实现清单

### BE-1：新增模型

在 `backend/app/models.py` 增加：

```text
KnowledgeSource
KnowledgeItem
```

建议字段：

```text
KnowledgeSource
  id
  workspace_id
  name
  source_type
  description
  created_at
  updated_at

KnowledgeItem
  id
  workspace_id
  source_id
  service_id
  title
  content_markdown
  summary
  source_type
  tags_json
  status
  visibility
  confidence
  metadata_json
  archived_at
  created_at
  updated_at
```

字段说明：

- `workspace_id`：必须有，所有查询必须按 Workspace 隔离。
- `source_id`：可选，关联知识来源。
- `service_id`：可选，关联 Service Catalog。
- `content_markdown`：第一版主内容。
- `summary`：短摘要，方便列表和 Agent 上下文使用。
- `tags_json`：字符串数组。
- `visibility`：第一版可用 `internal`，后续支持 `agent_usable` / `human_only`。
- `confidence`：可选，表达这条知识可靠程度。
- `metadata_json`：扩展字段，为文档来源、页码、外部系统 ID 留空间。

### BE-2：新增 schema

在 `backend/app/schemas.py` 增加：

```text
KnowledgeSourceCreate
KnowledgeSourceUpdate
KnowledgeSourceOut
KnowledgeItemCreate
KnowledgeItemUpdate
KnowledgeItemOut
KnowledgeItemListOut
```

最低校验：

- `title` 必填。
- `content_markdown` 必填。
- `status` 只能是 `draft | active | archived`。
- `source_type` 必须在允许范围内。
- `tags_json` 必须是字符串数组。
- `service_id` 如果提供，必须属于当前 Workspace。

### BE-3：新增 service 层

建议新增：

```text
backend/app/services/knowledge.py
```

职责：

- `list_knowledge_items`
- `get_knowledge_item_or_none`
- `create_knowledge_item`
- `update_knowledge_item`
- `archive_knowledge_item`
- `search_knowledge_items`
- `ensure_default_knowledge_sources`

简单搜索规则：

```text
q 命中 title / summary / content_markdown
status 默认 active
source_type 可筛选
tag 可筛选
service_id 可筛选
archived 默认不返回
```

### BE-4：新增 Admin API

建议新增：

```text
backend/app/api/knowledge.py
```

接口：

```text
GET    /api/v1/admin/knowledge
POST   /api/v1/admin/knowledge
GET    /api/v1/admin/knowledge/{knowledge_id}
PATCH  /api/v1/admin/knowledge/{knowledge_id}
POST   /api/v1/admin/knowledge/{knowledge_id}/archive

GET    /api/v1/admin/knowledge/sources
POST   /api/v1/admin/knowledge/sources
```

列表 query：

```text
q
status
source_type
tag
service_id
offset
limit
```

### BE-5：事件记录

使用已有 Event Center 记录：

```text
knowledge_item.created
knowledge_item.updated
knowledge_item.archived
knowledge_source.created
```

第一版不要求生成 Notification，先只记录 Event。

### BE-6：后端测试

新增：

```text
backend/tests/test_workspace_knowledge.py
```

测试清单：

- 创建 KnowledgeItem 成功。
- 创建时 title 必填。
- 创建时 content_markdown 必填。
- 列表默认只返回 active。
- 可以按 status 筛选 draft / archived。
- q 可以搜索 title。
- q 可以搜索 content_markdown。
- tag 筛选有效。
- source_type 筛选有效。
- service_id 筛选有效。
- detail 只能读取当前 Workspace 数据。
- update 可以修改 title / content / tags / status。
- archive 后默认列表不展示。
- 其他 Workspace 的 KnowledgeItem 不可读、不可改、不可归档。
- 全量后端测试通过。

## 前端实现清单

### FE-1：Admin API client

在 `frontend/src/lib/admin-api.ts` 增加类型：

```ts
export interface KnowledgeSourceOut {}
export interface KnowledgeItemOut {}
```

新增函数：

```text
getKnowledgeItems
getKnowledgeItem
createKnowledgeItem
updateKnowledgeItem
archiveKnowledgeItem
getKnowledgeSources
createKnowledgeSource
```

### FE-2：AdminShell 导航

在 AdminShell 中增加 Knowledge 入口：

```text
Knowledge
```

建议路由：

```text
/admin/knowledge
```

### FE-3：知识列表页

新增：

```text
frontend/src/app/admin/knowledge/page.tsx
```

页面能力：

- 展示 KnowledgeItem 列表。
- 搜索输入框。
- status 筛选。
- source_type 筛选。
- tag 搜索或筛选。
- service_id 筛选第一版可先隐藏。
- 新增按钮。
- 空状态。
- loading / error 状态。

列表展示字段：

```text
title
summary
source_type
tags
status
linked service
updated_at
```

### FE-4：知识详情 / 编辑页

可选两种方案：

方案 A：单页内 drawer / inline editor。

方案 B：独立详情页。

建议 MVP 用方案 A，减少路由和状态复杂度。

编辑字段：

```text
title
summary
content_markdown
source_type
tags
status
service_id
visibility
confidence
```

### FE-5：新增知识表单

表单要求：

- title 必填。
- content_markdown 必填。
- source_type 默认 manual。
- status 默认 active 或 draft，建议默认 draft。
- tags 用逗号分隔输入，提交时转数组。
- 保存中禁用按钮。
- 保存成功后刷新列表。

### FE-6：归档交互

列表项支持归档。

要求：

- 归档前确认。
- 归档后默认列表消失。
- 可通过 status=archived 查看。

### FE-7：页面文案

建议统一中文：

```text
知识库
新增知识
编辑知识
归档
确认归档
来源类型
标签
状态
适用服务
```

## UI 建议

Knowledge 列表页不应做成营销页。它是后台工作台，应该偏安静、密集、清晰。

建议结构：

```text
AdminShell
  Header：知识库 / Workspace 私有知识
  Toolbar：搜索、状态、来源类型、新增
  Knowledge List
    Knowledge Row
      title
      source_type badge
      status badge
      tags
      summary
      updated_at
      actions
  Editor Panel
```

空状态文案：

```text
还没有知识条目。先录入 FAQ、案例、报价规则或交付 SOP，让后续 Agent 能基于你的业务资料工作。
```

## Context Builder 前置约束

虽然本任务不接 Agent，但模型要为下一步 Context Builder 留好字段。

Context Builder 后续至少需要：

```text
title
summary
content_markdown
source_type
tags
service_id
status
visibility
confidence
updated_at
```

因此本任务不能只做一个简单 notes 表。

## 与 Service Catalog 的关系

Service Catalog 表达“能卖什么”。

Knowledge Engine 表达“怎么卖、怎么做、有哪些经验和边界”。

两者关系：

```text
Service
  -> linked KnowledgeItems
     -> FAQ
     -> case study
     -> delivery SOP
     -> pricing rule
     -> contract boundary
```

第一版 KnowledgeItem 通过可选 `service_id` 关联 Service。

后续 Context Builder 可以按 Opportunity 匹配的 Service，检索相关 KnowledgeItem。

## 验收标准

### 产品验收

- 用户可以新增 Workspace 私有知识。
- 用户可以搜索知识。
- 用户可以按状态、来源类型、标签筛选知识。
- 用户可以编辑知识。
- 用户可以归档知识。
- 已归档知识默认不出现在 active 列表。
- 知识可以选择关联某个 Service。
- 页面能清楚表达这是 Workspace 私有知识，而不是中心平台共享内容。

### 后端验收

- KnowledgeItem 有 workspace_id。
- 所有查询按 workspace_id 隔离。
- create / list / detail / update / archive API 可用。
- 简单搜索可用。
- status / source_type / tag / service_id 筛选可用。
- 非法 status / source_type 返回 422 或 400。
- 后端专项测试通过。
- 后端全量测试通过。

### 前端验收

- `/admin/knowledge` 页面可访问。
- AdminShell 有 Knowledge 导航入口。
- 列表、搜索、筛选、新增、编辑、归档可用。
- loading / error / empty 状态可用。
- 归档前有确认。
- `npm run lint` 通过。
- `npm run build` 通过。

## 推荐实现顺序

### Step 1：后端模型和 API

先完成 KnowledgeSource / KnowledgeItem 模型、schema、service、API。

原因：

- 前端依赖稳定数据契约。
- 后续 Context Builder 也依赖模型字段。

### Step 2：后端测试

完成 `test_workspace_knowledge.py`，覆盖创建、搜索、筛选、归档和 workspace 隔离。

### Step 3：前端 API client

增加 Knowledge 类型和 API client。

### Step 4：Admin 导航和列表页

新增 `/admin/knowledge` 页面，实现列表、搜索、筛选、空状态。

### Step 5：新增 / 编辑 / 归档

补表单和归档确认，让知识条目可维护。

### Step 6：验证

运行：

```text
backend tests/test_workspace_knowledge.py
backend full pytest
frontend npm run lint
frontend npm run build
```

## 不建议现在做的事

- 不建议第一版直接上 pgvector。
- 不建议第一版做复杂文件上传。
- 不建议把 KnowledgeItem 直接塞进 Sales Reply Agent。
- 不建议做跨 Workspace 知识共享。
- 不建议做过重的权限和审批。
- 不建议把知识库 UI 做成网盘。

## 完成定义

当以下条件全部满足时，本任务完成：

```text
1. KnowledgeSource / KnowledgeItem 模型存在。
2. KnowledgeItem 支持 workspace 隔离。
3. create / list / detail / update / archive API 可用。
4. 搜索和筛选可用。
5. /admin/knowledge 页面可用。
6. 用户可以新增、编辑、归档知识。
7. 后端专项测试通过。
8. 后端全量测试通过。
9. 前端 lint 通过。
10. 前端 build 通过。
```

