"use client";

import { useCallback, useEffect, useState } from "react";
import AdminShell from "@/components/admin/admin-shell";
import {
	  archiveKnowledgeItem, bulkUpdateKnowledgeReviewItems, createKnowledgeItem,
	  archiveRetrievalEvalCase, createRetrievalEvalCase,
	  getKnowledgeDocuments, getKnowledgeItems, getKnowledgeReviewItems,
	  getKnowledgeVectorStatus, getNotificationSummary, getServices,
	  getRetrievalEvalCases, getRetrievalEvalRun,
	  reindexActiveKnowledge, reindexKnowledgeItem,
	  runRetrievalEvaluation, updateKnowledgeItem, uploadKnowledgeDocument,
	  KNOWLEDGE_SOURCE_TYPES, type KnowledgeDocumentOut, type KnowledgeItemInput,
	  type KnowledgeItemOut, type KnowledgeReviewItemOut, type RetrievalEvalCaseOut,
	  type RetrievalEvalRunDetailOut, type ServiceOut,
	} from "@/lib/admin-api";

const SOURCE_TYPE_LABELS: Record<string, string> = {
  manual: "手工录入", faq: "FAQ", case_study: "案例", methodology: "方法论",
  pricing_rule: "报价规则", contract_boundary: "合同边界", delivery_sop: "交付 SOP",
  service_note: "服务说明", external_doc: "外部文档",
};
const STATUS_LABELS: Record<string, string> = { draft: "草稿", active: "有效", archived: "已归档" };
const STATUS_FILTERS = ["active", "draft", "archived"];
const PARSER_LABELS: Record<string, string> = {
  text_v1: "TXT", markdown_text_v1: "Markdown", pdf_text_v1: "PDF 文本", docx_text_v1: "Word 文档",
};

type Draft = {
  title: string; summary: string; content_markdown: string;
  source_type: string; status: string; tags: string; service_id: string;
};
const emptyDraft: Draft = {
  title: "", summary: "", content_markdown: "", source_type: "manual",
  status: "active", tags: "", service_id: "",
};

function toDraft(it: KnowledgeItemOut): Draft {
  return {
    title: it.title, summary: it.summary ?? "", content_markdown: it.content_markdown,
    source_type: it.source_type, status: it.status,
    tags: (it.tags_json || []).join(", "), service_id: it.service_id ?? "",
  };
}
function toPayload(d: Draft): KnowledgeItemInput {
  return {
    title: d.title.trim(),
    content_markdown: d.content_markdown.trim(),
    summary: d.summary.trim() || null,
    source_type: d.source_type,
    status: d.status,
    tags_json: d.tags.split(",").map((t) => t.trim()).filter(Boolean),
    service_id: d.service_id || null,
  };
}

export default function KnowledgePage() {
  const [items, setItems] = useState<KnowledgeItemOut[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [unreadCount, setUnreadCount] = useState<number | undefined>();
  const [services, setServices] = useState<ServiceOut[]>([]);

  const [q, setQ] = useState("");
  const [status, setStatus] = useState("active");
  const [sourceType, setSourceType] = useState("");
  const [tag, setTag] = useState("");

  const [editorOpen, setEditorOpen] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);
  const [draft, setDraft] = useState<Draft>(emptyDraft);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [confirmArchive, setConfirmArchive] = useState<string | null>(null);

  const [documents, setDocuments] = useState<KnowledgeDocumentOut[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadMsg, setUploadMsg] = useState<string | null>(null);

  const [reviewItems, setReviewItems] = useState<KnowledgeReviewItemOut[]>([]);
  const [reviewTotal, setReviewTotal] = useState(0);
  const [reviewDoc, setReviewDoc] = useState("");
  const [reviewQuality, setReviewQuality] = useState("");
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [bulkSaving, setBulkSaving] = useState(false);
  const [bulkService, setBulkService] = useState("");
	  const [indexing, setIndexing] = useState(false);
	  const [vectorStatuses, setVectorStatuses] = useState<Record<string, { knowledge_item_id: string; status: string; stale: boolean; error_message?: string | null; provider?: string | null; embedding_model?: string | null; vector_dim?: number | null; vector_store?: string | null }>>({});
	  const [evalCases, setEvalCases] = useState<RetrievalEvalCaseOut[]>([]);
	  const [evalRun, setEvalRun] = useState<RetrievalEvalRunDetailOut | null>(null);
	  const [evalQuery, setEvalQuery] = useState("");
	  const [evalTags, setEvalTags] = useState("");
	  const [evalNotes, setEvalNotes] = useState("");
	  const [expectedIds, setExpectedIds] = useState<Set<string>>(new Set());
	  const [evalSaving, setEvalSaving] = useState(false);
	  const [evalRunning, setEvalRunning] = useState(false);

  const loadDocuments = useCallback(() => {
    getKnowledgeDocuments().then((r) => setDocuments(r.items)).catch(() => {});
  }, []);

	  const loadReview = useCallback(() => {
    getKnowledgeReviewItems({
      status: "draft",
      document_id: reviewDoc || undefined,
      quality_flag: reviewQuality || undefined,
    }).then((r) => { setReviewItems(r.items); setReviewTotal(r.total); }).catch(() => {});
	  }, [reviewDoc, reviewQuality]);

	  const loadEvalCases = useCallback(() => {
	    getRetrievalEvalCases("active").then((r) => setEvalCases(r.items)).catch(() => {});
	  }, []);

  useEffect(() => { loadReview(); }, [loadReview]);

  // Proactively load vector status for active items in the current list
  useEffect(() => {
    const activeItems = items.filter((it) => it.status === "active");
    activeItems.forEach((it) => {
      getKnowledgeVectorStatus(it.id).then((s) => {
        setVectorStatuses((prev) => ({ ...prev, [it.id]: s }));
      }).catch(() => {});
    });
  }, [items]);

  const load = useCallback(() => {
    setLoading(true);
    getKnowledgeItems({ q: q || undefined, status, source_type: sourceType || undefined, tag: tag || undefined })
      .then((r) => { setItems(r.items); setTotal(r.total); setError(null); })
      .catch((e) => setError(e instanceof Error ? e.message : "加载失败"))
      .finally(() => setLoading(false));
  }, [q, status, sourceType, tag]);

  useEffect(() => { queueMicrotask(load); }, [load]);
  useEffect(() => {
    getNotificationSummary().then((s) => setUnreadCount(s.unread_count)).catch(() => {});
	    getServices({ status: "active" }).then((r) => setServices(r.items)).catch(() => {});
	    loadDocuments();
	    loadEvalCases();
	  }, [loadDocuments, loadEvalCases]);

  const handleUpload = async (file: File | undefined) => {
    if (!file) return;
    setUploading(true); setUploadMsg(null); setError(null);
    try {
      const res = await uploadKnowledgeDocument(file);
      setUploadMsg(`已从「${res.document.filename}」生成 ${res.item_count} 条草稿 KnowledgeItem，请审核后启用。`);
      setStatus("draft"); // surface the freshly-generated drafts
      loadDocuments();
    } catch (e: unknown) {
      setUploadMsg(null);
      setError(e instanceof Error ? e.message : "上传失败");
    } finally {
      setUploading(false);
    }
  };

  const QUALITY_FLAG_LABELS: Record<string, string> = {
    short_content: "正文偏短", missing_summary: "缺少摘要", missing_service: "未关联服务",
    duplicate_title: "标题重复", missing_tags: "缺少标签", external_doc_without_document_id: "缺少来源文档",
    high_noise_removed: "已移除较多噪音", very_short_after_cleaning: "清洗后内容偏短",
    duplicate_content: "内容疑似重复", weak_title: "标题质量较弱", cleaning_removed_all_content: "清洗后无有效内容",
  };

  const handleBulk = async (action: "activate" | "archive" | "set_service" | "clear_service") => {
    if (selectedIds.size === 0) return;
    setBulkSaving(true); setError(null);
    try {
      await bulkUpdateKnowledgeReviewItems({
        item_ids: Array.from(selectedIds),
        action,
        service_id: action === "set_service" ? (bulkService || undefined) : undefined,
      });
      setSelectedIds(new Set());
      loadReview(); load(); loadDocuments();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "批量操作失败");
    } finally {
      setBulkSaving(false);
    }
  };

	  const toggleSelect = (id: string) => {
	    setSelectedIds((prev) => { const next = new Set(prev); if (next.has(id)) next.delete(id); else next.add(id); return next; });
	  };

	  const toggleExpected = (id: string) => {
	    setExpectedIds((prev) => { const next = new Set(prev); if (next.has(id)) next.delete(id); else next.add(id); return next; });
	  };

  const viewDocDrafts = (docId: string) => { setReviewDoc(docId); setStatus("draft"); };

  const handleBatchReindex = async () => {
    setIndexing(true); setError(null);
    try {
      const res = await reindexActiveKnowledge(100);
      setError(`已索引 ${res.indexed_count} 条，跳过 ${res.skipped_count} 条${res.failed_count > 0 ? `，失败 ${res.failed_count} 条` : ""}`);
      // Refresh all active items' vector status after batch reindex
      const activeItems = items.filter((it) => it.status === "active");
      for (const it of activeItems) {
        try {
          const s = await getKnowledgeVectorStatus(it.id);
          setVectorStatuses((prev) => ({ ...prev, [it.id]: s }));
        } catch { /* skip individual failures */ }
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "索引失败");
    } finally {
      setIndexing(false);
    }
  };

  const handleSingleReindex = async (id: string) => {
    setVectorStatuses((prev) => ({ ...prev, [id]: { knowledge_item_id: id, status: "indexing" as const, stale: false } }));
    try {
      await reindexKnowledgeItem(id);
      const status = await getKnowledgeVectorStatus(id);
      setVectorStatuses((prev) => ({ ...prev, [id]: status }));
    } catch {
      setVectorStatuses((prev) => ({ ...prev, [id]: { knowledge_item_id: id, status: "failed" as const, stale: false } }));
    }
  };

  const set = (patch: Partial<Draft>) => setDraft((d) => ({ ...d, ...patch }));
  const startCreate = () => { setDraft(emptyDraft); setEditId(null); setFormError(null); setEditorOpen(true); };
  const startEdit = (it: KnowledgeItemOut) => { setDraft(toDraft(it)); setEditId(it.id); setFormError(null); setEditorOpen(true); };
  const closeEditor = () => { setEditorOpen(false); setEditId(null); setFormError(null); };

  const save = async () => {
    if (!draft.title.trim() || !draft.content_markdown.trim()) { setFormError("标题和正文为必填"); return; }
    setSaving(true); setFormError(null);
    try {
      if (editId) await updateKnowledgeItem(editId, toPayload(draft));
      else await createKnowledgeItem(toPayload(draft));
      closeEditor(); load();
    } catch (e: unknown) {
      setFormError(e instanceof Error ? e.message : "保存失败");
    } finally {
      setSaving(false);
    }
  };

	  const doArchive = async (id: string) => {
	    try { await archiveKnowledgeItem(id); setConfirmArchive(null); load(); }
	    catch (e: unknown) { setError(e instanceof Error ? e.message : "归档失败"); }
	  };

	  const createEvalCase = async () => {
	    if (!evalQuery.trim() || expectedIds.size === 0) { setError("评估问题和期望命中的知识条目为必填"); return; }
	    setEvalSaving(true); setError(null);
	    try {
	      await createRetrievalEvalCase({
	        query: evalQuery.trim(),
	        expected_knowledge_item_ids: Array.from(expectedIds),
	        tags_json: evalTags.split(",").map((t) => t.trim()).filter(Boolean),
	        notes: evalNotes.trim() || null,
	      });
	      setEvalQuery(""); setEvalTags(""); setEvalNotes(""); setExpectedIds(new Set());
	      loadEvalCases();
	    } catch (e: unknown) {
	      setError(e instanceof Error ? e.message : "创建评估用例失败");
	    } finally {
	      setEvalSaving(false);
	    }
	  };

	  const runEval = async (caseIds?: string[]) => {
	    setEvalRunning(true); setError(null);
	    try {
	      const run = await runRetrievalEvaluation({ case_ids: caseIds, k: 5 });
	      const detail = await getRetrievalEvalRun(run.id);
	      setEvalRun(detail);
	      loadEvalCases();
	    } catch (e: unknown) {
	      setError(e instanceof Error ? e.message : "运行评估失败");
	    } finally {
	      setEvalRunning(false);
	    }
	  };

	  const archiveEval = async (id: string) => {
	    try { await archiveRetrievalEvalCase(id); loadEvalCases(); }
	    catch (e: unknown) { setError(e instanceof Error ? e.message : "归档评估用例失败"); }
	  };

	  const serviceName = (id: string | null) => services.find((s) => s.id === id)?.name;
	  const knowledgeTitle = (id: string) => items.find((it) => it.id === id)?.title || id;
	  const pct = (n: number) => `${Math.round(n * 100)}%`;

  return (
    <AdminShell active="knowledge" unreadCount={unreadCount} eyebrow="Workspace 私有知识" title="知识库" subtitle={`${total} 条知识`}>
      {error && <p className="error-msg">{error}</p>}

      <section className="admin-toolbar">
        <label>搜索 <input placeholder="标题 / 摘要 / 正文" value={q} onChange={(e) => setQ(e.target.value)} /></label>
        <label>标签 <input placeholder="按标签筛选" value={tag} onChange={(e) => setTag(e.target.value)} /></label>
        <label>来源类型
          <select value={sourceType} onChange={(e) => setSourceType(e.target.value)}>
            <option value="">全部</option>
            {KNOWLEDGE_SOURCE_TYPES.map((t) => <option key={t} value={t}>{SOURCE_TYPE_LABELS[t]}</option>)}
          </select>
        </label>
        <div className="stage-filter">
          {STATUS_FILTERS.map((s) => (
            <button key={s} className={s === status ? "active" : ""} onClick={() => setStatus(s)}>{STATUS_LABELS[s]}</button>
          ))}
        </div>
        <button className="button primary" onClick={startCreate}>新增知识</button>
        <button className="button ghost small" onClick={handleBatchReindex} disabled={indexing}>{indexing ? "索引中..." : "批量索引"}</button>
      </section>

      <section className="knowledge-upload">
        <div className="panel-heading"><h2>上传文档</h2></div>
        <div className="upload-row">
          <label className="button ghost">
            {uploading ? "解析中..." : "选择 TXT / Markdown / PDF / Word 文件"}
            <input type="file" accept=".txt,.md,.pdf,.docx,text/plain,text/markdown,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document" style={{ display: "none" }}
              disabled={uploading}
              onChange={(e) => { handleUpload(e.target.files?.[0]); e.target.value = ""; }} />
          </label>
          <small>支持 TXT、Markdown、PDF 文本层、Word 文档；扫描版 PDF 暂不支持 OCR。上传后自动解析为草稿知识条目，需审核后启用；仅 active 条目会被 Agent 使用。</small>
        </div>
        {uploadMsg && <p className="upload-result">{uploadMsg}</p>}
        {documents.length > 0 && (
          <div className="document-list">
            {documents.slice(0, 8).map((d) => (
              <div key={d.id} className="document-row">
                <strong>{d.filename}</strong>
                <span className="document-meta">
                  <span className={`stage-badge stage-${d.status === "processed" ? "qualified" : d.status === "failed" ? "lead" : "lead"}`}>{d.status}</span>
                  <span>{d.item_count} 条</span>
                  {d.parser && <span>{PARSER_LABELS[d.parser] || d.parser}</span>}
                  <span>{new Date(d.created_at).toLocaleString()}</span>
                  {d.error_message && <span className="document-error">{d.error_message}</span>}
                  {d.metadata_json && (d.metadata_json as Record<string, unknown>).removed_line_count != null && (
                    <span>清洗移除 {(d.metadata_json as Record<string, unknown>).removed_line_count as number} 处</span>
                  )}
                  <button className="button ghost small" onClick={() => viewDocDrafts(d.id)}>查看草稿</button>
                </span>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* ── Review Queue ── */}
      <section className="knowledge-review">
        <div className="panel-heading"><h2>审核队列{reviewDoc && " · 按文档筛选"}{reviewTotal > 0 && ` · ${reviewTotal} 条草稿`}</h2></div>
        <div className="review-toolbar">
          <div className="stage-filter">
            <select value={reviewDoc} onChange={(e) => setReviewDoc(e.target.value)}>
              <option value="">全部文档</option>
              {documents.map((d) => <option key={d.id} value={d.id}>{d.filename}</option>)}
            </select>
          </div>
          <div className="stage-filter">
            <select value={reviewQuality} onChange={(e) => setReviewQuality(e.target.value)}>
              <option value="">全部质量提示</option>
              {Object.entries(QUALITY_FLAG_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          </div>
          <span className="review-count">已选择 {selectedIds.size} 条</span>
          <button className="button primary small" disabled={selectedIds.size === 0 || bulkSaving} onClick={() => handleBulk("activate")}>{bulkSaving ? "处理中..." : "启用"}</button>
          <button className="button ghost small" disabled={selectedIds.size === 0 || bulkSaving} onClick={() => handleBulk("archive")}>归档</button>
        </div>
        {selectedIds.size > 0 && (
          <div className="review-service-bar">
            <label>绑定服务
              <select value={bulkService} onChange={(e) => setBulkService(e.target.value)}>
                <option value="">选择服务</option>
                {services.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
              </select>
            </label>
            <button className="button ghost small" disabled={!bulkService || bulkSaving} onClick={() => handleBulk("set_service")}>关联服务</button>
            <button className="button ghost small" disabled={bulkSaving} onClick={() => handleBulk("clear_service")}>清空关联</button>
          </div>
        )}
        <div className="review-list">
          {reviewItems.length === 0 ? (
            <p className="subresource-empty">{reviewDoc ? "该文档没有草稿条目" : "暂无可审核草稿"}</p>
          ) : (
            reviewItems.map((r) => (
              <div key={r.item.id} className={`review-row ${selectedIds.has(r.item.id) ? "selected" : ""}`}>
                <label className="review-checkbox">
                  <input type="checkbox" checked={selectedIds.has(r.item.id)} onChange={() => toggleSelect(r.item.id)} />
                </label>
                <div className="review-main">
                  <strong>{r.item.title}</strong>
                  {r.quality_flags.length > 0 && (
                    <span className="quality-flags">
                      {r.quality_flags.map((f) => <span key={f} className="quality-flag">{QUALITY_FLAG_LABELS[f] || f}</span>)}
                    </span>
                  )}
                  {r.document && <small className="review-doc-src">{r.document.filename}</small>}
                </div>
              </div>
            ))
          )}
        </div>
	      </section>

	      <section className="knowledge-review">
	        <div className="panel-heading"><h2>检索评估{evalCases.length > 0 && ` · ${evalCases.length} 条用例`}</h2></div>
	        <div className="subform-grid">
	          <label className="subform-full">评估问题
	            <input value={evalQuery} onChange={(e) => setEvalQuery(e.target.value)} placeholder="如：企业知识库 PoC 怎么验收？" />
	          </label>
	          <label>标签
	            <input value={evalTags} onChange={(e) => setEvalTags(e.target.value)} placeholder="rag, poc" />
	          </label>
	          <label>备注
	            <input value={evalNotes} onChange={(e) => setEvalNotes(e.target.value)} placeholder="期望命中哪些资料" />
	          </label>
	        </div>
	        <div className="review-list">
	          {items.filter((it) => it.status === "active").slice(0, 12).map((it) => (
	            <div key={it.id} className={`review-row ${expectedIds.has(it.id) ? "selected" : ""}`}>
	              <label className="review-checkbox">
	                <input type="checkbox" checked={expectedIds.has(it.id)} onChange={() => toggleExpected(it.id)} />
	              </label>
	              <div className="review-main">
	                <strong>{it.title}</strong>
	                <small>{SOURCE_TYPE_LABELS[it.source_type] || it.source_type}{it.tags_json?.length ? ` · ${it.tags_json.join(" / ")}` : ""}</small>
	              </div>
	            </div>
	          ))}
	          {items.filter((it) => it.status === "active").length === 0 && <p className="subresource-empty">当前列表没有 active 知识条目可选</p>}
	        </div>
	        <div className="confirm-actions">
	          <button className="button primary small" onClick={createEvalCase} disabled={evalSaving}>{evalSaving ? "保存中..." : "创建评估用例"}</button>
	          <button className="button ghost small" onClick={() => runEval()} disabled={evalRunning || evalCases.length === 0}>{evalRunning ? "评估中..." : "运行全部评估"}</button>
	        </div>
	        {evalCases.length > 0 && (
	          <div className="document-list">
	            {evalCases.map((c) => (
	              <div key={c.id} className="document-row">
	                <strong>{c.query}</strong>
	                <span className="document-meta">
	                  <span>{c.expected_knowledge_item_ids.length} 个期望命中</span>
	                  {c.tags_json.map((t) => <span key={t} className="knowledge-tag">#{t}</span>)}
	                  <button className="button ghost small" onClick={() => runEval([c.id])} disabled={evalRunning}>运行</button>
	                  <button className="button ghost small" onClick={() => archiveEval(c.id)}>归档</button>
	                </span>
	              </div>
	            ))}
	          </div>
	        )}
	        {evalRun && (
	          <div className="document-list">
	            <div className="document-row">
	              <strong>最近一次评估</strong>
	              <span className="document-meta">
	                <span>Recall@{evalRun.run.k}: {pct(evalRun.run.average_recall_at_k)}</span>
	                <span>Precision@{evalRun.run.k}: {pct(evalRun.run.average_precision_at_k)}</span>
	                <span>漏召回 {evalRun.run.miss_count}</span>
	                <span>空召回 {evalRun.run.zero_hit_count}</span>
	                {evalRun.run.vector_store && <span>{evalRun.run.vector_store}</span>}
	                {evalRun.run.embedding_model && <span>{evalRun.run.embedding_model}</span>}
	                <span>Reranker：{evalRun.run.reranker_enabled ? (evalRun.run.reranker_provider || "enabled") : "none"}</span>
	                {evalRun.run.reranker_model && <span>{evalRun.run.reranker_model}</span>}
	              </span>
	            </div>
	            {evalRun.results.map((r) => (
	              <div key={r.id} className="document-row">
	                <strong>{r.status === "passed" ? "通过" : r.status === "missed" ? "漏召回" : r.status === "empty" ? "空召回" : "错误"} · {r.query}</strong>
	                <span className="document-meta">
	                  <span>Recall {pct(r.recall_at_k)}</span>
	                  <span>Precision {pct(r.precision_at_k)}</span>
	                  <span>命中 {r.hit_count}</span>
	                  {r.matched_expected_ids.map((id) => <span key={id}>命中：{knowledgeTitle(id)}</span>)}
	                  {r.missed_expected_ids.map((id) => <span key={id} className="document-error">漏掉：{knowledgeTitle(id)}</span>)}
	                  {r.error_message && <span className="document-error">{r.error_message}</span>}
	                  {r.citation_pack_json?.reranker_error && <span className="document-error">Reranker：{r.citation_pack_json.reranker_error}</span>}
	                </span>
	                {r.citation_pack_json?.hits && r.citation_pack_json.hits.length > 0 && (
	                  <span className="document-meta">
	                    {r.citation_pack_json.hits.slice(0, 5).map((h, idx) => (
	                      <span key={`${r.id}-${h.knowledge_item_id}`}>
	                        #{idx + 1} {h.title || knowledgeTitle(h.knowledge_item_id)}
	                        {h.score != null ? ` · score ${h.score}` : ""}
	                        {h.reranked && h.rerank_score != null ? ` · rerank ${h.rerank_score}` : ""}
	                        {h.retrieval_mode ? ` · ${h.retrieval_mode}` : ""}
	                      </span>
	                    ))}
	                  </span>
	                )}
	              </div>
	            ))}
	          </div>
	        )}
	      </section>

	      {editorOpen && (
        <section className="knowledge-editor">
          <div className="panel-heading"><h2>{editId ? "编辑知识" : "新增知识"}</h2></div>
          {formError && <p className="error-msg">{formError}</p>}
          <div className="subform-grid">
            <label className="subform-full">标题 *
              <input value={draft.title} onChange={(e) => set({ title: e.target.value })} placeholder="如：RAG 项目常见验收标准" />
            </label>
            <label className="subform-full">摘要
              <input value={draft.summary} onChange={(e) => set({ summary: e.target.value })} placeholder="一句话摘要，供列表和 Agent 上下文使用" />
            </label>
            <label className="subform-full">正文 (Markdown) *
              <textarea value={draft.content_markdown} rows={6} onChange={(e) => set({ content_markdown: e.target.value })} />
            </label>
            <label>来源类型
              <select value={draft.source_type} onChange={(e) => set({ source_type: e.target.value })}>
                {KNOWLEDGE_SOURCE_TYPES.map((t) => <option key={t} value={t}>{SOURCE_TYPE_LABELS[t]}</option>)}
              </select>
            </label>
            <label>状态
              <select value={draft.status} onChange={(e) => set({ status: e.target.value })}>
                <option value="active">有效</option>
                <option value="draft">草稿</option>
                <option value="archived">已归档</option>
              </select>
            </label>
            <label>适用服务
              <select value={draft.service_id} onChange={(e) => set({ service_id: e.target.value })}>
                <option value="">不关联</option>
                {services.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
              </select>
            </label>
            <label>标签（逗号分隔）
              <input value={draft.tags} onChange={(e) => set({ tags: e.target.value })} placeholder="rag, 验收, PoC" />
            </label>
          </div>
          <div className="confirm-actions">
            <button className="button primary small" onClick={save} disabled={saving}>{saving ? "保存中..." : "保存"}</button>
            <button className="button ghost small" onClick={closeEditor} disabled={saving}>取消</button>
          </div>
        </section>
      )}

      {loading ? (
        <div className="loading-state">Loading...</div>
      ) : items.length === 0 ? (
        <div className="empty-state">
          <p>还没有知识条目。先录入 FAQ、案例、报价规则或交付 SOP，让后续 Agent 能基于你的业务资料工作。</p>
        </div>
      ) : (
        <div className="knowledge-list">
          {items.map((it) => (
            <article className="knowledge-row" key={it.id}>
              <div className="knowledge-main">
                <strong>{it.title}</strong>
                {it.summary && <small>{it.summary}</small>}
                <span className="knowledge-meta">
                  <span className="severity-badge">{SOURCE_TYPE_LABELS[it.source_type] || it.source_type}</span>
                  <span className={`stage-badge stage-${it.status === "active" ? "qualified" : "lead"}`}>{STATUS_LABELS[it.status] || it.status}</span>
                  {it.service_id && serviceName(it.service_id) && <span>服务：{serviceName(it.service_id)}</span>}
                  {(it.tags_json || []).map((t) => <span key={t} className="knowledge-tag">#{t}</span>)}
                  <span>更新于 {new Date(it.updated_at).toLocaleDateString()}</span>
                  {vectorStatuses[it.id] && (
                    <span className={`vector-status-badge vector-status-${vectorStatuses[it.id].status}`} title={vectorStatuses[it.id].error_message || ""}>
                      {vectorStatuses[it.id].status === "indexing" ? "索引中"
                        : vectorStatuses[it.id].status === "indexed" ? (vectorStatuses[it.id].stale ? "待更新" : "已索引")
                        : vectorStatuses[it.id].status === "stale" ? "待更新"
                        : vectorStatuses[it.id].status === "failed" ? `失败${vectorStatuses[it.id].error_message ? "：" + vectorStatuses[it.id].error_message : ""}`
                        : vectorStatuses[it.id].status}
                      {(vectorStatuses[it.id].status === "indexed" || vectorStatuses[it.id].status === "stale") && vectorStatuses[it.id].embedding_model && (
                        <span className="vector-status-meta">
                          {" · "}
                          {[vectorStatuses[it.id].vector_store, vectorStatuses[it.id].embedding_model,
                            vectorStatuses[it.id].vector_dim ? `${vectorStatuses[it.id].vector_dim}d` : null]
                            .filter(Boolean).join(" / ")}
                        </span>
                      )}
                    </span>
                  )}
                </span>
              </div>
              <div className="knowledge-actions">
                {confirmArchive === it.id ? (
                  <span className="confirm-actions">确认归档？
                    <button className="button primary small" onClick={() => doArchive(it.id)}>确认归档</button>
                    <button className="button ghost small" onClick={() => setConfirmArchive(null)}>取消</button>
                  </span>
                ) : (
                  <>
                    <button className="button ghost small" onClick={() => startEdit(it)}>编辑</button>
                    {it.status === "active" && (
                      <button className="button ghost small"
                        disabled={vectorStatuses[it.id]?.status === "indexing"}
                        onClick={() => handleSingleReindex(it.id)}>
                        {vectorStatuses[it.id]?.status === "indexing" ? "索引中" : "索引"}
                      </button>
                    )}
                    {it.status !== "archived" && <button className="button ghost small" onClick={() => setConfirmArchive(it.id)}>归档</button>}
                  </>
                )}
              </div>
            </article>
          ))}
        </div>
      )}
    </AdminShell>
  );
}
