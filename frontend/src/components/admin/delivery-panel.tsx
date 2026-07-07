"use client";

import { useState } from "react";
import { markDeliveryJobSent, type CockpitDeliveryJob } from "@/lib/admin-api";

function errorMessage(err: unknown): string {
  if (!(err instanceof Error)) return "Unknown error";
  const msg = err.message;
  if (msg.includes("404")) return "发送任务不存在";
  if (msg.includes("409")) return "发送任务已处理";
  return msg;
}

export default function DeliveryPanel({
  jobs,
  onDeliveryChanged,
}: {
  jobs: CockpitDeliveryJob[];
  onDeliveryChanged?: () => void;
}) {
  const [actingId, setActingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleMarkSent = async (jobId: string) => {
    setActingId(jobId);
    setError(null);
    try {
      await markDeliveryJobSent(jobId);
      onDeliveryChanged?.();
    } catch (err: unknown) {
      setError(errorMessage(err));
    } finally {
      setActingId(null);
    }
  };

  if (jobs.length === 0) {
    return (
      <section className="delivery-panel" aria-label="Delivery jobs">
        <div className="inspector-title"><span>Delivery</span></div>
        <div className="empty-state small">
          <p>无待发送任务</p>
          <small>审批通过后会在此生成发送任务。</small>
        </div>
      </section>
    );
  }

  return (
    <section className="delivery-panel" aria-label="Delivery jobs">
      <div className="inspector-title"><span>Delivery</span></div>
      {error && <p className="error-msg">{error}</p>}
      {jobs.map((j) => (
        <div className={`delivery-item ${j.status}`} key={j.id}>
          <strong>{j.subject}</strong>
          {j.subject?.includes("PoC Proposal") && <span className="badge proposal">Proposal PDF</span>}
          {(j.subject?.includes("Quote / SOW") || j.subject?.includes("Quote/SOW")) && <span className="badge proposal">Quote / SOW</span>}
          <dl>
            <div><dt>Recipient</dt><dd>{j.recipient}</dd></div>
            <div><dt>Channel</dt><dd>{j.channel}</dd></div>
            <div><dt>Status</dt><dd>{j.status}</dd></div>
            <div><dt>Created</dt><dd>{new Date(j.created_at).toLocaleString()}</dd></div>
            {j.sent_at && <div><dt>Sent</dt><dd>{new Date(j.sent_at).toLocaleString()}</dd></div>}
          </dl>
          {j.body_markdown && (
            <details>
              <summary>正文预览</summary>
              <pre style={{ whiteSpace: "pre-wrap", fontSize: "0.8rem" }}>{j.body_markdown.slice(0, 300)}{j.body_markdown.length > 300 ? "..." : ""}</pre>
            </details>
          )}
          {j.status === "draft" && (
            <button
              className="button primary small"
              type="button"
              disabled={actingId === j.id}
              onClick={() => handleMarkSent(j.id)}
            >
              {actingId === j.id ? "..." : "Mark sent"}
            </button>
          )}
          {j.status === "sent" && (
            <small className="meta">已在 {j.sent_at ? new Date(j.sent_at).toLocaleString() : "?"} 确认发送</small>
          )}
        </div>
      ))}
    </section>
  );
}
