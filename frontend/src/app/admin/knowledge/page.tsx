"use client";

import { useCallback, useEffect, useState } from "react";
import AdminShell from "@/components/admin/admin-shell";
import {
	  applyGuidedKnowledgeEdit,
	  archiveKnowledgeItem, bulkUpdateKnowledgeReviewItems, createKnowledgeItem,
	  createKnowledgeRetrievalFeedback,
	  generateKnowledgeImprovementSuggestions,
	  archiveRetrievalEvalCase, createRetrievalEvalCase,
	  getKnowledgeImprovementSuggestions,
	  getKnowledgeRetrievalFeedback,
	  getKnowledgeDocuments, getKnowledgeItems, getKnowledgeReviewItems,
	  getKnowledgeVectorStatus, getNotificationSummary, getServices,
	  getRetrievalEvalCases, getRetrievalEvalRun,
	  promoteRetrievalEvalCases,
	  reindexActiveKnowledge, reindexKnowledgeItem,
	  runRetrievalEvaluation, updateKnowledgeItem, uploadKnowledgeDocument,
	  updateKnowledgeImprovementSuggestion,
	  updateKnowledgeRetrievalFeedback,
	  KNOWLEDGE_SOURCE_TYPES, type KnowledgeDocumentOut, type KnowledgeItemInput,
	  type KnowledgeImprovementSuggestionOut, type KnowledgeImprovementSuggestionStatus,
	  type KnowledgeItemOut, type KnowledgeRetrievalFeedbackOut,
	  type KnowledgeRetrievalFeedbackStatus, type KnowledgeReviewItemOut,
	  type KnowledgeCitationHit, type RetrievalEvalCaseOut,
	  type RetrievalEvalResultOut, type RetrievalEvalRunDetailOut, type ServiceOut,
	} from "@/lib/admin-api";

const SOURCE_TYPE_LABELS: Record<string, string> = {
  manual: "手工录入", faq: "FAQ", case_study: "案例", methodology: "方法论",
  pricing_rule: "报价规则", contract_boundary: "合同边界", delivery_sop: "交付 SOP",
  service_note: "服务说明", external_doc: "外部文档",
};
const STATUS_LABELS: Record<string, string> = { draft: "草稿", active: "有效", archived: "已归档" };
const STATUS_FILTERS = ["active", "draft", "archived"];
const FEEDBACK_TYPE_LABELS: Record<string, string> = {
  helpful: "有用", irrelevant: "不相关", missing: "漏召回", outdated: "过时", needs_review: "需检查",
};
const FEEDBACK_STATUS_LABELS: Record<string, string> = {
  open: "待处理", reviewed: "已查看", resolved: "已解决", archived: "已归档",
};
const SUGGESTION_TYPE_LABELS: Record<string, string> = {
  update_content: "更新正文",
  improve_metadata: "优化元数据",
  improve_retrievability: "增强可检索性",
  split_knowledge: "拆分知识",
  create_knowledge: "新增知识",
  promote_eval_case: "沉淀评估用例",
};
const SUGGESTION_STATUS_LABELS: Record<string, string> = {
  open: "待处理", accepted: "已接受", dismissed: "已忽略", applied: "已处理", archived: "已归档",
};
const EDITABLE_SUGGESTION_TYPES = new Set(["update_content", "improve_metadata", "improve_retrievability", "split_knowledge"]);
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
	  const [evalPromotingKey, setEvalPromotingKey] = useState<string | null>(null);
	  const [feedbackItems, setFeedbackItems] = useState<KnowledgeRetrievalFeedbackOut[]>([]);
	  const [feedbackTotal, setFeedbackTotal] = useState(0);
	  const [feedbackStatus, setFeedbackStatus] = useState("open");
	  const [feedbackType, setFeedbackType] = useState("");
	  const [feedbackSavingKey, setFeedbackSavingKey] = useState<string | null>(null);
	  const [suggestions, setSuggestions] = useState<KnowledgeImprovementSuggestionOut[]>([]);
	  const [suggestionTotal, setSuggestionTotal] = useState(0);
	  const [suggestionStatus, setSuggestionStatus] = useState("open");
	  const [suggestionType, setSuggestionType] = useState("");
	  const [suggestionMsg, setSuggestionMsg] = useState<string | null>(null);
	  const [suggestionSavingKey, setSuggestionSavingKey] = useState<string | null>(null);
	  const [guidedEditId, setGuidedEditId] = useState<string | null>(null);
	  const [guidedDraft, setGuidedDraft] = useState<Draft>(emptyDraft);
	  const [guidedReindex, setGuidedReindex] = useState(true);

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

	  const loadFeedback = useCallback(() => {
	    getKnowledgeRetrievalFeedback({
	      status: feedbackStatus || undefined,
	      feedback_type: feedbackType || undefined,
	    }).then((r) => { setFeedbackItems(r.items); setFeedbackTotal(r.total); }).catch(() => {});
	  }, [feedbackStatus, feedbackType]);

	  const loadSuggestions = useCallback(() => {
	    getKnowledgeImprovementSuggestions({
	      status: suggestionStatus || undefined,
	      suggestion_type: suggestionType || undefined,
	    }).then((r) => { setSuggestions(r.items); setSuggestionTotal(r.total); }).catch(() => {});
	  }, [suggestionStatus, suggestionType]);

  useEffect(() => { loadReview(); }, [loadReview]);
	  useEffect(() => { loadFeedback(); }, [loadFeedback]);
	  useEffect(() => { loadSuggestions(); }, [loadSuggestions]);

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
	    loadFeedback();
	    loadSuggestions();
	  }, [loadDocuments, loadEvalCases, loadFeedback, loadSuggestions]);

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

	  const promoteEvalCases = async (data: { feedback_ids?: string[]; suggestion_id?: string }, key: string) => {
	    setEvalPromotingKey(key); setSuggestionMsg(null); setError(null);
	    try {
	      const res = await promoteRetrievalEvalCases(data);
	      setSuggestionMsg(`已沉淀 ${res.created_count} 条评估用例，跳过 ${res.skipped_count} 条重复用例`);
	      loadEvalCases();
	      loadSuggestions();
	    } catch (e: unknown) {
	      setError(e instanceof Error ? e.message : "沉淀评估用例失败");
	    } finally {
	      setEvalPromotingKey(null);
	    }
	  };

	  const hitSnapshot = (hit: KnowledgeCitationHit, rank: number) => ({
	    knowledge_item_id: hit.knowledge_item_id,
	    title: hit.title,
	    score: hit.score,
	    keyword_score: hit.keyword_score ?? null,
	    vector_score: hit.vector_score ?? null,
	    rerank_score: hit.rerank_score ?? null,
	    retrieval_mode: hit.retrieval_mode ?? null,
	    match_reasons: hit.match_reasons ?? [],
	    excerpt: hit.excerpt,
	    rank,
	  });

	  const recordEvalHitFeedback = async (
	    result: RetrievalEvalResultOut,
	    hit: KnowledgeCitationHit,
	    rank: number,
	    feedbackType: "helpful" | "irrelevant" | "outdated" | "needs_review",
	  ) => {
	    const key = `${result.id}:${hit.knowledge_item_id}:${feedbackType}`;
	    setFeedbackSavingKey(key); setError(null);
	    try {
	      await createKnowledgeRetrievalFeedback({
	        feedback_type: feedbackType,
	        source: "retrieval_evaluation_result",
	        query: result.query,
	        knowledge_item_id: hit.knowledge_item_id,
	        retrieval_eval_result_id: result.id,
	        citation_hit_json: hitSnapshot(hit, rank),
	        metadata_json: { rank },
	      });
	      loadFeedback();
	    } catch (e: unknown) {
	      setError(e instanceof Error ? e.message : "记录检索反馈失败");
	    } finally {
	      setFeedbackSavingKey(null);
	    }
	  };

	  const recordMissingFeedback = async (result: RetrievalEvalResultOut, expectedId: string) => {
	    const key = `${result.id}:${expectedId}:missing`;
	    setFeedbackSavingKey(key); setError(null);
	    try {
	      await createKnowledgeRetrievalFeedback({
	        feedback_type: "missing",
	        source: "retrieval_evaluation_result",
	        query: result.query,
	        expected_knowledge_item_id: expectedId,
	        retrieval_eval_result_id: result.id,
	        note: `评估结果漏掉：${knowledgeTitle(expectedId)}`,
	        metadata_json: { result_status: result.status },
	      });
	      loadFeedback();
	    } catch (e: unknown) {
	      setError(e instanceof Error ? e.message : "记录漏召回失败");
	    } finally {
	      setFeedbackSavingKey(null);
	    }
	  };

	  const updateFeedbackStatus = async (id: string, nextStatus: KnowledgeRetrievalFeedbackStatus) => {
	    setFeedbackSavingKey(`${id}:${nextStatus}`); setError(null);
	    try {
	      await updateKnowledgeRetrievalFeedback(id, { status: nextStatus });
	      loadFeedback();
	    } catch (e: unknown) {
	      setError(e instanceof Error ? e.message : "更新反馈状态失败");
	    } finally {
	      setFeedbackSavingKey(null);
	    }
	  };

	  const generateSuggestions = async () => {
	    setSuggestionSavingKey("generate"); setSuggestionMsg(null); setError(null);
	    try {
	      const res = await generateKnowledgeImprovementSuggestions({ limit: 200 });
	      setSuggestionMsg(`已生成 ${res.created_count} 条，更新 ${res.updated_count} 条建议`);
	      loadSuggestions();
	    } catch (e: unknown) {
	      setError(e instanceof Error ? e.message : "生成知识改进建议失败");
	    } finally {
	      setSuggestionSavingKey(null);
	    }
	  };

	  const updateSuggestionStatus = async (id: string, nextStatus: KnowledgeImprovementSuggestionStatus) => {
	    setSuggestionSavingKey(`${id}:${nextStatus}`); setError(null);
	    try {
	      await updateKnowledgeImprovementSuggestion(id, { status: nextStatus });
	      loadSuggestions();
	    } catch (e: unknown) {
	      setError(e instanceof Error ? e.message : "更新知识改进建议失败");
	    } finally {
	      setSuggestionSavingKey(null);
	    }
	  };

	  const startGuidedEdit = (suggestion: KnowledgeImprovementSuggestionOut) => {
	    const item = items.find((it) => it.id === suggestion.knowledge_item_id);
	    if (!item) { setError("当前列表里没有找到这条知识，请切到 active 状态或刷新知识列表后再试"); return; }
	    setGuidedDraft(toDraft(item));
	    setGuidedEditId(suggestion.id);
	    setGuidedReindex(true);
	    setError(null);
	  };

	  const applyGuidedEdit = async (suggestionId: string) => {
	    if (!guidedDraft.title.trim() || !guidedDraft.content_markdown.trim()) { setError("标题和正文为必填"); return; }
	    setSuggestionSavingKey(`${suggestionId}:guided_edit`); setError(null); setSuggestionMsg(null);
	    try {
	      const res = await applyGuidedKnowledgeEdit(suggestionId, { patch: toPayload(guidedDraft), reindex: guidedReindex });
	      setSuggestionMsg(`已应用知识编辑${res.vector_status ? `，索引状态：${res.vector_status.status}` : ""}`);
	      setGuidedEditId(null);
	      load();
	      loadSuggestions();
	    } catch (e: unknown) {
	      setError(e instanceof Error ? e.message : "应用知识编辑失败");
	    } finally {
	      setSuggestionSavingKey(null);
	    }
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
	                  {r.missed_expected_ids.map((id) => (
	                    <span key={id} className="document-error">
	                      漏掉：{knowledgeTitle(id)}
	                      <button className="button ghost tiny" disabled={feedbackSavingKey === `${r.id}:${id}:missing`} onClick={() => recordMissingFeedback(r, id)}>
	                        记录漏召回
	                      </button>
	                    </span>
	                  ))}
	                  {r.error_message && <span className="document-error">{r.error_message}</span>}
	                  {r.citation_pack_json?.reranker_error && <span className="document-error">Reranker：{r.citation_pack_json.reranker_error}</span>}
	                </span>
	                {r.citation_pack_json?.hits && r.citation_pack_json.hits.length > 0 && (
	                  <span className="document-meta">
	                    {r.citation_pack_json.hits.slice(0, 5).map((h, idx) => (
	                      <span key={`${r.id}-${h.knowledge_item_id}`} className="eval-hit-feedback">
	                        #{idx + 1} {h.title || knowledgeTitle(h.knowledge_item_id)}
	                        {h.score != null ? ` · score ${h.score}` : ""}
	                        {h.reranked && h.rerank_score != null ? ` · rerank ${h.rerank_score}` : ""}
	                        {h.retrieval_mode ? ` · ${h.retrieval_mode}` : ""}
	                        <button className="button ghost tiny" disabled={feedbackSavingKey === `${r.id}:${h.knowledge_item_id}:helpful`} onClick={() => recordEvalHitFeedback(r, h, idx + 1, "helpful")}>有用</button>
	                        <button className="button ghost tiny" disabled={feedbackSavingKey === `${r.id}:${h.knowledge_item_id}:irrelevant`} onClick={() => recordEvalHitFeedback(r, h, idx + 1, "irrelevant")}>不相关</button>
	                        <button className="button ghost tiny" disabled={feedbackSavingKey === `${r.id}:${h.knowledge_item_id}:needs_review`} onClick={() => recordEvalHitFeedback(r, h, idx + 1, "needs_review")}>需检查</button>
	                      </span>
	                    ))}
	                  </span>
	                )}
	              </div>
	            ))}
	          </div>
	        )}
	      </section>

	      <section className="knowledge-review">
	        <div className="panel-heading"><h2>知识改进建议{suggestionTotal > 0 && ` · ${suggestionTotal} 条`}</h2></div>
	        <div className="review-toolbar">
	          <div className="stage-filter">
	            <select value={suggestionStatus} onChange={(e) => setSuggestionStatus(e.target.value)}>
	              <option value="">全部状态</option>
	              {Object.entries(SUGGESTION_STATUS_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
	            </select>
	          </div>
	          <div className="stage-filter">
	            <select value={suggestionType} onChange={(e) => setSuggestionType(e.target.value)}>
	              <option value="">全部类型</option>
	              {Object.entries(SUGGESTION_TYPE_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
	            </select>
	          </div>
	          <button className="button primary small" onClick={generateSuggestions} disabled={suggestionSavingKey === "generate"}>
	            {suggestionSavingKey === "generate" ? "生成中..." : "生成建议"}
	          </button>
	          <button className="button ghost small" onClick={loadSuggestions}>刷新</button>
	          {suggestionMsg && <span className="review-count">{suggestionMsg}</span>}
	        </div>
	        <div className="document-list">
	          {suggestions.length === 0 ? (
	            <p className="subresource-empty">暂无知识改进建议。可以先从检索评估或 Sales Reply 引用中记录反馈，再生成建议。</p>
	          ) : suggestions.map((s) => (
	            <div key={s.id} className="document-row">
	              <strong>{SUGGESTION_TYPE_LABELS[s.suggestion_type] || s.suggestion_type} · {s.title}</strong>
	              <span className="document-meta">
	                <span>{SUGGESTION_STATUS_LABELS[s.status] || s.status}</span>
	                {s.knowledge_item_id && <span>知识：{knowledgeTitle(s.knowledge_item_id)}</span>}
	                {s.confidence != null && <span>confidence {Math.round(s.confidence * 100)}%</span>}
	                <span>证据 {s.evidence_json?.feedback_count ?? s.source_feedback_ids.length} 条</span>
	                <span>{s.generator_version}</span>
	                <span>{new Date(s.created_at).toLocaleString()}</span>
	              </span>
	              <span className="document-meta suggestion-body">
	                <span>{s.reason}</span>
	                <span>{s.recommended_action}</span>
	              </span>
	              {s.evidence_json?.sample_queries && s.evidence_json.sample_queries.length > 0 && (
	                <span className="document-meta">
	                  {s.evidence_json.sample_queries.slice(0, 3).map((q) => <span key={q}>query：{q}</span>)}
	                </span>
	              )}
	              {s.status !== "dismissed" && s.status !== "applied" && s.status !== "archived" && (
	                <span className="document-meta">
	                  {s.status === "open" && <button className="button ghost small" disabled={suggestionSavingKey === `${s.id}:accepted`} onClick={() => updateSuggestionStatus(s.id, "accepted")}>接受</button>}
	                  {s.status === "open" && <button className="button ghost small" disabled={suggestionSavingKey === `${s.id}:dismissed`} onClick={() => updateSuggestionStatus(s.id, "dismissed")}>忽略</button>}
	                  {s.suggestion_type === "promote_eval_case" && (
	                    <button className="button ghost small" disabled={evalPromotingKey === `suggestion:${s.id}`} onClick={() => promoteEvalCases({ suggestion_id: s.id }, `suggestion:${s.id}`)}>
	                      {evalPromotingKey === `suggestion:${s.id}` ? "沉淀中..." : "沉淀为评估用例"}
	                    </button>
	                  )}
	                  {s.knowledge_item_id && EDITABLE_SUGGESTION_TYPES.has(s.suggestion_type) && (
	                    <button className="button ghost small" disabled={suggestionSavingKey === `${s.id}:guided_edit`} onClick={() => startGuidedEdit(s)}>
	                      编辑并应用
	                    </button>
	                  )}
	                  <button className="button ghost small" disabled={suggestionSavingKey === `${s.id}:applied`} onClick={() => updateSuggestionStatus(s.id, "applied")}>标记已处理</button>
	                  <button className="button ghost small" disabled={suggestionSavingKey === `${s.id}:archived`} onClick={() => updateSuggestionStatus(s.id, "archived")}>归档</button>
	                </span>
	              )}
	              {guidedEditId === s.id && (
	                <div className="guided-edit-box">
	                  <div className="subform-grid">
	                    <label className="subform-full">标题
	                      <input value={guidedDraft.title} onChange={(e) => setGuidedDraft((d) => ({ ...d, title: e.target.value }))} />
	                    </label>
	                    <label>摘要
	                      <input value={guidedDraft.summary} onChange={(e) => setGuidedDraft((d) => ({ ...d, summary: e.target.value }))} />
	                    </label>
	                    <label>标签
	                      <input value={guidedDraft.tags} onChange={(e) => setGuidedDraft((d) => ({ ...d, tags: e.target.value }))} />
	                    </label>
	                    <label>来源类型
	                      <select value={guidedDraft.source_type} onChange={(e) => setGuidedDraft((d) => ({ ...d, source_type: e.target.value }))}>
	                        {KNOWLEDGE_SOURCE_TYPES.map((t) => <option key={t} value={t}>{SOURCE_TYPE_LABELS[t]}</option>)}
	                      </select>
	                    </label>
	                    <label>状态
	                      <select value={guidedDraft.status} onChange={(e) => setGuidedDraft((d) => ({ ...d, status: e.target.value }))}>
	                        {STATUS_FILTERS.map((st) => <option key={st} value={st}>{STATUS_LABELS[st]}</option>)}
	                      </select>
	                    </label>
	                    <label className="subform-full">正文
	                      <textarea value={guidedDraft.content_markdown} onChange={(e) => setGuidedDraft((d) => ({ ...d, content_markdown: e.target.value }))} />
	                    </label>
	                  </div>
	                  <label className="review-count">
	                    <input type="checkbox" checked={guidedReindex} onChange={(e) => setGuidedReindex(e.target.checked)} /> 应用后重新索引
	                  </label>
	                  <div className="confirm-actions">
	                    <button className="button primary small" disabled={suggestionSavingKey === `${s.id}:guided_edit`} onClick={() => applyGuidedEdit(s.id)}>
	                      {suggestionSavingKey === `${s.id}:guided_edit` ? "应用中..." : "应用编辑"}
	                    </button>
	                    <button className="button ghost small" onClick={() => setGuidedEditId(null)}>取消</button>
	                  </div>
	                </div>
	              )}
	            </div>
	          ))}
	        </div>
	      </section>

	      <section className="knowledge-review">
	        <div className="panel-heading"><h2>检索反馈{feedbackTotal > 0 && ` · ${feedbackTotal} 条`}</h2></div>
	        <div className="review-toolbar">
	          <div className="stage-filter">
	            <select value={feedbackStatus} onChange={(e) => setFeedbackStatus(e.target.value)}>
	              <option value="">全部状态</option>
	              {Object.entries(FEEDBACK_STATUS_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
	            </select>
	          </div>
	          <div className="stage-filter">
	            <select value={feedbackType} onChange={(e) => setFeedbackType(e.target.value)}>
	              <option value="">全部类型</option>
	              {Object.entries(FEEDBACK_TYPE_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
	            </select>
	          </div>
	          <button className="button ghost small" onClick={loadFeedback}>刷新</button>
	        </div>
	        <div className="document-list">
	          {feedbackItems.length === 0 ? (
	            <p className="subresource-empty">暂无检索反馈</p>
	          ) : feedbackItems.map((fb) => (
	            <div key={fb.id} className="document-row">
	              <strong>{FEEDBACK_TYPE_LABELS[fb.feedback_type] || fb.feedback_type} · {fb.query || "未记录 query"}</strong>
	              <span className="document-meta">
	                <span>{FEEDBACK_STATUS_LABELS[fb.status] || fb.status}</span>
	                <span>{fb.source}</span>
	                {fb.knowledge_item_id && <span>命中项：{knowledgeTitle(fb.knowledge_item_id)}</span>}
	                {fb.expected_knowledge_item_id && <span>期望项：{knowledgeTitle(fb.expected_knowledge_item_id)}</span>}
	                {fb.note && <span>{fb.note}</span>}
	                <span>{new Date(fb.created_at).toLocaleString()}</span>
	              </span>
	              {fb.status !== "reviewed" && fb.status !== "resolved" && fb.status !== "archived" && (
	                <span className="document-meta">
	                  {(fb.feedback_type === "helpful" || (fb.feedback_type === "missing" && !!fb.expected_knowledge_item_id)) && (
	                    <button className="button ghost small" disabled={evalPromotingKey === `feedback:${fb.id}`} onClick={() => promoteEvalCases({ feedback_ids: [fb.id] }, `feedback:${fb.id}`)}>
	                      {evalPromotingKey === `feedback:${fb.id}` ? "沉淀中..." : "沉淀为评估用例"}
	                    </button>
	                  )}
	                  <button className="button ghost small" disabled={feedbackSavingKey === `${fb.id}:reviewed`} onClick={() => updateFeedbackStatus(fb.id, "reviewed")}>标记已查看</button>
	                  <button className="button ghost small" disabled={feedbackSavingKey === `${fb.id}:resolved`} onClick={() => updateFeedbackStatus(fb.id, "resolved")}>标记已解决</button>
	                  <button className="button ghost small" disabled={feedbackSavingKey === `${fb.id}:archived`} onClick={() => updateFeedbackStatus(fb.id, "archived")}>归档</button>
	                </span>
	              )}
	            </div>
	          ))}
	        </div>
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
