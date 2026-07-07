"use client";

import { useEffect, useState } from "react";
import { createApprovedQuoteSowDeliveryJob, getApprovedQuoteSow, type ApprovedQuoteSowData } from "@/lib/admin-api";

export default function ApprovedQuoteSowPanel({
  opportunityId,
  onDeliveryJobCreated,
}: {
  opportunityId: string;
  onDeliveryJobCreated?: () => void;
}) {
  const [state, setState] = useState<"loading" | "empty" | "ready" | "error">("loading");
  const [data, setData] = useState<ApprovedQuoteSowData | null>(null);
  const [preparing, setPreparing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    queueMicrotask(() => {
      if (cancelled) return;
      setState("loading");
      getApprovedQuoteSow(opportunityId)
        .then((d) => { if (!cancelled) { setData(d); setState("ready"); } })
        .catch((err: unknown) => {
          if (!cancelled) {
            const msg = err instanceof Error ? err.message : "";
            if (msg.includes("404")) setState("empty");
            else { setError(msg); setState("error"); }
          }
        });
    });
    return () => { cancelled = true; };
  }, [opportunityId]);

  const handlePrepare = async () => {
    setPreparing(true); setError(null);
    try {
      await createApprovedQuoteSowDeliveryJob(opportunityId);
      onDeliveryJobCreated?.();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed");
    } finally { setPreparing(false); }
  };

  return (
    <section className="approved-quote-sow-panel" aria-label="Approved Quote/SOW">
      <div className="panel-heading">
        <div><p className="eyebrow">Approved Quote / SOW</p><h2>已审批报价与 SOW</h2></div>
      </div>
      {state === "loading" && <div className="loading-state small">Loading...</div>}
      {state === "empty" && <div className="empty-state small"><p>暂无已审批 Quote/SOW</p><small>先生成并审批 Quote/SOW Draft 后可在此创建发送任务。</small></div>}
      {state === "error" && <div className="error-state small"><p>加载失败</p><small>{error}</small></div>}
      {state === "ready" && data && (
        <div>
          <dl>
            <div><dt>Quote</dt><dd>{data.quote_markdown.slice(0, 100)}...</dd></div>
            <div><dt>SOW</dt><dd>{data.sow_markdown.slice(0, 100)}...</dd></div>
            <div><dt>批准时间</dt><dd>{data.approved_at ? new Date(data.approved_at).toLocaleString() : "N/A"}</dd></div>
          </dl>
          {error && <p className="error-msg">{error}</p>}
          <button className="button primary" type="button" disabled={preparing} onClick={handlePrepare}>
            {preparing ? "Preparing..." : "Prepare Quote/SOW Send"}
          </button>
        </div>
      )}
    </section>
  );
}
