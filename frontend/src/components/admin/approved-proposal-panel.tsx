"use client";

import { useEffect, useState } from "react";
import { getApprovedProposal, getApprovedProposalPdfUrl, type ApprovedProposalData } from "@/lib/admin-api";

export default function ApprovedProposalPanel({ opportunityId }: { opportunityId: string }) {
  const [state, setState] = useState<"loading" | "empty" | "ready" | "error">("loading");
  const [data, setData] = useState<ApprovedProposalData | null>(null);
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    queueMicrotask(() => {
      if (cancelled) return;
      setState("loading");
      getApprovedProposal(opportunityId)
        .then((d) => { if (!cancelled) { setData(d); setState("ready"); } })
        .catch((err: unknown) => {
          if (!cancelled) {
            const msg = err instanceof Error ? err.message : "";
            if (msg.includes("404")) { setState("empty"); }
            else { setError(msg); setState("error"); }
          }
        });
    });
    return () => { cancelled = true; };
  }, [opportunityId]);

  const handleDownload = () => {
    setDownloading(true);
    const url = getApprovedProposalPdfUrl(opportunityId);
    const a = document.createElement("a");
    a.href = url;
    a.download = `chenforge-proposal-${opportunityId.slice(0, 8)}.pdf`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(() => setDownloading(false), 1500);
  };

  return (
    <section className="approved-proposal-panel" aria-label="Approved proposal">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Approved Proposal</p>
          <h2>已批准方案</h2>
        </div>
      </div>

      {state === "loading" && <div className="loading-state small">Loading...</div>}

      {state === "empty" && (
        <div className="empty-state small">
          <p>暂无已批准方案</p>
          <small>先生成 Proposal Draft 并审批通过后，可在此导出 PDF。</small>
        </div>
      )}

      {state === "error" && (
        <div className="error-state small">
          <p>加载失败</p>
          <small>{error}</small>
        </div>
      )}

      {state === "ready" && data && (
        <div className="approved-proposal-content">
          <dl>
            <div><dt>客户</dt><dd>{data.customer_name}</dd></div>
            <div><dt>商机</dt><dd>{data.opportunity_title}</dd></div>
            <div><dt>批准时间</dt><dd>{data.approved_at ? new Date(data.approved_at).toLocaleString() : "N/A"}</dd></div>
          </dl>
          <details>
            <summary>方案预览</summary>
            <div className="markdown-body" style={{ whiteSpace: "pre-wrap", maxHeight: 200, overflowY: "auto" }}>
              {data.markdown.slice(0, 500)}{data.markdown.length > 500 ? "..." : ""}
            </div>
          </details>
          <button
            className="button primary"
            type="button"
            disabled={downloading}
            onClick={handleDownload}
          >
            {downloading ? "Downloading..." : "Download PDF"}
          </button>
        </div>
      )}
    </section>
  );
}
