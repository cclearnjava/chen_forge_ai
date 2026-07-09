import Link from "next/link";
import type { CitationPack } from "@/lib/admin-api";

const SOURCE_TYPE_LABELS: Record<string, string> = {
  manual: "手工录入", faq: "FAQ", case_study: "案例", methodology: "方法论",
  pricing_rule: "报价规则", contract_boundary: "合同边界", delivery_sop: "交付 SOP",
  service_note: "服务说明", external_doc: "外部文档",
};
const MATCH_REASON_LABELS: Record<string, string> = {
  title: "标题匹配", summary: "摘要匹配", content: "正文匹配",
  tags: "标签匹配", service_link: "关联服务", source_type_priority: "类型优先",
};

export default function CitationPackView({ citations }: { citations: CitationPack | null }) {
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
        {citations.hits.slice(0, 5).map((h) => (
          <div className="citation-item" key={h.knowledge_item_id}>
            <div className="citation-main">
              <strong>{h.title}</strong>
              {h.excerpt && <span className="citation-excerpt">{h.excerpt}</span>}
            </div>
            <div className="citation-meta">
              <span>{SOURCE_TYPE_LABELS[h.source_type] || h.source_type}</span>
              {h.source?.document_filename && (
                <span>{h.source.document_filename}{h.source.chunk_index != null ? ` · 片段 ${h.source.chunk_index + 1}` : ""}</span>
              )}
              {h.match_reasons.map((r) => (
                <span className="citation-reason-tag" key={r}>{MATCH_REASON_LABELS[r] || r}</span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
