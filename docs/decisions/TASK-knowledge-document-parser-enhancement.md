# TASK：Knowledge Document Parser Enhancement 产品与开发实现清单

## 背景

`Knowledge Document Upload MVP` 已经完成第一阶段闭环：

```text
.txt / .md 上传
  -> 本地保存原文件
  -> UTF-8 文本抽取
  -> 标题或长度切分
  -> 生成 draft KnowledgeItem
  -> 用户审核后启用
```

这证明了“用户资料可以进入 Workspace Knowledge Engine”。但真实客户手里的资料通常不是 `.txt` 或 `.md`，而是：

- PDF：方案、白皮书、报价说明、制度文件、合同样本。
- DOCX：SOP、需求文档、会议纪要、项目总结、培训材料。

因此 P6.2 要做的是：

> 在不引入 embedding / pgvector 的前提下，把 Knowledge Document Upload 的 parser 从 `.txt/.md` 扩展到 `.pdf/.docx`。

这一步仍然属于“结构化导入层”，不是完整 RAG。

## 产品目标

作为私有化部署用户，我希望可以直接上传常见业务文档格式，系统能抽取其中的文字并生成可审核的知识条目草稿。这样我不需要先手工把 PDF 或 Word 转成 Markdown，知识库导入成本更低。

目标链路：

```text
Admin uploads .pdf / .docx
  -> KnowledgeDocument created
  -> original file saved
  -> parser extracts text
  -> existing chunk_document splits text
  -> draft KnowledgeItems created
  -> user reviews and activates
```

## 为什么这一步先于 pgvector

pgvector 解决的是“如何更好检索已经存在的文本 chunk”。但如果大多数真实业务文档还不能被解析成文本，向量检索就没有足够可靠的输入。

因此顺序应该是：

```text
Document Upload
  -> Parser Coverage
  -> Chunk Quality
  -> Embedding / pgvector
  -> Citation / Source Trace
```

P6.2 的核心价值是提升“知识入口覆盖率”。

## 这一步解决什么场景

### 场景 1：上传 PDF 方案文档

用户上传：

```text
AI 客服系统 PoC 方案.pdf
```

系统应该：

- 保存原 PDF。
- 使用 PDF parser 抽取可选择文本。
- 生成 `parser = pdf_text_v1` 的 KnowledgeDocument。
- 生成 draft KnowledgeItem。
- 若 PDF 没有可抽取文本，则 fail-closed。

### 场景 2：上传 Word 交付 SOP

用户上传：

```text
RAG 项目交付 SOP.docx
```

系统应该：

- 保存原 DOCX。
- 抽取段落和表格中的文本。
- 复用现有 chunk 逻辑生成 draft KnowledgeItem。
- 生成 `parser = docx_text_v1` 的 KnowledgeDocument。

### 场景 3：扫描版 PDF

用户上传扫描版 PDF，里面只有图片，没有文本层。

MVP 不做 OCR。系统应该：

- 标记 KnowledgeDocument 为 `failed`。
- 不创建 KnowledgeItem。
- 返回明确错误：

```text
No extractable text found in PDF
```

### 场景 4：加密或损坏文件

加密 PDF、损坏 DOCX、非法扩展文件都应该 fail-closed：

- 不创建 KnowledgeItem。
- 记录 `knowledge_document.failed` Event。
- 前端展示错误。

## MVP 范围

### In Scope

- 扩展 `extract_text_from_upload` 支持 `.pdf`。
- 扩展 `extract_text_from_upload` 支持 `.docx`。
- 增加 parser 标识：
  - `pdf_text_v1`
  - `docx_text_v1`
- 新增后端依赖：
  - `pypdf`
  - `python-docx`
- PDF 只抽取文本层，不做 OCR。
- DOCX 抽取段落和表格文本。
- 继续复用现有本地存储、chunk、draft KnowledgeItem、Event、Workspace 隔离。
- 前端上传入口支持 `.pdf/.docx`。
- 后端测试覆盖 PDF/DOCX 成功和失败。

### Out of Scope

- 不做 OCR。
- 不做图片内容识别。
- 不做 Excel 解析。
- 不做 PPT 解析。
- 不做 PDF 版式还原。
- 不做表格结构化抽取。
- 不做 embedding。
- 不做 pgvector。
- 不做异步任务队列。
- 不做文件预览器。
- 不自动把生成条目设为 active。

## 技术方案

### PDF Parser

推荐依赖：

```text
pypdf>=5.0.0
```

原因：

- 依赖轻。
- 适合 MVP 文本层抽取。
- 不依赖系统级 Poppler。
- 私有化部署更容易安装。

实现策略：

```text
PdfReader(BytesIO(content_bytes))
  -> 检查 encrypted
  -> 遍历 pages
  -> page.extract_text()
  -> 用空行拼接 pages
  -> strip 后为空则 fail
```

错误：

```text
Encrypted PDF is not supported
No extractable text found in PDF
Failed to parse PDF
```

### DOCX Parser

推荐依赖：

```text
python-docx>=1.1.0
```

实现策略：

```text
Document(BytesIO(content_bytes))
  -> 读取 paragraphs
  -> 读取 tables rows/cells
  -> 拼接为 Markdown-ish text
  -> strip 后为空则 fail
```

表格文本可以先用：

```text
cell1 | cell2 | cell3
```

MVP 不做复杂表格结构还原。

## 后端实现清单

### BE-01：新增依赖

文件：

```text
backend/requirements.txt
```

新增：

```text
pypdf>=5.0.0
python-docx>=1.1.0
```

验收：

```text
cd backend && .venv/bin/pip install -r requirements.txt
```

在网络受限环境中，如果 PyPI 访问失败，应记录实际失败原因，不把依赖未安装误描述为测试通过。

### BE-02：扩展 SUPPORTED_EXTS

文件：

```text
backend/app/services/knowledge_documents.py
```

从：

```text
SUPPORTED_EXTS = {".txt": "text_v1", ".md": "markdown_text_v1"}
```

扩展为：

```text
SUPPORTED_EXTS = {
  ".txt": "text_v1",
  ".md": "markdown_text_v1",
  ".pdf": "pdf_text_v1",
  ".docx": "docx_text_v1",
}
```

### BE-03：拆分 parser 函数

文件：

```text
backend/app/services/knowledge_documents.py
```

建议拆成：

```text
extract_text_from_upload(...)
extract_plain_text(...)
extract_pdf_text(...)
extract_docx_text(...)
```

这样 parser 逻辑可单测，后续加 Excel/PPT/OCR 不会把一个函数堆太大。

### BE-04：实现 PDF 文本抽取

文件：

```text
backend/app/services/knowledge_documents.py
```

函数：

```text
extract_pdf_text(content_bytes: bytes) -> str
```

规则：

- 空 bytes 继续走现有 `File is empty`。
- 加密 PDF 返回 `Encrypted PDF is not supported`。
- 每页 `extract_text()`。
- 所有页面文本为空返回 `No extractable text found in PDF`。
- parser 异常包装为 `Failed to parse PDF`。

### BE-05：实现 DOCX 文本抽取

文件：

```text
backend/app/services/knowledge_documents.py
```

函数：

```text
extract_docx_text(content_bytes: bytes) -> str
```

规则：

- 读取段落。
- 读取表格单元格。
- 空文档返回 `No extractable text found in DOCX`。
- parser 异常包装为 `Failed to parse DOCX`。

### BE-06：保持后续处理不变

这些逻辑不需要重写：

- `save_knowledge_document_file`
- `_ensure_external_doc_source`
- `chunk_document`
- draft KnowledgeItem 创建
- success/failure Event
- document list/detail API
- Workspace 隔离

### BE-07：API 错误语义

现有上传 API：

```text
POST /api/v1/admin/knowledge/documents
```

保持不变。

新增 parser 后，错误仍统一返回：

```text
422
```

错误 message 应能区分：

- unsupported type
- encrypted PDF
- no PDF text
- empty DOCX
- parse failure

### BE-08：后端测试

文件：

```text
backend/tests/test_knowledge_document_upload.py
```

新增测试：

1. 上传 `.pdf` 成功创建 `KnowledgeDocument(parser=pdf_text_v1)`。
2. 上传 `.pdf` 成功生成 draft `KnowledgeItem`。
3. 上传无文本 PDF 返回 422。
4. 上传加密 PDF 返回 422。
5. 上传 `.docx` 成功创建 `KnowledgeDocument(parser=docx_text_v1)`。
6. 上传 `.docx` 成功生成 draft `KnowledgeItem`。
7. DOCX 表格文本能进入生成条目。
8. 空 DOCX 返回 422。
9. 损坏 DOCX 返回 422。
10. 原有 `.txt/.md` 测试继续通过。

测试数据建议：

- DOCX：用 `python-docx` 在测试中动态生成 BytesIO。
- 文本 PDF：优先使用小型固定 fixture bytes，或用 `pypdf` 能稳定读取的最小 fixture。
- 无文本 PDF：用 `pypdf.PdfWriter` 创建空白页。
- 加密 PDF：用 `pypdf.PdfWriter.encrypt()` 创建。

运行：

```text
cd backend && .venv/bin/python -m pytest tests/test_knowledge_document_upload.py -q
cd backend && .venv/bin/python -m pytest -q
```

## 前端实现清单

### FE-01：扩展上传 accept

文件：

```text
frontend/src/app/admin/knowledge/page.tsx
```

从：

```text
accept=".txt,.md,text/plain,text/markdown"
```

改为：

```text
accept=".txt,.md,.pdf,.docx,text/plain,text/markdown,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
```

### FE-02：更新上传文案

文件：

```text
frontend/src/app/admin/knowledge/page.tsx
```

文案：

```text
选择 TXT / Markdown / PDF / Word 文件
```

说明：

```text
支持 TXT、Markdown、PDF 文本层、Word 文档。扫描版 PDF 暂不支持 OCR。
```

### FE-03：最近文档列表展示 parser

当前已展示 parser。只需确保新 parser 可读：

```text
pdf_text_v1
docx_text_v1
```

可选增加 label map：

```text
PDF 文本
Word 文档
```

### FE-04：错误展示

现有上传失败会展示后端错误。需要确认 PDF/DOCX 的 422 错误能直接显示，让用户知道：

- 扫描版 PDF 不支持。
- 加密 PDF 不支持。
- DOCX 无可抽取文本。

### FE-05：前端验证

运行：

```text
cd frontend && npm run lint
cd frontend && npm run build
```

## API 不变

本任务不新增 API。

仍然使用：

```text
POST /api/v1/admin/knowledge/documents
GET /api/v1/admin/knowledge/documents
GET /api/v1/admin/knowledge/documents/{document_id}
```

上传成功响应结构不变：

```json
{
  "document": {
    "filename": "sop.docx",
    "file_ext": ".docx",
    "status": "processed",
    "parser": "docx_text_v1",
    "item_count": 2
  },
  "items": [...],
  "item_count": 2
}
```

## 安全与边界

### 文件大小

继续沿用：

```text
knowledge_document_max_size_mb = 2
```

PDF/DOCX 可能比纯文本大。MVP 不扩大限制，避免解析时间和内存不可控。后续可以根据真实使用情况单独调整。

### OCR 边界

扫描版 PDF 不支持。不要用“解析失败”模糊提示，应明确：

```text
No extractable text found in PDF
```

### 解析失败不污染知识库

失败时必须满足：

- `KnowledgeDocument.status = failed`
- `KnowledgeDocument.error_message` 有具体原因
- 不创建 KnowledgeItem
- 记录 `knowledge_document.failed`

### Agent 使用边界

生成条目仍然是：

```text
status = draft
```

因此 PDF/DOCX 上传内容不会未经审核直接进入 Context Builder。

## 验收标准

### 后端验收

- `.txt/.md` 上传行为不变。
- `.pdf` 上传可生成 draft KnowledgeItem。
- `.pdf` 成功时 `parser = pdf_text_v1`。
- 无文本 PDF 返回 422。
- 加密 PDF 返回 422。
- `.docx` 上传可生成 draft KnowledgeItem。
- `.docx` 成功时 `parser = docx_text_v1`。
- DOCX 段落文本能被抽取。
- DOCX 表格文本能被抽取。
- 空 DOCX 返回 422。
- 损坏 DOCX 返回 422。
- 失败时不创建 KnowledgeItem。
- 成功/失败 Event 行为不变。
- Workspace 隔离不变。
- 后端专项测试通过。
- 后端全量测试通过。

### 前端验收

- `/admin/knowledge` 上传入口可选择 `.pdf/.docx`。
- 上传说明明确支持 TXT / Markdown / PDF / Word。
- 扫描版 PDF 或加密 PDF 失败时能展示错误。
- 最近文档列表能显示 `pdf_text_v1 / docx_text_v1` 或对应 label。
- `npm run lint` 通过。
- `npm run build` 通过。

## 推荐实现顺序

### Step 1：增加依赖

先加 `pypdf` 和 `python-docx`，确认本地环境可安装。

### Step 2：后端 parser 函数

实现 `extract_pdf_text` 和 `extract_docx_text`。

### Step 3：专项测试

补 PDF/DOCX 成功和失败测试，确保 `.txt/.md` 回归通过。

### Step 4：前端上传入口

改 accept 和文案，确认错误显示。

### Step 5：全量验证

运行：

```text
backend tests/test_knowledge_document_upload.py
backend full pytest
frontend npm run lint
frontend npm run build
```

## 不建议现在做的事

- 不建议同时做 pgvector。
- 不建议同时做 OCR。
- 不建议做 PDF 版式结构还原。
- 不建议把 DOCX 表格转成复杂结构化表。
- 不建议引入后台任务队列。
- 不建议把上传生成条目设为 active。
- 不建议做文件预览器。

## 完成定义

当以下条件全部满足时，本任务完成：

```text
1. 后端依赖包含 pypdf / python-docx。
2. extract_text_from_upload 支持 .pdf。
3. extract_text_from_upload 支持 .docx。
4. PDF 成功解析后生成 draft KnowledgeItem。
5. DOCX 成功解析后生成 draft KnowledgeItem。
6. 无文本 PDF / 加密 PDF fail-closed。
7. 空 DOCX / 损坏 DOCX fail-closed。
8. .txt/.md 原有上传能力不回退。
9. /admin/knowledge 上传入口支持 PDF / Word。
10. 后端专项测试通过。
11. 后端全量测试通过。
12. 前端 lint/build 通过。
```

