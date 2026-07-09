"use client";

import Link from "next/link";
import type { ArtifactOut, AgentRunOut, CitationPack } from "@/lib/admin-api";
import CitationPackView from "@/components/admin/citation-pack";

type ContextUsage = {
  service_hit_count?: number;
  knowledge_hit_count?: number;
  service_names?: string[];
  knowledge_titles?: string[];
  context_builder_version?: string;
};

function riskColor(level: string) {
  if (level === "high") return "var(--color-danger, #dc2626)";
  if (level === "medium") return "var(--color-warn, #d97706)";
  return "var(--color-success, #16a34a)";
}

function findArtifact(artifacts: ArtifactOut[], type: string) {
  return artifacts.find((a) => a.type === type);
}

export default function AgentWorkbench({
  artifacts,
  agentRuns,
  qualityReview,
}: {
  artifacts: ArtifactOut[];
  agentRuns: AgentRunOut[];
  qualityReview?: {
    risk_level: "low" | "medium" | "high";
    risk_flags: Array<{ type: string; keyword?: string; detail?: string }>;
    summary: string;
    recommendation: string;
  } | null;
}) {
  const draft = findArtifact(artifacts, "customer_reply_draft");
  const questions = findArtifact(artifacts, "discovery_questions");
  const review = findArtifact(artifacts, "review");
  const proposal = findArtifact(artifacts, "proposal_draft");
  const followupReply = findArtifact(artifacts, "proposal_followup_reply_draft");
  const objection = findArtifact(artifacts, "objection_analysis");
  const nextStep = findArtifact(artifacts, "next_step_recommendation");
  const quote = findArtifact(artifacts, "quote_draft");
  const sow = findArtifact(artifacts, "sow_draft");
  const commReview = findArtifact(artifacts, "commercial_review");

  const contextUsage = (draft?.content_json?.context_usage as ContextUsage | undefined) ?? undefined;
  const citationPack = (draft?.content_json?.citations as CitationPack | undefined) ?? null;

  if (!draft && !review && !proposal && !followupReply && !objection && !nextStep && !quote && !sow && !commReview) {
    return (
      <section className="agent-workbench" aria-label="Agent output">
        <div className="empty-state">
          <p>尚未运行 Sales Agent</p>
          <small>点击上方 Run Sales Agent 生成客户回复草稿和风险审查。</small>
        </div>
      </section>
    );
  }

  return (
    <section className="agent-workbench" aria-label="Agent output">
      {draft && (
        <article className="workbench-card">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Sales Agent</p>
              <h2>客户回复草稿</h2>
            </div>
            <span className="badge">requires approval</span>
          </div>
          <div className="markdown-body" style={{ whiteSpace: "pre-wrap" }}>
            {draft.content_markdown}
          </div>
          <small className="meta">model: {draft.model} · {new Date(draft.created_at).toLocaleString()}</small>
        </article>
      )}

      {contextUsage && (
        <article className="workbench-card context-usage-card">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Context Builder</p>
              <h2>本次回复使用的上下文</h2>
            </div>
            <span className="badge">{contextUsage.context_builder_version || "context_builder.v1"}</span>
          </div>
          <div className="context-usage-counts">
            <span>服务命中：<strong>{contextUsage.service_hit_count ?? 0}</strong></span>
            <span>知识命中：<strong>{contextUsage.knowledge_hit_count ?? 0}</strong></span>
          </div>
          {contextUsage.service_names && contextUsage.service_names.length > 0 && (
            <div className="context-usage-list">
              <small>服务</small>
              <ul>{contextUsage.service_names.map((n, i) => <li key={i}>{n}</li>)}</ul>
            </div>
          )}
          {contextUsage.knowledge_titles && contextUsage.knowledge_titles.length > 0 && (
            <div className="context-usage-list">
              <small>知识</small>
              <ul>{contextUsage.knowledge_titles.map((t, i) => <li key={i}>{t}</li>)}</ul>
            </div>
          )}
          {(contextUsage.knowledge_hit_count ?? 0) === 0 && (
            <p className="context-usage-empty">
              当前回复未使用 Workspace 知识。可以先到 <Link href="/admin/knowledge">Knowledge 页面</Link> 维护 FAQ、案例、报价规则或交付 SOP。
            </p>
          )}
        </article>
      )}

      <CitationPackView citations={citationPack} />

      {questions?.content_json && (
        <article className="workbench-card">
          <div className="panel-heading">
            <h2>澄清问题</h2>
          </div>
          <ul className="question-list">
            {(questions.content_json.questions as string[]).map((q, i) => (
              <li key={i}>{q}</li>
            ))}
          </ul>
        </article>
      )}

      {qualityReview && (
        <article className="workbench-card">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Quality Agent</p>
              <h2>Quality Review</h2>
            </div>
            <span className="risk-badge" style={{ background: riskColor(qualityReview.risk_level) }}>
              {qualityReview.risk_level}
            </span>
          </div>
          <p className="review-summary">{qualityReview.summary}</p>
          {qualityReview.risk_flags.length > 0 && (
            <ul className="risk-flags">
              {qualityReview.risk_flags.map((f, i) => (
                <li key={i} className={f.type}>
                  <strong>{f.type}</strong>
                  {f.keyword && <span> · keyword: &ldquo;{f.keyword}&rdquo;</span>}
                  {f.detail && <span> · {f.detail}</span>}
                </li>
              ))}
            </ul>
          )}
          <p className="recommendation">
            Recommendation: <strong>{qualityReview.recommendation}</strong>
          </p>
        </article>
      )}

      {proposal && (
        <article className="workbench-card">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Proposal Agent</p>
              <h2>PoC 方案草案</h2>
            </div>
            <span className="badge">requires approval</span>
          </div>
          <div className="markdown-body" style={{ whiteSpace: "pre-wrap" }}>
            {proposal.content_markdown}
          </div>
          <small className="meta">model: {proposal.model} · {new Date(proposal.created_at).toLocaleString()}</small>
        </article>
      )}

      {followupReply && (
        <article className="workbench-card">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Proposal Follow-up Agent</p>
              <h2>Proposal Follow-up 回复草稿</h2>
            </div>
            <span className="badge">requires approval</span>
          </div>
          <div className="markdown-body" style={{ whiteSpace: "pre-wrap" }}>
            {followupReply.content_markdown}
          </div>
          <small className="meta">model: {followupReply.model} · {new Date(followupReply.created_at).toLocaleString()}</small>
        </article>
      )}

      {objection && (
        <article className="workbench-card">
          <div className="panel-heading"><h2>异议分析</h2></div>
          <div className="markdown-body" style={{ whiteSpace: "pre-wrap" }}>
            {objection.content_markdown}
          </div>
        </article>
      )}

      {nextStep && (
        <article className="workbench-card">
          <div className="panel-heading"><h2>下一步建议</h2></div>
          <div className="markdown-body" style={{ whiteSpace: "pre-wrap" }}>
            {nextStep.content_markdown}
          </div>
        </article>
      )}

      {quote && (
        <article className="workbench-card">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Quote / SOW Agent</p>
              <h2>Quote Draft</h2>
            </div>
            <span className="badge">requires approval</span>
          </div>
          <div className="markdown-body" style={{ whiteSpace: "pre-wrap" }}>{quote.content_markdown}</div>
        </article>
      )}
      {sow && (
        <article className="workbench-card">
          <div className="panel-heading"><h2>SOW Draft</h2><span className="badge">requires approval</span></div>
          <div className="markdown-body" style={{ whiteSpace: "pre-wrap" }}>{sow.content_markdown}</div>
        </article>
      )}
      {commReview && (
        <article className="workbench-card">
          <div className="panel-heading"><h2>Commercial Review</h2></div>
          <div className="markdown-body" style={{ whiteSpace: "pre-wrap" }}>{commReview.content_markdown}</div>
        </article>
      )}

      {agentRuns.length > 0 && (
        <article className="workbench-card">
          <div className="panel-heading">
            <h2>Agent Run Timeline</h2>
          </div>
          <div className="timeline">
            {agentRuns.map((run) => (
              <div className="timeline-item" key={run.id}>
                <div className="timeline-dot" data-status={run.status} />
                <div>
                  <strong>{run.agent_profile_id}</strong>
                  <small>status: {run.status}</small>
                  {run.started_at && <small>start: {new Date(run.started_at).toLocaleTimeString()}</small>}
                  {run.completed_at && <small>end: {new Date(run.completed_at).toLocaleTimeString()}</small>}
                </div>
              </div>
            ))}
          </div>
        </article>
      )}
    </section>
  );
}
