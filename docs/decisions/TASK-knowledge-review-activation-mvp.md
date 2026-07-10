# TASK：Knowledge Review / Activation MVP 产品与开发实现清单

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

当前 P6 已经完成三段关键能力：

```text
P6.1 Knowledge Document Upload
  -> 上传文档
  -> 保存原文件
  -> 解析文本
  -> 切分为 draft KnowledgeItem

P6.2 Parser Enhancement
  -> 支持 TXT / Markdown / PDF / DOCX
  -> 扫描版 PDF / 加密文件 fail-closed

P6.3 Knowledge Retrieval & Citation Pack
  -> Retriever 只读取 active KnowledgeItem
  -> Sales Reply Agent 生成回复时写入 citations
  -> 前端展示 Agent 使用的知识依据
```

这说明“资料进入系统”和“Agent 使用资料”已经打通。

但中间还有一个实际落地会很痛的缺口：

> 上传文档后会生成多个 draft KnowledgeItem，用户需要逐条审核、编辑、启用或归档。如果审核体验不够好，知识库很难真正变成可用资产。

因此 P6.4 要做的是：

> 提供 Knowledge Review / Activation 工作流，让用户能高效审核上传生成的草稿知识，并安全地把它们变成 Agent 可用的 active knowledge。

这一步不是做更聪明的 RAG，而是把知识入库的人机协作闭环补完整。

## 产品目标

作为私有化部署用户，我希望上传一份 PDF / Word / Markdown 后，可以快速看到它生成了哪些草稿知识，哪些质量可用、哪些需要编辑、哪些应该丢弃，并能批量启用可靠条目。这样我的资料不会直接污染 Agent，又不会因为逐条处理太麻烦而卡住。

目标链路：

```text
Admin uploads document
  -> parser creates draft KnowledgeItems
  -> Review Queue shows pending drafts
  -> user filters by document / source_type / service / quality
  -> user edits item if needed
  -> user bulk activates approved items
  -> Retriever starts using active items
  -> Agent citations can reference them
```

完成后，知识闭环从：

```text
上传 -> 草稿 -> 手动一条条处理 -> Agent 使用
```

升级为：

```text
上传 -> 草稿队列 -> 质量信号 -> 批量审核 -> Agent 可引用
```

## 这一步解决什么场景

### 场景 1：上传一个较长 PDF 后生成很多草稿

用户上传：

```text
RAG 项目交付 SOP.pdf
```

系统生成 18 条 draft KnowledgeItem。

用户希望：

- 只看这份文档生成的条目。
- 快速扫标题、摘要、正文片段。
- 看哪些条目太短或缺少摘要。
- 勾选其中 12 条批量启用。
- 剩下 6 条继续编辑或归档。

### 场景 2：草稿质量明显不足

解析后的某些条目可能是：

- 只有目录。
- 只有页眉页脚。
- 正文太短。
- 标题是乱码或无意义。
- 没有关联服务。

系统不需要用 AI 判断质量，但应该用确定性规则给出提示：

```text
正文过短
缺少摘要
没有服务关联
疑似重复标题
来源文档未启用任何条目
```

这些提示帮助用户决定是否编辑、归档或启用。

### 场景 3：用户希望安全启用知识

用户不希望上传文档后内容立刻进入 Agent。

规则必须保持：

```text
draft KnowledgeItem 不进入 Retriever
active KnowledgeItem 才会被 Agent 使用
archived KnowledgeItem 不进入 Retriever
```

P6.4 的所有批量操作都必须尊重这个边界。

### 场景 4：按业务服务整理知识

用户有多个服务：

- RAG 知识库 PoC
- AI 客服系统
- 自动化报表系统

上传文档生成的草稿如果不关联服务，Retriever 的命中质量会下降。

审核队列应该允许用户：

- 批量给选中的草稿绑定 Service。
- 按 `service_id` 筛选。
- 查看“未关联服务”的草稿。

### 场景 5：私有化部署用户需要可控入库

不同行业的用户会上传不同资料：

- IT 咨询方案。
- 法律合同模板。
- 医美服务 SOP。
- 制造业设备维护文档。
- 教培课程资料。

系统不能假设行业，也不能自动替用户启用知识。

通用抽象应该是：

```text
Draft Review
Quality Signal
Activation
Archive
Service Binding
Source Trace
```

## MVP 范围

### In Scope

- 新增 Knowledge Review Queue 后端 API。
- 支持按 draft / document_id / source_type / service_id / quality_flags 筛选。
- 支持批量启用 draft KnowledgeItem。
- 支持批量归档 draft / active KnowledgeItem。
- 支持批量绑定 service_id。
- 支持返回每条草稿的 quality_flags。
- 支持 Document detail 返回其生成的 KnowledgeItems。
- Admin Knowledge 页面增加 Review Queue 区域。
- Admin Knowledge 页面支持按文档查看生成条目。
- 前端支持勾选多条草稿并批量操作。
- 所有批量操作必须 workspace scoped。
- 记录 Event / Notification 可用的操作事件。
- 后端测试覆盖批量操作、质量信号、文档过滤、workspace 隔离。
- 前端 lint / build 通过。

### Out of Scope

- 不做 AI 自动质量评分。
- 不做 LLM 自动改写草稿。
- 不做自动启用所有草稿。
- 不做全文 diff。
- 不做文档原文预览器。
- 不做 PDF 页码级定位。
- 不做复杂审批流。
- 不做多人协同审核。
- 不做 pgvector。
- 不做 embedding。
- 不做 OCR。
- 不做知识版本历史。

## 核心概念

### Review Queue

Review Queue 是待审核知识条目的工作台视图。

它不是新模型，MVP 可以基于现有 `KnowledgeItem(status=draft)` 构建。

```text
Review Queue
  -> draft KnowledgeItems
  -> source_type = external_doc / manual / etc.
  -> metadata_json.document_id
  -> quality_flags
  -> selectable rows
  -> bulk actions
```

### Quality Flags

Quality Flags 是确定性规则，不是 AI 判断。

建议 MVP 支持：

```text
short_content
missing_summary
missing_service
duplicate_title
missing_tags
external_doc_without_document_id
```

说明：

- `short_content`：正文长度低于阈值，例如 80 字。
- `missing_summary`：summary 为空。
- `missing_service`：service_id 为空。
- `duplicate_title`：同 Workspace 下存在相同标题的非 archived 条目。
- `missing_tags`：tags_json 为空。
- `external_doc_without_document_id`：source_type 是 external_doc 但 metadata 缺 document_id。

这些 flags 不阻止启用，只做提醒。

### Bulk Action

批量操作包括：

```text
activate
archive
set_service
clear_service
```

MVP 不做复杂事务补偿。单次批量操作应在一个数据库事务里完成：

- 全部成功则 commit。
- 有非法 item 或跨 Workspace item 则 fail-closed。
- 不做部分成功。

### Document Review View

Document Review View 是从 `KnowledgeDocument` 看它生成的知识条目。

建议后端返回：

```text
KnowledgeDocumentReviewOut
  document
  items
  counts
    total
    draft
    active
    archived
  quality_summary
```

这样前端可以展示：

```text
RAG 项目交付 SOP.docx
  processed
  生成 18 条
  draft 6 / active 12 / archived 0
  质量提醒：3 条缺少摘要，2 条未关联服务
```

## 后端实现清单

### BE-01：新增 Knowledge Review service

新增文件：

```text
backend/app/services/knowledge_review.py
```

建议函数：

```python
def build_quality_flags(db: Session, workspace_id: str, item: KnowledgeItem) -> list[str]:
    ...

def list_review_items(
    db: Session,
    workspace_id: str,
    *,
    status: str = "draft",
    document_id: str | None = None,
    source_type: str | None = None,
    service_id: str | None = None,
    quality_flag: str | None = None,
) -> list[dict]:
    ...

def bulk_update_review_items(
    db: Session,
    workspace_id: str,
    *,
    item_ids: list[str],
    action: str,
    service_id: str | None = None,
) -> list[KnowledgeItem]:
    ...
```

### BE-02：Quality Flags 规则

实现确定性规则：

```text
short_content：len(content_markdown.strip()) < 80
missing_summary：not summary
missing_service：not service_id
missing_tags：tags_json 为空
duplicate_title：同 workspace 下同 title 的非 archived item 超过 1
external_doc_without_document_id：source_type=external_doc 且 metadata_json.document_id 缺失
```

注意：

- flags 只做提示，不阻止启用。
- duplicate_title 查询必须限制 workspace_id。
- archived item 不参与 duplicate_title 判断。

### BE-03：Review Queue API

修改：

```text
backend/app/api/knowledge.py
```

新增接口：

```text
GET /api/v1/admin/knowledge/review
```

Query：

```text
status=draft|active|archived
document_id
source_type
service_id
quality_flag
offset
limit
```

返回：

```json
{
  "items": [
    {
      "item": {},
      "quality_flags": ["missing_summary", "missing_service"],
      "document": {
        "id": "doc_1",
        "filename": "sop.docx"
      }
    }
  ],
  "total": 18
}
```

### BE-04：Bulk Action API

新增接口：

```text
POST /api/v1/admin/knowledge/review/bulk
```

请求：

```json
{
  "item_ids": ["ki_1", "ki_2"],
  "action": "activate",
  "service_id": null
}
```

支持 action：

```text
activate
archive
set_service
clear_service
```

规则：

- `activate`：把 item status 改为 active。
- `archive`：把 item status 改为 archived，并设置 archived_at。
- `set_service`：需要 service_id，且 service 属于当前 workspace。
- `clear_service`：service_id 置空。
- item_ids 不能为空。
- item_ids 最多 100 个。
- 任何 item 不属于当前 workspace 都返回 404 或 422。
- 不允许部分成功。

返回：

```json
{
  "updated_count": 2,
  "items": []
}
```

### BE-05：Document Review API

新增接口：

```text
GET /api/v1/admin/knowledge/documents/{document_id}/review
```

返回：

```json
{
  "document": {},
  "items": [],
  "counts": {
    "total": 18,
    "draft": 6,
    "active": 12,
    "archived": 0
  },
  "quality_summary": {
    "missing_summary": 3,
    "missing_service": 6
  }
}
```

注意：

- 必须确认 document 属于当前 workspace。
- items 必须只来自该 document 对应的 metadata_json.document_id。

### BE-06：Schemas

修改：

```text
backend/app/schemas.py
```

新增：

```text
KnowledgeReviewItemOut
KnowledgeReviewListOut
KnowledgeReviewBulkRequest
KnowledgeReviewBulkOut
KnowledgeDocumentReviewOut
```

如果现有 schema 文件已经偏大，可以先保持同文件，后续再拆。

### BE-07：Events

批量操作后记录事件：

```text
knowledge_review.bulk_activated
knowledge_review.bulk_archived
knowledge_review.bulk_service_set
knowledge_review.bulk_service_cleared
```

payload：

```json
{
  "item_ids": [],
  "updated_count": 12,
  "service_id": "svc_1"
}
```

MVP 不要求第三方通知，但 Event Center 后续可以订阅这些事件。

### BE-08：后端测试

新增测试文件：

```text
backend/tests/test_knowledge_review_activation.py
```

覆盖：

1. Review Queue 默认返回 draft items。
2. Review Queue 可按 document_id 筛选。
3. Review Queue 可按 quality_flag 筛选。
4. quality_flags 能识别 short_content。
5. quality_flags 能识别 missing_summary。
6. quality_flags 能识别 missing_service。
7. quality_flags 能识别 duplicate_title。
8. 批量 activate 后 items 变为 active。
9. 批量 archive 后 items 变为 archived。
10. 批量 set_service 要求 service 属于当前 workspace。
11. 批量 clear_service 可清空 service_id。
12. 跨 workspace item 不能被批量更新。
13. Document Review 返回 counts。
14. Document Review 只返回该 document 生成的 items。
15. Event 被记录。

## 前端实现清单

### FE-01：Admin API client

修改：

```text
frontend/src/lib/admin-api.ts
```

新增类型：

```ts
export type KnowledgeQualityFlag =
  | "short_content"
  | "missing_summary"
  | "missing_service"
  | "duplicate_title"
  | "missing_tags"
  | "external_doc_without_document_id";

export type KnowledgeReviewItemOut = {
  item: KnowledgeItemOut;
  quality_flags: KnowledgeQualityFlag[];
  document?: {
    id: string;
    filename: string;
  } | null;
};

export type KnowledgeReviewListOut = {
  items: KnowledgeReviewItemOut[];
  total: number;
};

export type KnowledgeReviewBulkRequest = {
  item_ids: string[];
  action: "activate" | "archive" | "set_service" | "clear_service";
  service_id?: string | null;
};
```

新增 API：

```ts
getKnowledgeReviewItems(params)
bulkUpdateKnowledgeReviewItems(input)
getKnowledgeDocumentReview(documentId)
```

### FE-02：Knowledge 页面增加 Review Queue

修改：

```text
frontend/src/app/admin/knowledge/page.tsx
```

新增 Review Queue 区域，建议放在上传文档区域下方、普通 Knowledge 列表上方。

功能：

- 默认展示 draft items。
- 支持按文档筛选。
- 支持按质量 flag 筛选。
- 支持按服务筛选。
- 支持多选。
- 支持批量启用。
- 支持批量归档。
- 支持批量绑定服务。
- 支持清空服务关联。

### FE-03：Quality Flags 展示

质量提示文案：

```text
short_content -> 正文偏短
missing_summary -> 缺少摘要
missing_service -> 未关联服务
duplicate_title -> 标题重复
missing_tags -> 缺少标签
external_doc_without_document_id -> 缺少来源文档
```

展示方式：

- 小型标签。
- 不要做醒目的错误态，因为这些不是阻塞错误。
- 可以用 muted warning 风格。

### FE-04：Document Review 入口

在最近文档列表每行增加一个操作：

```text
查看草稿
```

点击后：

- 设置 Review Queue 的 document_id filter。
- 滚动或切换到 Review Queue。
- 展示该文档 counts。

MVP 不需要单独页面。

### FE-05：批量操作交互

Review Queue 顶部显示：

```text
已选择 12 条
[启用] [归档] [绑定服务 dropdown] [清空服务]
```

规则：

- 未选择时按钮 disabled。
- 操作中显示 loading。
- 成功后刷新 Review Queue、普通 Knowledge 列表、Document list。
- 失败时展示 error。

### FE-06：样式

修改：

```text
frontend/src/app/globals.css
```

新增样式建议：

```text
.knowledge-review
.review-toolbar
.review-row
.review-checkbox
.quality-flags
.quality-flag
.bulk-actions
.document-review-summary
```

设计原则：

- 后台工具风格，密集但清晰。
- 不做营销页式大卡片。
- 批量操作区域固定在 Review Queue 顶部。
- 长正文片段正常换行，不挤压按钮。
- 移动端允许纵向堆叠。

## 数据与状态规则

### 状态转换

允许：

```text
draft -> active
draft -> archived
active -> archived
archived -> active
active -> draft
```

MVP 可以继续沿用现有单条编辑接口允许状态切换。

批量操作只提供：

```text
activate
archive
```

不提供批量恢复 draft，避免误操作。

### Agent 使用规则

保持不变：

```text
Retriever only reads active KnowledgeItem
```

因此：

- Review Queue 中 draft 不会影响 Agent。
- 批量 activate 后才进入 Retriever。
- 批量 archive 后立即退出 Retriever。

### Service 绑定规则

`service_id` 必须属于当前 workspace。

如果 service 不属于当前 workspace：

```text
422 service_id does not belong to this workspace
```

## API 设计细节

### GET /admin/knowledge/review

Query 示例：

```text
/api/v1/admin/knowledge/review?status=draft&document_id=doc_1&quality_flag=missing_summary
```

Response 示例：

```json
{
  "items": [
    {
      "item": {
        "id": "ki_1",
        "title": "RAG 项目验收标准",
        "status": "draft",
        "source_type": "external_doc"
      },
      "quality_flags": ["missing_service"],
      "document": {
        "id": "doc_1",
        "filename": "rag-sop.docx"
      }
    }
  ],
  "total": 1
}
```

### POST /admin/knowledge/review/bulk

Request：

```json
{
  "item_ids": ["ki_1", "ki_2"],
  "action": "activate"
}
```

Response：

```json
{
  "updated_count": 2,
  "items": []
}
```

### GET /admin/knowledge/documents/{document_id}/review

Response：

```json
{
  "document": {
    "id": "doc_1",
    "filename": "rag-sop.docx",
    "status": "processed",
    "item_count": 18
  },
  "counts": {
    "total": 18,
    "draft": 6,
    "active": 12,
    "archived": 0
  },
  "quality_summary": {
    "missing_summary": 3,
    "missing_service": 6
  },
  "items": []
}
```

## 安全与隔离

### Workspace 隔离

所有查询必须带：

```text
KnowledgeItem.workspace_id == current_workspace_id
KnowledgeDocument.workspace_id == current_workspace_id
Service.workspace_id == current_workspace_id
```

禁止：

- 先全局查 item 再 Python 层过滤。
- 批量操作时忽略 item workspace。
- 根据 metadata_json.document_id 直接读取其他 workspace document。

### 批量操作安全

批量操作必须 fail-closed：

```text
item_ids 为空 -> 422
item_ids 超过 100 -> 422
存在找不到的 item -> 404 或 422
存在其他 workspace item -> 404 或 422
service_id 不合法 -> 422
```

### 私有化部署

本任务不引入任何外部服务。

所有质量判断在本地完成，不会把用户知识发送给第三方。

## 测试验收标准

### 后端验收

1. Review Queue 默认返回 draft items。
2. Review Queue 只返回当前 workspace items。
3. Review Queue 可按 document_id 筛选。
4. Review Queue 可按 quality_flag 筛选。
5. Quality flags 覆盖 short_content / missing_summary / missing_service / duplicate_title。
6. Bulk activate 能把多条 draft 改为 active。
7. Bulk archive 能把多条 item 改为 archived。
8. Bulk set_service 校验 workspace。
9. Bulk clear_service 清空关联。
10. Document Review 返回 document + items + counts + quality_summary。
11. Document Review 不泄漏其他 workspace 的 document 或 items。
12. 操作写入 Event。
13. 后端全量测试通过。

### 前端验收

1. Knowledge 页面能看到 Review Queue。
2. 可按文档筛选草稿。
3. 可按质量 flag 筛选草稿。
4. 可多选条目。
5. 可批量启用。
6. 可批量归档。
7. 可批量绑定服务。
8. 可清空服务关联。
9. 最近文档列表可进入该文档 review 视图。
10. 操作后列表和 counts 刷新。
11. 旧 Knowledge 功能不回归。
12. `npm run lint` 通过。
13. `npm run build` 通过。

## 实现顺序建议

### Step 1：后端 Review service + tests

先写：

```text
backend/tests/test_knowledge_review_activation.py
```

锁定：

- quality flags。
- review list。
- bulk action。
- document review。
- workspace isolation。

### Step 2：实现 knowledge_review.py

实现：

- quality flag builder。
- review list。
- bulk action。
- document review aggregation。

### Step 3：API + schemas

新增 review API 和 schema。

保持现有 KnowledgeItem CRUD 不破坏。

### Step 4：前端 API client

补齐 TypeScript 类型和 API client。

### Step 5：Knowledge 页面 Review Queue

在现有页面上增加区域，不做单独路由。

优先实现：

- 文档筛选。
- quality flag 展示。
- 多选。
- 批量启用/归档。

再实现：

- 批量服务绑定。
- document review summary。

### Step 6：验证

运行：

```text
cd backend && .venv/bin/python -m pytest tests/test_knowledge_review_activation.py -q
cd backend && .venv/bin/python -m pytest tests/test_workspace_knowledge.py tests/test_knowledge_document_upload.py tests/test_knowledge_retriever.py -q
cd backend && .venv/bin/python -m pytest -q
cd frontend && npm run lint
cd frontend && npm run build
```

## 不建议本阶段做的事

- 不建议做 AI 自动总结草稿。
- 不建议自动启用全部草稿。
- 不建议做单独复杂审批系统。
- 不建议引入 pgvector。
- 不建议接 embedding。
- 不建议把 Review Queue 做成独立知识管理 SaaS。
- 不建议重构整个 Knowledge 页面。

## 完成定义

本任务完成时，应该满足：

1. 用户上传文档后可以在 Review Queue 中看到待审核草稿。
2. 用户能看到每条草稿的质量提示。
3. 用户能按文档、服务、质量问题筛选草稿。
4. 用户能批量启用草稿。
5. 用户能批量归档无效草稿。
6. 用户能批量绑定或清空服务。
7. Document Review 能展示一份文档生成的知识条目和状态统计。
8. draft 仍不会进入 Retriever。
9. active 才会被 Agent 使用。
10. 后端全量测试通过。
11. 前端 lint / build 通过。

完成 P6.4 后，下一步建议进入：

```text
P6.5 Vector RAG / pgvector
  -> 在 Review / Activation 和 Citation Pack 稳定后，引入 embedding、vector index、hybrid retrieval
```
