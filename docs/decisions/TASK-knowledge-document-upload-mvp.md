# TASK：Knowledge Document Upload MVP 产品与开发实现清单

## 背景

ChenForge AI 当前平台化路线已经完成：

```text
P0：Workspace MVP
P1：Event & Notification Center MVP
P2：Service Catalog MVP
P3：Workspace Knowledge Engine MVP
P4：Context Builder 接入 Sales Reply Agent
P5：External Connector MVP
P6：Vector RAG / 文档上传 / pgvector
```

P3 已经让用户可以手工维护 `KnowledgeSource / KnowledgeItem`。P4 已经让 Sales Reply Agent 能读取这些 KnowledgeItem。P5 已经让外部客户消息进入系统。

现在真正影响平台化和私有化部署落地的问题是：

> 用户如何把自己的资料、案例、FAQ、报价规则、合同边界、交付 SOP 放进系统，而不是一条条手工录入？

本任务是 P6 的第一阶段，但不直接做完整 Vector RAG。先完成：

```text
文档上传
  -> 本地存储原文件
  -> 文本抽取
  -> 文档切分
  -> 生成 draft KnowledgeItem
  -> 用户审核后启用
  -> Context Builder 后续可使用 active KnowledgeItem
```

这一步做完，系统就从“能手工维护知识库”升级为“能把用户自己的资料导入知识库”。

## 产品目标

作为私有化部署用户，我希望可以把自己的业务文档上传到系统中，由系统自动解析成知识条目草稿。这样我的业务知识能快速进入 Workspace Knowledge Engine，并在我审核启用后被 Agent 使用。

目标链路：

```text
Admin uploads .txt / .md
  -> KnowledgeDocument created
  -> file saved to local storage
  -> text extracted
  -> chunks generated
  -> KnowledgeItems created as draft
  -> Event recorded
  -> Admin reviews draft items
  -> active KnowledgeItems are used by Context Builder
```

## 这一步解决什么场景

### 场景 1：上传 FAQ 文档

用户有一份 FAQ：

```text
# 常见问题

## PoC 一般多久？
通常 2-4 周，取决于数据准备情况。

## 是否直接接生产系统？
第一阶段建议只读或离线数据验证。
```

系统应该：

- 保存原文件。
- 抽取文本。
- 切分为多个 KnowledgeItem 草稿。
- `source_type = external_doc`。
- `status = draft`。
- 用户确认后再启用。

### 场景 2：上传交付 SOP

用户上传 Markdown 交付流程：

```text
# RAG 项目交付 SOP

## 第一阶段：资料盘点
...

## 第二阶段：问题样例整理
...
```

系统应该把标题结构转成较小的知识条目，方便后续检索和 Context Builder 使用。

### 场景 3：上传不支持文件类型

用户上传 `.xlsx` 或未知二进制文件。

MVP 应该 fail-closed：

- 不创建 KnowledgeItem。
- KnowledgeDocument 标记为 `failed`。
- 返回明确错误。

### 场景 4：私有化部署本地存储

本地测试和私有化部署早期可以把原文件放在本机磁盘：

```text
backend/storage/knowledge_documents/{workspace_id}/{document_id}/original.ext
```

生产环境后续再替换为对象存储，不影响上层 API 和数据模型。

## MVP 范围

### In Scope

- 新增 `KnowledgeDocument` 模型。
- 支持上传 `.txt` / `.md`。
- 本地磁盘保存原文件。
- 抽取 UTF-8 文本。
- 按标题和长度切分文本。
- 自动创建 `KnowledgeSource`。
- 自动创建 draft `KnowledgeItem`。
- 上传成功/失败记录 Event。
- Admin Knowledge 页面增加上传入口。
- 上传后展示文档处理结果和生成条目数量。
- 后端测试覆盖上传、解析、切分、Workspace 隔离、失败处理。

### Out of Scope

- 不做 embedding。
- 不做 pgvector。
- 不做向量相似度检索。
- 不做 PDF 文本抽取。
- 不做 DOCX 文本抽取。
- 不做 OCR。
- 不做异步任务队列。
- 不做对象存储真实接入。
- 不做文件内容在线预览器。
- 不自动把生成的 KnowledgeItem 设为 active。
- 不自动触发 Sales Agent。

## 核心概念

### KnowledgeDocument

表示一次上传的原始文档和处理状态。

```text
KnowledgeDocument
  id
  workspace_id
  source_id
  filename
  content_type
  file_ext
  storage_path
  status
  parser
  text_excerpt
  error_message
  item_count
  metadata_json
  created_at
  updated_at
```

状态：

```text
uploaded
processing
processed
failed
archived
```

### KnowledgeItem Draft

上传文档生成的 KnowledgeItem 默认是草稿：

```text
status = draft
source_type = external_doc
source_id = document.source_id
metadata_json.document_id = document.id
metadata_json.chunk_index = n
```

原因：

- 自动解析可能产生噪声。
- 用户应先审核再启用。
- Context Builder 当前只读取 active KnowledgeItem，因此 draft 不会直接影响 Agent 输出。

## 后端实现清单

### BE-01：新增 KnowledgeDocument 模型

文件：

```text
backend/app/models.py
```

新增状态常量：

```text
KNOWLEDGE_DOCUMENT_STATUSES = ("uploaded", "processing", "processed", "failed", "archived")
```

新增模型：

```text
KnowledgeDocument
```

字段：

```text
id: String(36)
workspace_id: FK workspaces.id, index, non-null
source_id: FK knowledge_sources.id, index, nullable
filename: String(255), non-null
content_type: String(120), nullable
file_ext: String(20), index
storage_path: String(500), non-null
status: String(20), default uploaded, index
parser: String(80), nullable
text_excerpt: Text, nullable
error_message: Text, nullable
item_count: Integer, default 0
metadata_json: JSON, default {}
created_at: DateTime
updated_at: DateTime
```

### BE-02：配置本地存储目录

文件：

```text
backend/app/config.py
```

新增配置：

```text
knowledge_document_storage_dir: str = "./storage/knowledge_documents"
```

本地路径规则：

```text
storage/knowledge_documents/{workspace_id}/{document_id}/original{file_ext}
```

注意：

- API 不直接暴露本机绝对路径。
- 返回给前端的是 document id 和 storage key。

### BE-03：新增文档存储 service

文件：

```text
backend/app/services/knowledge_document_storage.py
```

职责：

- 创建目录。
- 保存上传文件 bytes。
- 返回相对 storage_path。
- 限制路径只能落在 knowledge document storage root 下。

函数建议：

```text
save_knowledge_document_file(workspace_id, document_id, filename, content: bytes) -> str
```

### BE-04：新增文本解析 service

文件：

```text
backend/app/services/knowledge_documents.py
```

支持解析：

```text
.txt
.md
```

规则：

- 使用 UTF-8 解码。
- 如果 UTF-8 解码失败，返回 failed。
- 文件为空，返回 failed。
- 单文件大小 MVP 限制为 2MB。

函数建议：

```text
extract_text_from_upload(filename, content_type, content_bytes) -> tuple[str, str]
```

返回：

```text
(parser_name, text)
```

### BE-05：文档切分

文件：

```text
backend/app/services/knowledge_documents.py
```

切分策略：

1. 优先按 Markdown 标题切分：

```text
# / ## / ###
```

2. 如果没有标题，按固定长度切分：

```text
max_chunk_chars = 1200
overlap_chars = 120
```

3. 过滤过短 chunk：

```text
min_chunk_chars = 40
```

输出结构：

```text
[
  {
    "title": "...",
    "summary": "...",
    "content_markdown": "...",
    "chunk_index": 0
  }
]
```

### BE-06：上传处理 service

文件：

```text
backend/app/services/knowledge_documents.py
```

核心函数：

```text
process_uploaded_knowledge_document(db, workspace_id, filename, content_type, content_bytes) -> dict
```

处理流程：

```text
1. 创建 KnowledgeDocument(status=uploaded)。
2. 保存原文件到本地 storage。
3. 标记 processing。
4. 抽取文本。
5. 确保 KnowledgeSource：外部文档。
6. 切分文本。
7. 为每个 chunk 创建 draft KnowledgeItem。
8. 更新 KnowledgeDocument status=processed。
9. 记录 item_count / text_excerpt / parser。
10. 记录 Event。
11. 返回 document + created items。
```

失败处理：

```text
1. KnowledgeDocument status=failed。
2. 写 error_message。
3. 不创建 KnowledgeItem。
4. 记录 Event。
5. API 返回 422。
```

### BE-07：新增 API

文件：

```text
backend/app/api/knowledge.py
```

新增接口：

```text
POST /api/v1/admin/knowledge/documents
GET /api/v1/admin/knowledge/documents
GET /api/v1/admin/knowledge/documents/{document_id}
```

上传接口：

```text
POST multipart/form-data
field: file
```

返回：

```json
{
  "document": {...},
  "items": [...],
  "item_count": 3
}
```

### BE-08：Schema

文件：

```text
backend/app/schemas.py
```

新增：

```text
KnowledgeDocumentOut
KnowledgeDocumentListOut
KnowledgeDocumentUploadOut
```

### BE-09：Event

上传成功：

```text
knowledge_document.processed
```

上传失败：

```text
knowledge_document.failed
```

Event payload：

```json
{
  "document_id": "...",
  "filename": "...",
  "item_count": 3,
  "parser": "markdown_text_v1"
}
```

### BE-10：后端测试

新增文件：

```text
backend/tests/test_knowledge_document_upload.py
```

测试用例：

1. 上传 `.txt` 成功创建 KnowledgeDocument。
2. 上传 `.md` 成功创建 draft KnowledgeItem。
3. Markdown 标题切分能生成多个 items。
4. 无标题长文本按长度切分。
5. 生成的 KnowledgeItem status 为 draft。
6. 生成的 KnowledgeItem source_type 为 external_doc。
7. 生成的 KnowledgeItem metadata_json 包含 document_id / chunk_index。
8. 不支持文件类型返回 422。
9. 空文件返回 422。
10. UTF-8 解码失败返回 422。
11. 失败时不创建 KnowledgeItem。
12. Workspace 隔离：只能看到当前 Workspace 文档。
13. 上传成功记录 Event。
14. 上传失败记录 Event。

运行：

```text
cd backend && .venv/bin/python -m pytest tests/test_knowledge_document_upload.py -q
cd backend && .venv/bin/python -m pytest -q
```

## 前端实现清单

### FE-01：扩展 admin-api

文件：

```text
frontend/src/lib/admin-api.ts
```

新增类型：

```text
KnowledgeDocumentOut
KnowledgeDocumentUploadOut
```

新增 API：

```text
uploadKnowledgeDocument(file: File)
fetchKnowledgeDocuments()
fetchKnowledgeDocument(documentId)
```

### FE-02：Knowledge 页面增加上传入口

文件：

```text
frontend/src/app/admin/knowledge/page.tsx
```

新增区域：

```text
Upload document
  -> choose file
  -> upload
  -> processing result
```

支持：

- `.txt`
- `.md`

上传完成后：

- 展示生成条目数量。
- 提示“已生成 draft KnowledgeItem，请审核后启用”。
- 刷新 Knowledge 列表。

### FE-03：Document 列表

在 `/admin/knowledge` 页面增加轻量列表：

```text
最近上传文档
  filename
  status
  item_count
  parser
  created_at
```

MVP 不做单独 `/admin/knowledge/documents` 页面。

### FE-04：Draft 状态提示

上传生成的 KnowledgeItem 默认是 draft。页面需要让用户看见 draft：

- 上传后自动切换或提示查看 `status=draft`。
- Draft item 上显示“需要审核启用”。

### FE-05：前端验证

运行：

```text
cd frontend && npm run lint
cd frontend && npm run build
```

## API 设计

### 上传文档

```http
POST /api/v1/admin/knowledge/documents
Content-Type: multipart/form-data
```

Request：

```text
file=@faq.md
```

Response：

```json
{
  "document": {
    "id": "...",
    "filename": "faq.md",
    "file_ext": ".md",
    "status": "processed",
    "parser": "markdown_text_v1",
    "item_count": 3
  },
  "items": [
    {
      "id": "...",
      "title": "PoC 一般多久？",
      "status": "draft",
      "source_type": "external_doc"
    }
  ],
  "item_count": 3
}
```

### 文档列表

```http
GET /api/v1/admin/knowledge/documents
```

Response：

```json
{
  "items": [...],
  "total": 10
}
```

## 安全与边界

### Workspace 隔离

- KnowledgeDocument 必须有 workspace_id。
- 生成的 KnowledgeSource / KnowledgeItem 必须使用同一个 workspace_id。
- list/detail API 必须按当前 Workspace 过滤。

### 文件安全

- 不信任用户 filename。
- 保存时只保留安全 basename。
- storage path 由系统生成。
- 不允许 `../` 路径穿越。
- MVP 限制文件大小 2MB。
- 不支持类型 fail-closed。

### Agent 使用边界

- 上传生成的 KnowledgeItem 默认 draft。
- Context Builder 当前只读取 active KnowledgeItem。
- 因此上传内容不会未经审核直接影响客户回复。

## 验收标准

### 后端验收

- 能上传 `.txt` 文件。
- 能上传 `.md` 文件。
- 能保存原文件到本地 storage。
- 能创建 KnowledgeDocument。
- 能创建或复用“外部文档” KnowledgeSource。
- 能生成 draft KnowledgeItem。
- Markdown 标题能切分为多个 items。
- 长文本能按长度切分。
- 不支持文件类型返回 422。
- 空文件返回 422。
- UTF-8 解码失败返回 422。
- 失败时不创建 KnowledgeItem。
- 成功/失败都记录 Event。
- Workspace 隔离正确。
- 后端专项测试通过。
- 后端全量测试通过。

### 前端验收

- `/admin/knowledge` 可以上传 `.txt` / `.md`。
- 上传中有 loading 状态。
- 上传成功展示生成条目数量。
- 上传失败展示错误。
- 页面展示最近上传文档。
- 上传后能看到 draft KnowledgeItem。
- `npm run lint` 通过。
- `npm run build` 通过。

## 推荐实现顺序

### Step 1：后端模型和 schema

先实现 `KnowledgeDocument`、schema 和基础序列化。

### Step 2：本地存储和解析 service

实现保存文件、解析 `.txt/.md`、切分文本。

### Step 3：上传 API

实现 `POST /admin/knowledge/documents`。

### Step 4：后端测试

优先覆盖成功上传、失败类型、workspace 隔离和 draft item。

### Step 5：前端上传 UI

在 `/admin/knowledge` 中加上传入口和文档列表。

### Step 6：全量验证

跑后端专项、后端全量、前端 lint/build。

## 不建议现在做的事

- 不建议直接上 pgvector。
- 不建议一开始做 PDF/DOCX 解析。
- 不建议引入异步任务队列。
- 不建议上传后自动 active。
- 不建议做复杂知识去重。
- 不建议做 citation UI。
- 不建议重构整个 Knowledge 页面。

## 完成定义

当以下条件全部满足时，本任务完成：

```text
1. KnowledgeDocument 模型存在。
2. .txt/.md 上传可用。
3. 原文件保存到本地 storage。
4. 文本能被抽取和切分。
5. 上传成功生成 draft KnowledgeItem。
6. 生成条目带 document_id / chunk_index metadata。
7. 失败类型 fail-closed。
8. Workspace 隔离正确。
9. /admin/knowledge 有上传入口。
10. /admin/knowledge 能展示上传结果和最近文档。
11. 后端专项测试通过。
12. 后端全量测试通过。
13. 前端 lint/build 通过。
```

