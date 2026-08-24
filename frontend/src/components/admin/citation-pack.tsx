"use client";

import Link from "next/link";
import { useState } from "react";
import {
  createKnowledgeRetrievalFeedback,
  type CitationPack,
  type KnowledgeCitationHit,
  type KnowledgeRetrievalFeedbackType,
} from "@/lib/admin-api";

const SOURCE_TYPE_LABELS: Record<string, string> = {
  manual: "手工录入", faq: "FAQ", case_study: "案例", methodology: "方法论",
  pricing_rule: "报价规则", contract_boundary: "合同边界", delivery_sop: "交付 SOP",
  service_note: "服务说明", external_doc: "外部文档",
};
const MATCH_REASON_LABELS: Record<string, string> = {
  title: "标题匹配", summary: "摘要匹配", content: "正文匹配",
  tags: "标签匹配", service_link: "关联服务", source_type_priority: "类型优先",
  vector: "语义匹配",
};
const RETRIEVAL_MODE_LABELS: Record<string, string> = {
  keyword: "关键词命中", vector: "语义命中", hybrid: "混合命中",
};

type CitationPackViewProps = {
  citations: CitationPack | null;
  artifactId?: string;
  opportunityId?: string;
};

const FEEDBACK_ACTIONS: Array<{ type: KnowledgeRetrievalFeedbackType; label: string }> = [
  { type: "helpful", label: "有用" },
  { type: "irrelevant", label: "不相关" },
  { type: "outdated", label: "过时" },
  { type: "needs_review", label: "需检查" },
];

function hitSnapshot(hit: KnowledgeCitationHit, rank: number): Record<string, unknown> {
  return {
    knowledge_item_id: hit.knowledge_item_id,
    title: hit.title,
    summary: hit.summary ?? null,
    source_type: hit.source_type,
    score: hit.score,
    keyword_score: hit.keyword_score ?? null,
    vector_score: hit.vector_score ?? null,
    rerank_score: hit.rerank_score ?? null,
    retrieval_mode: hit.retrieval_mode ?? null,
    excerpt: hit.excerpt,
    source: hit.source ?? null,
    rank,
  };
}

export default function CitationPackView({ citations, artifactId, opportunityId }: CitationPackViewProps) {
  const [savingKey, setSavingKey] = useState<string | null>(null);
  const [saved, setSaved] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  if (!citations) return null;

  if (!citations.hits || citations.hits.length === 0) {
    return (
      <div className="citation-pack">
        <div className="citation-empty">
          本次回复未命中 Workspace 知识。
          <Link href="/admin/knowledge">去维护知识库</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="citation-pack">
      <h3>使用知识依据</h3>
      <div className="citation-list">
        {citations.hits.slice(0, 5).map((h, idx) => (
          <div className="citation-item" key={h.knowledge_item_id}>
            <div className="citation-main">
              <strong>{h.title}</strong>
              {h.excerpt && <span className="citation-excerpt">{h.excerpt}</span>}
            </div>
            <div className="citation-meta">
              {((h as KnowledgeCitationHit & { retrieval_mode?: string }).retrieval_mode) && (
                <span className="retrieval-mode-tag">{RETRIEVAL_MODE_LABELS[(h as KnowledgeCitationHit & { retrieval_mode?: string }).retrieval_mode!] || (h as KnowledgeCitationHit & { retrieval_mode?: string }).retrieval_mode}</span>
              )}
              <span>{SOURCE_TYPE_LABELS[h.source_type] || h.source_type}</span>
              {h.source?.document_filename && (
                <span>{h.source.document_filename}{h.source.chunk_index != null ? ` · 片段 ${h.source.chunk_index + 1}` : ""}</span>
              )}
              {h.match_reasons.map((r) => (
                <span className="citation-reason-tag" key={r}>{MATCH_REASON_LABELS[r] || r}</span>
              ))}
              {h.reranked && h.rerank_score != null && <span className="citation-reason-tag">rerank {h.rerank_score}</span>}
            </div>
            <div className="citation-feedback-actions">
              {FEEDBACK_ACTIONS.map((action) => {
                const key = `${h.knowledge_item_id}:${action.type}`;
                return (
                  <button
                    key={action.type}
                    className="button ghost tiny"
                    disabled={savingKey === key || saved[h.knowledge_item_id] === action.type}
                    onClick={async () => {
                      setSavingKey(key);
                      setError(null);
                      try {
                        await createKnowledgeRetrievalFeedback({
                          feedback_type: action.type,
                          source: "sales_reply_citation",
                          query: citations.query_summary ?? null,
                          knowledge_item_id: h.knowledge_item_id,
                          artifact_id: artifactId ?? null,
                          opportunity_id: opportunityId ?? null,
                          citation_hit_json: hitSnapshot(h, idx + 1),
                          metadata_json: { rank: idx + 1 },
                        });
                        setSaved((prev) => ({ ...prev, [h.knowledge_item_id]: action.type }));
                      } catch (err: unknown) {
                        setError(err instanceof Error ? err.message : "反馈记录失败");
                      } finally {
                        setSavingKey(null);
                      }
                    }}
                  >
                    {saved[h.knowledge_item_id] === action.type ? "已记录" : action.label}
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>
      {error && <p className="citation-feedback-error">{error}</p>}
    </div>
  );
}
