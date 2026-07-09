"use client";

import { useCallback, useEffect, useState } from "react";
import AdminShell from "@/components/admin/admin-shell";
import {
  archiveKnowledgeItem, createKnowledgeItem, getKnowledgeItems, getNotificationSummary,
  getServices, updateKnowledgeItem,
  KNOWLEDGE_SOURCE_TYPES, type KnowledgeItemInput, type KnowledgeItemOut, type ServiceOut,
} from "@/lib/admin-api";

const SOURCE_TYPE_LABELS: Record<string, string> = {
  manual: "手工录入", faq: "FAQ", case_study: "案例", methodology: "方法论",
  pricing_rule: "报价规则", contract_boundary: "合同边界", delivery_sop: "交付 SOP",
  service_note: "服务说明", external_doc: "外部文档",
};
const STATUS_LABELS: Record<string, string> = { draft: "草稿", active: "有效", archived: "已归档" };
const STATUS_FILTERS = ["active", "draft", "archived"];

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
  }, []);

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

  const serviceName = (id: string | null) => services.find((s) => s.id === id)?.name;

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
