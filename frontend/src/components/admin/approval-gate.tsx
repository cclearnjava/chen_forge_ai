"use client";

import { useState } from "react";
import { approveDecision, requestRewrite, type DecisionOut } from "@/lib/admin-api";

export default function ApprovalGate({
  decisions,
  onDecisionChanged,
}: {
  decisions: DecisionOut[];
  onDecisionChanged?: () => void;
}) {
  const [acting, setActing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const waiting = decisions.filter((d) => d.status === "waiting");
  const latest = waiting[0];

  const handleAction = async (action: "approve" | "rewrite") => {
    if (!latest) return;
    setActing(true);
    setError(null);
    try {
      if (action === "approve") {
        await approveDecision(latest.id);
      } else {
        await requestRewrite(latest.id);
      }
      onDecisionChanged?.();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Action failed");
    } finally {
      setActing(false);
    }
  };

  return (
    <aside className="approval-gate" aria-label="Approval gate">
      <div className="inspector-title">
        <span>Approval Gate</span>
      </div>

      {!latest ? (
        <div className="empty-state small">
          <p>当前没有待审批</p>
          <small>运行 Sales Agent 后会生成等待审批的 Decision。</small>
        </div>
      ) : (
        <div className="approval-card">
          <div className="approval-question">
            <span className="badge attention">等待审批</span>
            <p>{latest.question}</p>
          </div>

          {latest.recommendation && (
            <div className="approval-recommendation">
              <small>Agent 建议</small>
              <strong>{latest.recommendation}</strong>
            </div>
          )}

          {error && <p className="error-msg">{error}</p>}

          <div className="approval-actions">
            <button
              className="button primary"
              type="button"
              disabled={acting}
              onClick={() => handleAction("approve")}
            >
              {acting ? "Processing..." : "Approve"}
            </button>
            <button
              className="button ghost"
              type="button"
              disabled={acting}
              onClick={() => handleAction("rewrite")}
            >
              Request rewrite
            </button>
          </div>

          <small className="meta">created: {new Date(latest.created_at).toLocaleString()}</small>
        </div>
      )}

      {waiting.length > 1 && (
        <small className="meta">+{waiting.length - 1} more waiting decisions</small>
      )}
    </aside>
  );
}
