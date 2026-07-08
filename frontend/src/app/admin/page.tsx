"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import AdminShell from "@/components/admin/admin-shell";
import { getCurrentWorkspace, getNotificationSummary, getOpportunities, type OpportunityListItem } from "@/lib/admin-api";

export default function AdminPage() {
  const [items, setItems] = useState<OpportunityListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [wsName, setWsName] = useState<string | undefined>();
  const [unreadCount, setUnreadCount] = useState<number | undefined>();

  useEffect(() => {
    getCurrentWorkspace().then((ws) => setWsName(ws.name)).catch(() => {});
    getNotificationSummary().then((s) => setUnreadCount(s.unread_count)).catch(() => {});
    getOpportunities()
      .then((res) => { setItems(res.items); setTotal(res.total); })
      .catch((err) => setError(err.message));
  }, []);

  const needsFollowUp = items.filter((o) => !o.next_step || o.stage === "qualified");
  const qualifiedCount = items.filter((o) => o.stage === "qualified").length;
  const recentItems = [...items].sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()).slice(0, 5);

  return (
    <AdminShell
      active="cockpit"
      workspaceName={wsName}
      unreadCount={unreadCount}
      eyebrow="Company Cockpit"
      title="今日经营台"
      subtitle={error ? `API error: ${error}` : `${total} opportunities from API`}
    >
      <section className="admin-metrics" aria-label="Cockpit metrics">
        <article><span>Customers</span><strong>{total}</strong><small>with opportunities</small></article>
        <article><span>Opportunities</span><strong>{total}</strong><small>total pipeline</small></article>
        <article className="attention">
          <span>Follow-up</span><strong>{needsFollowUp.length}</strong><small>owner actions</small>
        </article>
        <article><span>Qualified</span><strong>{qualifiedCount}</strong><small>ready for agent</small></article>
      </section>

      <section className="cockpit-grid">
        <article className="focus-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Priority Queue</p>
              <h2>待跟进机会</h2>
            </div>
            <Link className="button ghost" href="/admin/opportunities">查看全部</Link>
          </div>
          {needsFollowUp.length === 0 ? (
            <div className="empty-state small"><p>暂无待跟进机会</p></div>
          ) : (
            needsFollowUp.slice(0, 5).map((o) => (
              <Link className="focus-item" href={`/admin/opportunities/${o.id}`} key={o.id}>
                <strong>{o.company_name}</strong>
                <span>{o.title}</span>
                <small>{o.next_step || "未设置下一步动作"}</small>
              </Link>
            ))
          )}
        </article>

        <article className="focus-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Recent</p>
              <h2>最近更新的机会</h2>
            </div>
          </div>
          {recentItems.length === 0 ? (
            <div className="empty-state small"><p>暂无数据</p></div>
          ) : (
            recentItems.map((o) => (
              <Link className="focus-item" href={`/admin/opportunities/${o.id}`} key={o.id}>
                <strong>{o.company_name}</strong>
                <span>{o.title} · <StageLabel stage={o.stage} /></span>
                <small>updated: {new Date(o.updated_at).toLocaleDateString()}</small>
              </Link>
            ))
          )}
        </article>
      </section>
    </AdminShell>
  );
}

function StageLabel({ stage }: { stage: string }) {
  const labels: Record<string, string> = {
    lead: "Lead", qualified: "Qualified", proposal: "Proposal",
    negotiation: "Negotiation", won: "Won", lost: "Lost", archived: "Archived",
  };
  return <span className={`stage-badge stage-${stage}`}>{labels[stage] || stage}</span>;
}
