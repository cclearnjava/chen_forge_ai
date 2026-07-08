"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import AdminShell from "@/components/admin/admin-shell";
import { archiveNotification, getNotifications, getNotificationSummary, markAllNotificationsRead, markNotificationRead, type NotificationOut, type NotificationSummaryOut } from "@/lib/admin-api";

const statusFilters = ["all", "unread", "read", "archived"] as const;
const kindFilters = ["all", "approval_required", "delivery_action_required", "lead_created", "customer_reply_recorded", "delivery_sent", "proposal_ready", "quote_sow_ready"] as const;

export default function NotificationsPage() {
  const [items, setItems] = useState<NotificationOut[]>([]);
  const [total, setTotal] = useState(0);
  const [summary, setSummary] = useState<NotificationSummaryOut | null>(null);
  const [status, setStatus] = useState<string>("all");
  const [kind, setKind] = useState<string>("all");
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    getNotifications({ status: status === "all" ? undefined : status, kind: kind === "all" ? undefined : kind })
      .then((r) => { setItems(r.items); setTotal(r.total); })
      .catch((e) => setError(e.message));
    getNotificationSummary().then(setSummary).catch(() => {});
  };

  useEffect(load, [status, kind]);

  const handleMarkRead = async (id: string) => {
    await markNotificationRead(id);
    load();
  };

  const handleMarkAllRead = async () => {
    await markAllNotificationsRead();
    load();
  };

  const handleArchive = async (id: string) => {
    await archiveNotification(id);
    load();
  };

  return (
    <AdminShell active="notifications" eyebrow="Notification Center" title="通知中心" subtitle={summary ? `${summary.unread_count} unread` : "loading..."}>
      {error && <p className="error-msg">{error}</p>}

      <section className="admin-toolbar">
        <div className="stage-filter">
          {statusFilters.map((s) => <button key={s} className={s === status ? "active" : ""} onClick={() => setStatus(s)}>{s === "all" ? "All" : s}</button>)}
        </div>
        <div className="stage-filter">
          {kindFilters.map((k) => <button key={k} className={k === kind ? "active" : ""} onClick={() => setKind(k)}>{k === "all" ? "All Types" : k}</button>)}
        </div>
        <button className="button ghost" onClick={handleMarkAllRead}>Mark All Read</button>
      </section>

      <div className="notification-list">
        {items.length === 0 ? (
          <div className="empty-state"><p>暂无通知</p></div>
        ) : (
          items.map((n) => (
            <div key={n.id} className={`notification-item ${n.status}`}>
              <div className="notif-main">
                <span className={`severity-${n.severity}`}>{n.severity}</span>
                <strong>{n.title}</strong>
                {n.body && <p>{n.body}</p>}
                <small>{n.kind} · {new Date(n.created_at).toLocaleString()}</small>
              </div>
              <div className="notif-actions">
                {n.target_url && <Link href={n.target_url} className="button ghost small">Open</Link>}
                {n.status === "unread" && <button className="button ghost small" onClick={() => handleMarkRead(n.id)}>Read</button>}
                {n.status !== "archived" && <button className="button ghost small" onClick={() => handleArchive(n.id)}>Archive</button>}
              </div>
            </div>
          ))
        )}
      </div>
      <small className="meta">{total} total</small>
    </AdminShell>
  );
}
