"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import AdminShell from "@/components/admin/admin-shell";
import AgentWorkbench from "@/components/admin/agent-workbench";
import ApprovalGate from "@/components/admin/approval-gate";
import AuditTrail from "@/components/admin/audit-trail";
import ConversationThread from "@/components/admin/conversation-thread";
import StageBadge from "@/components/admin/stage-badge";
import {
  getOpportunityDetail,
  runSalesReplyAgent,
  type OpportunityDetail,
} from "@/lib/admin-api";

type PageState = "loading" | "empty" | "error" | "ready" | "running";

export default function OpportunityDetailPage() {
  const params = useParams();
  const opportunityId = params?.opportunityId as string;

  const [state, setState] = useState<PageState>("loading");
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<OpportunityDetail | null>(null);
  const [retryKey, setRetryKey] = useState(0);

  const doFetch = useCallback(async (id: string) => {
    setState("loading");
    setError(null);
    try {
      const res = await getOpportunityDetail(id);
      setData(res.opportunity);
      setState("ready");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Unknown error");
      setState("error");
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    if (!opportunityId) return;
    queueMicrotask(() => {
      if (cancelled) return;
      setState("loading");
      setError(null);
      getOpportunityDetail(opportunityId)
        .then((res) => { if (!cancelled) { setData(res.opportunity); setState("ready"); } })
        .catch((err: unknown) => { if (!cancelled) { setError(err instanceof Error ? err.message : "Unknown error"); setState("error"); } });
    });
    return () => { cancelled = true; };
  }, [opportunityId, retryKey]);

  const handleRunSalesAgent = async () => {
    if (!opportunityId) return;
    setState("running");
    try {
      await runSalesReplyAgent(opportunityId);
      await doFetch(opportunityId);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Workflow failed");
      setState("error");
    }
  };

  if (state === "loading") {
    return (
      <AdminShell active="opportunities" eyebrow="Loading..." title="Opportunity" subtitle="正在加载机会详情">
        <div className="loading-state">Loading...</div>
      </AdminShell>
    );
  }

  if (state === "error" || !data) {
    return (
      <AdminShell active="opportunities" eyebrow="Error" title="Opportunity" subtitle="加载失败">
        <div className="error-state">
          <p>加载失败：{error || "Unknown error"}</p>
          <button className="button primary" type="button" onClick={() => { setRetryKey((k) => k + 1); }}>重试</button>
        </div>
      </AdminShell>
    );
  }

  const isRunning = state === "running";
  const waitingDecision = data.decisions?.find((d) => d.status === "waiting");

  return (
    <AdminShell
      active="opportunities"
      eyebrow="Company Cockpit / Opportunity"
      title={data.title}
      subtitle={`${data.customer?.name || ""} · ${data.desired_outcome || ""}`}
    >
      <div className="detail-header">
        <Link className="button ghost" href="/admin/opportunities">← 返回机会列表</Link>
        <StageBadge stage={data.stage} />
        <span>{new Date(data.updated_at).toLocaleString()}</span>
      </div>

      <section className="opportunity-summary">
        <article>
          <span>Next Step</span>
          <strong>{data.next_step || "未设置下一步"}</strong>
        </article>
        <article>
          <span>Estimated Value</span>
          <strong>{data.estimated_value ? `¥${data.estimated_value.toLocaleString()}` : "待估算"}</strong>
        </article>
        <article>
          <span>Probability</span>
          <strong>{data.probability != null ? `${data.probability}%` : "N/A"}</strong>
        </article>
      </section>

      {/* FE-03: Run Sales Agent */}
      <section className="agent-actions" aria-label="Agent actions">
        <button
          className="button primary"
          type="button"
          onClick={handleRunSalesAgent}
          disabled={isRunning}
        >
          {isRunning ? "Running Sales Agent..." : "Run Sales Agent"}
        </button>
        {isRunning && <span className="running-indicator">Agent 运行中，请稍候...</span>}
        {data.agent_runs && data.agent_runs.length > 0 && (
          <small className="meta">{data.agent_runs.length} agent run(s) recorded</small>
        )}
      </section>

      <div className="opportunity-detail-grid">
        <div className="detail-main">
          {/* FE-04+06: Agent Workbench */}
          <AgentWorkbench
            artifacts={data.artifacts || []}
            agentRuns={data.agent_runs || []}
          />

          {/* Conversation Thread */}
          <ConversationThread messages={data.recent_messages || []} />

          {/* FE-07: Audit Trail */}
          <AuditTrail logs={data.audit_logs || []} />
        </div>

        <aside className="detail-sidebar">
          {/* Customer & contact info */}
          <section className="opportunity-inspector" aria-label="Customer info">
            {data.customer && (
              <div className="inspector-section">
                <div className="inspector-title"><span>Customer</span><strong>{data.customer.name}</strong></div>
                <dl>
                  <div><dt>Email</dt><dd>{data.customer.owner_email}</dd></div>
                  <div><dt>Industry</dt><dd>{data.customer.industry || "N/A"}</dd></div>
                  <div><dt>Size</dt><dd>{data.customer.company_size || "N/A"}</dd></div>
                </dl>
              </div>
            )}
            {data.primary_contact && (
              <div className="inspector-section">
                <div className="inspector-title"><span>Contact</span><strong>{data.primary_contact.name || "N/A"}</strong></div>
                <dl>
                  <div><dt>Email</dt><dd>{data.primary_contact.email || "N/A"}</dd></div>
                  <div><dt>Method</dt><dd>{data.primary_contact.contact_method || "N/A"}</dd></div>
                </dl>
              </div>
            )}
            <div className="inspector-section">
              <div className="inspector-title"><span>Opportunity</span></div>
              <dl>
                <div><dt>Budget</dt><dd>{data.budget_range || "N/A"}</dd></div>
                <div><dt>Problem</dt><dd>{data.problem_summary || "N/A"}</dd></div>
              </dl>
            </div>
          </section>

          {/* FE-05: Approval Gate */}
          <ApprovalGate decisions={data.decisions || []} onDecisionChanged={() => { setRetryKey((k) => k + 1); }} />
        </aside>
      </div>

      {/* FE-09: Status indicator */}
      {waitingDecision && (
        <div className="status-bar waiting-approval">
          <span>⏳</span> 等待审批 &mdash; Decision {waitingDecision.id.slice(0, 8)}...
        </div>
      )}
    </AdminShell>
  );
}
