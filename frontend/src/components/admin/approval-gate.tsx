"use client";

import { useState } from "react";
import { approveDecision, requestRewrite, type DecisionOut } from "@/lib/admin-api";

const statusLabels: Record<string, string> = {
  waiting: "等待审批",
  approved: "已批准",
  rewrite_requested: "已要求重写",
  deferred: "已延后",
  edited_and_approved: "已编辑并批准",
};

function errorMessage(err: unknown): string {
  if (!(err instanceof Error)) return "Unknown error";
  const msg = err.message;
  if (msg.includes("409")) return "该审批已处理";
  if (msg.includes("422")) return "审批上下文不完整";
  return msg;
}

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
  const latestWaiting = waiting[0];
  const latestResolved = decisions.find((d) => d.status !== "waiting");

  const handleAction = async (action: "approve" | "rewrite") => {
    if (!latestWaiting) return;
    setActing(true);
    setError(null);
    try {
      if (action === "approve") {
        await approveDecision(latestWaiting.id);
      } else {
        await requestRewrite(latestWaiting.id);
      }
      onDecisionChanged?.();
    } catch (err: unknown) {
      setError(errorMessage(err));
    } finally {
      setActing(false);
    }
  };

  return (
    <aside className="approval-gate" aria-label="Approval gate">
      <div className="inspector-title">
        <span>Approval Gate</span>
      </div>

      {/* Waiting decision — show approve/rewrite controls */}
      {latestWaiting && (
        <div className="approval-card">
          <div className="approval-question">
            <span className="badge attention">等待审批</span>
            <p>{latestWaiting.question}</p>
          </div>

          {latestWaiting.recommendation && (
            <div className="approval-recommendation">
              <small>Agent 建议</small>
              <strong>{latestWaiting.recommendation}</strong>
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

          <small className="meta">created: {new Date(latestWaiting.created_at).toLocaleString()}</small>

          {waiting.length > 1 && (
            <small className="meta">+{waiting.length - 1} more waiting decisions</small>
          )}
        </div>
      )}

      {/* Resolved decision — show status summary */}
      {!latestWaiting && latestResolved && (
        <div className="approval-card resolved">
          <div className="approval-question">
            <span className={`badge ${latestResolved.status === "approved" ? "" : "attention"}`}>
              {statusLabels[latestResolved.status] || latestResolved.status}
            </span>
            <p>{latestResolved.question}</p>
          </div>

          {latestResolved.operator_note && (
            <div className="approval-recommendation">
              <small>备注</small>
              <strong>{latestResolved.operator_note}</strong>
            </div>
          )}

          {latestResolved.resolved_at && (
            <small className="meta">
              {latestResolved.status === "approved" ? "approved" : "resolved"}:{" "}
              {new Date(latestResolved.resolved_at).toLocaleString()}
            </small>
          )}
        </div>
      )}

      {/* No decisions at all */}
      {!latestWaiting && !latestResolved && (
        <div className="empty-state small">
          <p>当前没有待审批</p>
          <small>运行 Sales Agent 后会生成等待审批的 Decision。</small>
        </div>
      )}
    </aside>
  );
}
