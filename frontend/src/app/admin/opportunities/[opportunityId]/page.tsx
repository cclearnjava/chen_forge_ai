"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import AdminShell from "@/components/admin/admin-shell";
import AgentWorkbench from "@/components/admin/agent-workbench";
import ApprovalGate from "@/components/admin/approval-gate";
import AuditTrail from "@/components/admin/audit-trail";
import ConversationThread from "@/components/admin/conversation-thread";
import CustomerReplyComposer from "@/components/admin/customer-reply-composer";
import DeliveryPanel from "@/components/admin/delivery-panel";
import StageBadge from "@/components/admin/stage-badge";
import {
  getOpportunityCockpit,
  runProposalDraftAgent,
  runSalesReplyAgent,
  type AdminOpportunityCockpit,
} from "@/lib/admin-api";

type PageState = "loading" | "empty" | "error" | "ready" | "running";

export default function OpportunityDetailPage() {
  const params = useParams();
  const opportunityId = params?.opportunityId as string;

  const [state, setState] = useState<PageState>("loading");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [cockpit, setCockpit] = useState<AdminOpportunityCockpit | null>(null);
  const [retryKey, setRetryKey] = useState(0);

  const doFetch = useCallback(async (id: string) => {
    setState("loading");
    setErrorMsg(null);
    try {
      const data = await getOpportunityCockpit(id);
      setCockpit(data);
      setState("ready");
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : "Unknown error");
      setState("error");
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    if (!opportunityId) return;
    queueMicrotask(() => {
      if (cancelled) return;
      setState("loading");
      setErrorMsg(null);
      getOpportunityCockpit(opportunityId)
        .then((data) => { if (!cancelled) { setCockpit(data); setState("ready"); } })
        .catch((err: unknown) => { if (!cancelled) { setErrorMsg(err instanceof Error ? err.message : "Unknown error"); setState("error"); } });
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
      setErrorMsg(err instanceof Error ? err.message : "Workflow failed");
      setState("error");
    }
  };

  const handleGenerateProposal = async () => {
    if (!opportunityId) return;
    setState("running");
    try {
      await runProposalDraftAgent(opportunityId);
      await doFetch(opportunityId);
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : "Proposal generation failed");
      setState("error");
    }
  };

  if (state === "loading") {
    return (
      <AdminShell active="opportunities" eyebrow="Loading..." title="Opportunity" subtitle="正在加载">
        <div className="loading-state">Loading...</div>
      </AdminShell>
    );
  }

  if (state === "error" || !cockpit) {
    const is404 = errorMsg?.includes("404");
    return (
      <AdminShell active="opportunities" eyebrow={is404 ? "Not Found" : "Error"} title="Opportunity" subtitle={is404 ? "机会不存在" : "加载失败"}>
        <div className="error-state">
          <p>{is404 ? "该机会不存在或已被删除" : `加载失败：${errorMsg || "Unknown error"}`}</p>
          {!is404 && <button className="button primary" type="button" onClick={() => setRetryKey((k) => k + 1)}>重试</button>}
        </div>
      </AdminShell>
    );
  }

  const opp = cockpit.opportunity;
  const isRunning = state === "running";
  const waitingDecision = cockpit.decisions?.find((d) => d.status === "waiting");

  // Cockpit messages — already in ConversationThread-compatible format
  const messages = cockpit.messages || [];

  return (
    <AdminShell
      active="opportunities"
      eyebrow="Company Cockpit / Opportunity"
      title={opp.title}
      subtitle={`${cockpit.customer?.name || ""} · ${opp.desired_outcome || ""}`}
    >
      <div className="detail-header">
        <Link className="button ghost" href="/admin/opportunities">← 返回机会列表</Link>
        <StageBadge stage={opp.stage} />
        <span>{new Date(opp.updated_at).toLocaleString()}</span>
      </div>

      <section className="opportunity-summary">
        <article><span>Next Step</span><strong>{opp.next_step || "未设置下一步"}</strong></article>
        <article><span>Estimated Value</span><strong>{opp.estimated_value ? `¥${opp.estimated_value.toLocaleString()}` : "待估算"}</strong></article>
        <article><span>Probability</span><strong>{opp.probability != null ? `${opp.probability}%` : "N/A"}</strong></article>
      </section>

      <section className="agent-actions" aria-label="Agent actions">
        <button className="button primary" type="button" onClick={handleRunSalesAgent} disabled={isRunning}>
          {isRunning ? "Running..." : "Run Sales Agent"}
        </button>
        <button className="button primary" type="button" onClick={handleGenerateProposal} disabled={isRunning}>
          {isRunning ? "Running..." : "Generate Proposal Draft"}
        </button>
        {isRunning && <span className="running-indicator">Agent 运行中，请稍候...</span>}
        {cockpit.agent_runs.length > 0 && <small className="meta">{cockpit.agent_runs.length} agent run(s) recorded</small>}
      </section>

      <div className="opportunity-detail-grid">
        <div className="detail-main">
          <AgentWorkbench artifacts={cockpit.artifacts} agentRuns={cockpit.agent_runs} />
          <ConversationThread messages={messages} />
          <CustomerReplyComposer
            opportunityId={opportunityId}
            onRecorded={() => { setRetryKey((k) => k + 1); }}
          />
          <AuditTrail logs={cockpit.audit_logs} />
        </div>

        <aside className="detail-sidebar">
          <section className="opportunity-inspector" aria-label="Customer info">
            {cockpit.customer && (
              <div className="inspector-section">
                <div className="inspector-title"><span>Customer</span><strong>{cockpit.customer.name}</strong></div>
                <dl>
                  <div><dt>Email</dt><dd>{cockpit.customer.owner_email}</dd></div>
                  <div><dt>Industry</dt><dd>{cockpit.customer.industry || "N/A"}</dd></div>
                  <div><dt>Size</dt><dd>{cockpit.customer.company_size || "N/A"}</dd></div>
                </dl>
              </div>
            )}
            {cockpit.contact && (
              <div className="inspector-section">
                <div className="inspector-title"><span>Contact</span><strong>{cockpit.contact.name || "N/A"}</strong></div>
                <dl>
                  <div><dt>Email</dt><dd>{cockpit.contact.email || "N/A"}</dd></div>
                  <div><dt>Method</dt><dd>{cockpit.contact.contact_method || "N/A"}</dd></div>
                </dl>
              </div>
            )}
            <div className="inspector-section">
              <div className="inspector-title"><span>Opportunity</span></div>
              <dl>
                <div><dt>Budget</dt><dd>{opp.budget_range || "N/A"}</dd></div>
                <div><dt>Problem</dt><dd>{opp.problem_summary || "N/A"}</dd></div>
              </dl>
            </div>
          </section>

          <ApprovalGate decisions={cockpit.decisions} onDecisionChanged={() => { setRetryKey((k) => k + 1); }} />

          <DeliveryPanel jobs={cockpit.delivery_jobs} onDeliveryChanged={() => { setRetryKey((k) => k + 1); }} />
        </aside>
      </div>

      {waitingDecision && (
        <div className="status-bar waiting-approval">
          <span>⏳</span> 等待审批 — Decision {waitingDecision.id.slice(0, 8)}...
        </div>
      )}
    </AdminShell>
  );
}
