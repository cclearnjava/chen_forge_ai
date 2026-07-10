# TASK：Knowledge Quality Pipeline MVP 产品与开发需求文档

## 1. 文档目的

本文定义 ChenForge AI 平台化路线中 P6.5「Knowledge Quality Pipeline MVP」的产品需求、后端实现清单、前端实现清单、数据契约、验收标准与测试范围。

这一步的目标不是马上提升成“最强 RAG”，而是在进入 Vector RAG / pgvector 之前，先把用户上传资料变成更干净、更可审核、更适合检索的 KnowledgeItem。

## 2. 背景

当前知识库链路已经具备基础闭环：

```text
Workspace
  -> Document Upload
  -> Parser extracts text
  -> creates draft KnowledgeItem
  -> Review Queue
  -> activate KnowledgeItem
  -> Retriever / Citation Pack
  -> Sales Reply Agent uses workspace knowledge
```

但在真实客户环境里，RAG 的效果通常不是因为“没有向量数据库”才差，而是因为知识源质量不稳定：

- PDF / DOCX 里有页眉、页脚、页码、目录、版权声明。
- 文档解析后出现断行、空行、重复段落。
- 一个文档里混合了报价、介绍、FAQ、合同条款等多种内容。
- chunk 太短、太碎或没有标题。
- 同一段业务说明在多个文档中重复出现。
- 用户的行业术语和客户提问表达不一致。

如果把这些内容直接写入向量库，向量召回只会把“脏数据”更快地召回出来。  
所以 P6.5 必须先做 Knowledge Quality Pipeline，P6.6 再做 Vector RAG / pgvector 的正式产品化接入。

## 3. 产品定位

Knowledge Quality Pipeline 是一个本地、确定性、可审计的知识预处理能力。

它解决的问题是：

```text
用户上传的原始资料不够干净
  -> 系统在用户自己的部署环境内自动做基础清洗和质量标记
  -> 生成更适合审核和检索的 draft KnowledgeItem
  -> 用户只需要在 Review Queue 判断能不能启用
```

它不是：

- 不是人工代客户整理资料。
- 不是平台方读取客户数据后做清洗。
- 不是 LLM 自动改写客户资料。
- 不是 embedding 或向量数据库。
- 不是 OCR 或复杂版式还原。

## 4. 核心用户故事

### 用户故事 1：私有化用户上传资料后自动清洗

作为私有化部署用户，我希望直接上传自己的业务资料，不需要先手工删除页码、页眉、重复段落和空行。系统应在本地自动处理这些明显噪音，并生成可审核草稿。

验收结果：

- 原始文件保持不变。
- 系统生成的 KnowledgeItem 使用清洗后的文本。
- Review Queue 能看到对应质量提示。

### 用户故事 2：用户不希望平台方看到自己的数据

作为企业用户，我希望我的业务资料只在自己的部署环境内被处理，不默认发送给外部模型、外部 API 或平台服务。

验收结果：

- MVP 不调用外部 LLM、embedding 服务或清洗服务。
- 清洗规则 deterministic，可本地测试和审计。
- 文档 metadata 记录 pipeline version，便于后续追踪。

### 用户故事 3：运营人员能判断知识草稿是否可靠

作为后台运营人员，我希望 Review Queue 不只显示草稿内容，还能提示“清洗后内容偏短”“疑似重复”“移除较多噪音”等问题，帮助我决定是否启用。

验收结果：

- Review Queue 展示新增 quality flags。
- flags 只提示，不自动阻止启用。
- 用户可以继续 approve / reject / edit 当前草稿。

### 用户故事 4：后续 Vector RAG 有更干净的输入

作为系统开发者，我希望进入向量索引前，KnowledgeItem 已经具备基本质量信息，避免把明显噪音、重复内容和无意义 chunk 写入向量库。

验收结果：

- draft KnowledgeItem metadata 包含清洗统计和质量标记。
- 后续 reindex 可以读取这些 metadata。
- 质量 pipeline 有版本号，未来规则升级可追溯。

## 5. 这一步解决的场景问题

### 场景 1：PDF 页码和页眉页脚污染

用户上传方案 PDF 后，解析文本可能出现：

```text
ChenForge AI Confidential
Page 3 of 18
...
ChenForge AI Confidential
Page 4 of 18
```

如果不清洗，retriever 可能命中这些无业务价值内容。  
MVP 应删除明显页码行、重复页眉页脚和连续重复噪音。

### 场景 2：DOCX / PDF 断行导致 chunk 可读性差

解析文本可能出现：

```text
我们为客户提供
AI 咨询、系统集成
和自动化交付服务。
```

MVP 应尽量把同一自然段落合并成：

```text
我们为客户提供 AI 咨询、系统集成和自动化交付服务。
```

### 场景 3：重复段落导致召回结果单一

多个 chunk 中重复出现同一段介绍，会让 retriever 重复召回同质内容。  
MVP 需要在单次文档处理内去除连续重复段落，并给疑似重复 chunk 打标。

### 场景 4：内容太短或标题太弱

解析后的 chunk 可能只有：

```text
服务介绍
```

这种内容不适合进入检索主链路。  
MVP 不自动删除所有短内容，但要打 `very_short_after_cleaning` 或 `weak_title`，交给 Review Queue 审核。

### 场景 5：用户不想看到复杂清洗过程

用户只关心：

- 上传是否成功。
- 生成多少条草稿。
- 哪些草稿需要注意。
- 启用后 Agent 能不能引用。

因此前端只展示质量摘要和 flags，不暴露复杂算法细节。

## 6. 设计原则

1. **原始资料不可变**：上传文件和原始解析结果不能被覆盖。
2. **默认本地处理**：MVP 不调用任何外部模型或第三方清洗服务。
3. **确定性优先**：清洗规则必须稳定、可测试、可回放。
4. **提示优先于阻断**：质量 flags 只提醒用户，不自动阻止 activate。
5. **保守清洗**：宁可少删，也不能误删重要业务内容。
6. **版本可追踪**：清洗 pipeline 必须有 version 写入 metadata。
7. **后续可升级**：未来可接入行业模板、LLM 摘要、向量质量评分，但不塞进 MVP。

## 7. MVP 范围

### 7.1 In Scope

后端：

- 新增 `backend/app/services/knowledge_quality.py`。
- 对 parser 抽取文本进行 deterministic 清洗。
- 清洗规则包括：
  - 标准化换行和空白字符。
  - 合并明显断行。
  - 删除重复空行。
  - 删除明显页码行。
  - 删除明显页眉页脚重复行。
  - 删除连续重复段落。
  - 过滤过短噪音行。
- 在文档上传 pipeline 中接入清洗服务。
- 生成 document-level quality metadata。
- 生成 chunk-level quality metadata。
- 生成 draft KnowledgeItem quality flags。
- 扩展 Review Queue 后端 flags。
- 增加后端单元测试和集成测试。

前端：

- Review Queue 展示新增 quality flags。
- Knowledge Documents 列表展示基础清洗摘要。
- 保持现有 approve / reject / edit / activate 流程不变。

### 7.2 Out of Scope

- 不做 LLM 自动改写。
- 不做 LLM 自动摘要。
- 不做 LLM 自动打标签。
- 不做 embedding provider。
- 不做 pgvector schema。
- 不做 OCR。
- 不做复杂版式还原。
- 不做跨文档语义去重。
- 不做后台人工数据清洗服务。
- 不把用户资料发送到外部服务。
- 不新增独立 Knowledge Quality 页面。
- 不新增复杂配置中心。

## 8. 核心概念

### 8.1 Raw Text

Parser 从上传文件中抽取出的原始文本。  
Raw Text 用于审计和问题排查，不直接作为最终 chunk 输入。

### 8.2 Clean Text

经过 deterministic quality pipeline 处理后的文本。  
Clean Text 是 `chunk_document` 的输入。

### 8.3 Clean Report

一次清洗过程生成的统计结果，包含：

- pipeline version
- raw text length
- clean text length
- removed line count
- removed paragraph count
- normalized break count
- duplicate block count
- warning list

### 8.4 Chunk Quality Metadata

每个 KnowledgeItem chunk 附带的质量元数据，描述该 chunk 的来源、长度、质量和清洗状态。

### 8.5 Quality Flags

给 Review Queue 使用的提示标签。  
flags 不改变业务状态，只帮助用户判断是否启用。

## 9. 后端数据契约

### 9.1 KnowledgeDocument metadata_json

上传并处理完成后，`KnowledgeDocument.metadata_json` 应包含：

```json
{
  "quality_pipeline_version": "knowledge_quality.det_v1",
  "raw_text_length": 9821,
  "clean_text_length": 8342,
  "removed_line_count": 18,
  "removed_paragraph_count": 3,
  "normalized_break_count": 42,
  "duplicate_block_count": 2,
  "quality_warnings": ["high_noise_removed"],
  "created_item_count": 12
}
```

要求：

- 字段允许向后兼容缺失。
- 旧文档没有这些字段时，前端不能报错。
- `quality_pipeline_version` 必须稳定，后续规则变更时升级版本号。

### 9.2 KnowledgeItem metadata_json

由文档上传生成的 draft KnowledgeItem 应包含：

```json
{
  "document_id": 123,
  "document_filename": "AI咨询服务介绍.pdf",
  "document_content_type": "application/pdf",
  "chunk_index": 0,
  "chunk_count": 12,
  "quality_pipeline_version": "knowledge_quality.det_v1",
  "chunk_raw_text_length": 920,
  "chunk_clean_text_length": 846,
  "chunk_quality_flags": ["weak_title"],
  "chunk_fingerprint": "sha256:..."
}
```

要求：

- 保留现有 document/chunk metadata 字段。
- 新字段不能破坏现有 retriever、review queue、context builder。
- `chunk_fingerprint` 用于 deterministic 重复判断，不作为安全哈希承诺。

### 9.3 Review Queue response

Review Queue 已经返回 `quality_flags`。  
本任务扩展可能出现的 flags：

```text
high_noise_removed
very_short_after_cleaning
duplicate_content
weak_title
cleaning_removed_all_content
```

要求：

- 后端可以返回未知 flag。
- 前端对未知 flag 使用通用展示，不能崩溃。
- flags 不影响 approve / reject / activate 的权限和状态流转。

## 10. 后端实现清单

### BE-01：新增 Knowledge Quality Service

新增文件：

```text
backend/app/services/knowledge_quality.py
```

建议定义：

```python
QUALITY_PIPELINE_VERSION = "knowledge_quality.det_v1"

class CleanTextResult(TypedDict):
    raw_text: str
    clean_text: str
    metadata: dict[str, Any]
    warnings: list[str]
```

核心函数：

```python
def clean_extracted_text(text: str) -> CleanTextResult:
    ...

def normalize_text(text: str) -> tuple[str, dict[str, Any]]:
    ...

def remove_noise_lines(text: str) -> tuple[str, dict[str, Any]]:
    ...

def merge_broken_lines(text: str) -> tuple[str, dict[str, Any]]:
    ...

def dedupe_repeated_paragraphs(text: str) -> tuple[str, dict[str, Any]]:
    ...

def content_fingerprint(content: str) -> str:
    ...

def build_chunk_quality_metadata(
    *,
    document_metadata: dict[str, Any],
    chunk_text: str,
    chunk_index: int,
    chunk_count: int,
) -> dict[str, Any]:
    ...

def build_quality_flags_for_chunk(
    *,
    title: str | None,
    content: str,
    metadata: dict[str, Any],
) -> list[str]:
    ...
```

实现要求：

- 输入为空时返回空 clean text 和 `cleaning_removed_all_content` warning。
- 清洗过程不能抛出非预期异常导致上传流程崩溃。
- 如果清洗失败，应 fail-closed：保留 document failed 状态或记录错误，不创建错误草稿。
- 规则必须可通过单元测试稳定复现。

### BE-02：接入 Document Upload Pipeline

修改文件：

```text
backend/app/services/knowledge_documents.py
```

当前目标流程：

```text
extract_text_from_upload
  -> clean_extracted_text
  -> chunk_document(clean_text)
  -> create draft KnowledgeItems with quality metadata
  -> update KnowledgeDocument metadata_json
```

实现要求：

- 原始上传文件不变。
- `KnowledgeDocument.text_excerpt` 使用 clean text 的前段。
- 如果 clean text 为空，不创建 KnowledgeItem，并将文档标记为 failed 或 processed with zero items，具体按现有状态模型选择一个一致口径。
- 已有 TXT / Markdown / PDF / DOCX 解析测试不能回归。
- workspace 隔离不回归。

### BE-03：扩展 Review Queue Flags

修改文件：

```text
backend/app/services/knowledge_review.py
```

新增质量提示：

```text
high_noise_removed
very_short_after_cleaning
duplicate_content
weak_title
cleaning_removed_all_content
```

建议触发规则：

- `high_noise_removed`：清洗移除比例超过阈值，例如 20%。
- `very_short_after_cleaning`：clean content 长度低于最小阈值。
- `duplicate_content`：当前 workspace 内存在相同或高度相似 fingerprint。
- `weak_title`：标题为空、过短、泛化，或只包含“服务介绍/方案/文档”等弱标题。
- `cleaning_removed_all_content`：清洗后无有效内容。

MVP 可以先做 deterministic exact fingerprint 重复判断，不做语义相似判断。

### BE-04：保持 Retriever / Context Builder 向后兼容

检查文件：

```text
backend/app/services/knowledge_retriever.py
backend/app/services/context_builder.py
```

要求：

- 新 metadata 不影响已有 citation pack。
- 已 active 的 KnowledgeItem 仍可被检索。
- 没有 quality metadata 的历史 KnowledgeItem 仍可使用。

### BE-05：事件与通知

如果现有 Event & Notification Center 已有知识文档处理事件，可复用原事件并把清洗摘要放入 payload。  
如果没有合适事件，新增内部事件：

```text
knowledge_document.quality_processed
```

payload 建议：

```json
{
  "workspace_id": 1,
  "document_id": 123,
  "filename": "AI咨询服务介绍.pdf",
  "created_item_count": 12,
  "removed_line_count": 18,
  "quality_warnings": ["high_noise_removed"]
}
```

MVP 不要求前端实时消费该事件，但后端测试需要保证事件不会破坏上传流程。

## 11. 前端实现清单

### FE-01：Review Queue 展示新增 Quality Flags

修改文件：

```text
frontend/src/app/admin/knowledge/page.tsx
```

新增中文文案：

```text
high_noise_removed -> 已移除较多噪音
very_short_after_cleaning -> 清洗后内容偏短
duplicate_content -> 内容疑似重复
weak_title -> 标题质量较弱
cleaning_removed_all_content -> 清洗后无有效内容
```

要求：

- 旧 flags 继续显示。
- 未识别 flag 显示为原始 key 或“其他质量提示”。
- 不改变现有审核按钮和状态流转。

### FE-02：Document List 展示清洗摘要

在 Knowledge Documents 列表或详情区域展示轻量摘要：

```text
生成 12 条草稿
移除噪音 18 处
清洗版本 knowledge_quality.det_v1
```

展示原则：

- 有 metadata 就展示。
- 没有 metadata 就隐藏，不显示空值。
- 不引入新的复杂页面。

### FE-03：Review Item Metadata 展示增强

在每条 draft KnowledgeItem 上可展示：

- 来源文档。
- chunk 序号。
- quality flags。
- clean content 摘要。

MVP 不要求展示 raw text 与 clean text 对比，避免增加敏感信息暴露面和 UI 复杂度。

## 12. 测试清单

### 12.1 后端单元测试

新增：

```text
backend/tests/test_knowledge_quality_pipeline.py
```

覆盖：

1. 空文本返回空 clean text 和 warning。
2. 重复空行被压缩。
3. 明显页码行被移除。
4. 重复页眉页脚被移除。
5. 明显断行被合并。
6. 连续重复段落被去重。
7. 过短噪音行被移除。
8. 主要正文不会被误删。
9. clean report 统计字段稳定。
10. fingerprint 对相同内容稳定。

### 12.2 后端集成测试

扩展或新增文档上传测试，覆盖：

1. 上传 TXT 后生成带 `quality_pipeline_version` 的 KnowledgeItem。
2. 上传 PDF / DOCX 后仍走 quality pipeline。
3. `KnowledgeDocument.metadata_json` 包含清洗摘要。
4. `KnowledgeDocument.text_excerpt` 来自 clean text。
5. 清洗后为空时不创建无意义 KnowledgeItem。
6. Review Queue 返回新增 quality flags。
7. 历史 KnowledgeItem 缺少 quality metadata 时 review/retrieval 不报错。
8. workspace A 的文档不会影响 workspace B 的重复判断。

### 12.3 前端测试

如果项目当前有前端测试框架，则补：

1. Review Queue 能显示新增 flag 文案。
2. 未知 flag 不导致页面崩溃。
3. Document List 有 metadata 时显示清洗摘要。
4. 无 metadata 时保持现有展示。

如果当前没有前端测试框架，至少执行：

```text
npm run lint
npm run build
```

### 12.4 回归测试

后端：

```text
cd backend
.venv/bin/python -m pytest
```

前端：

```text
cd frontend
npm run lint
npm run build
```

## 13. 验收标准

### 产品验收

1. 用户上传文档后，系统自动完成本地清洗。
2. 用户不需要手工整理页码、空行、断行、重复段落。
3. Review Queue 能显示质量提示。
4. 用户仍然可以人工决定 approve / reject / edit。
5. 原始文件不被修改。
6. 不调用外部模型或外部清洗服务。

### 后端验收

1. `knowledge_quality.py` 存在并有稳定测试覆盖。
2. 文档上传 pipeline 接入 quality pipeline。
3. KnowledgeDocument metadata 记录清洗摘要。
4. KnowledgeItem metadata 记录 chunk quality 信息。
5. Review Queue 返回新增 flags。
6. 历史数据向后兼容。
7. 后端全量测试通过。

### 前端验收

1. Review Queue 能展示新增 quality flags。
2. Document List 能展示清洗摘要。
3. 缺少 metadata 时页面不报错。
4. 前端 lint / build 通过。

## 14. 失败与边界处理

### 清洗后无有效内容

处理原则：

- 不创建空 KnowledgeItem。
- Document 状态按现有模型记录为 failed 或 processed zero items。
- metadata 记录 `cleaning_removed_all_content`。

### 清洗规则误删风险

处理原则：

- 清洗规则必须保守。
- 不删除长正文段落。
- 不做语义改写。
- 测试覆盖“主要正文不会被误删”。

### 旧数据兼容

处理原则：

- 旧 KnowledgeDocument 可能没有 quality metadata。
- 旧 KnowledgeItem 可能没有 chunk quality metadata。
- review / retriever / context builder 必须兼容缺失字段。

### 重复内容判断

MVP 只做 deterministic fingerprint。  
跨文档语义相似、近似重复、行业术语归一，不在本任务内。

## 15. 与后续路线关系

P6.5 完成后，后续顺序为：

```text
P6.5 Knowledge Quality Pipeline
  -> P6.6 Vector RAG / pgvector
  -> P6.7 Real Embedding Provider
  -> P6.8 Production pgvector
```

P6.6 在使用向量索引时，应优先索引 active KnowledgeItem，并保留 quality metadata 到 citation pack 或检索 debug 信息中。

## 16. 推荐实现顺序

1. 新增 `knowledge_quality.py` 和单元测试。
2. 接入 `knowledge_documents.py` 上传处理流程。
3. 扩展 KnowledgeDocument / KnowledgeItem metadata。
4. 扩展 Review Queue flags。
5. 补齐上传集成测试和 workspace 隔离测试。
6. 更新前端 Review Queue flag 文案。
7. 更新前端 Document List 清洗摘要。
8. 跑后端全量测试。
9. 跑前端 lint / build。

## 17. 不做事项确认

本任务完成后，仍然不会具备：

- 真正语义向量召回。
- 真实 embedding provider。
- pgvector 生产数据库迁移。
- LLM 自动摘要与改写。
- 行业级知识模板。
- OCR。
- 用户资料人工代整理服务。

这些能力应在后续独立任务中设计和实现。

## 18. 完成定义

满足以下条件才算 P6.5 完成：

1. 上传文档经过 deterministic quality pipeline。
2. 原始文件不被修改。
3. 清洗后的文本用于 chunk 生成。
4. 文档级 metadata 记录清洗摘要。
5. chunk 级 metadata 记录质量信息。
6. Review Queue 展示新增质量提示。
7. 不调用任何外部服务。
8. 后端新增和回归测试通过。
9. 前端 lint / build 通过。
10. README / roadmap 中 P6.5 与 P6.6 顺序保持一致。
