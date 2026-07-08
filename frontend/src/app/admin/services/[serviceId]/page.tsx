"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import AdminShell from "@/components/admin/admin-shell";
import { getNotificationSummary, getService, updateService, activateService, deactivateService, archiveService, type ServiceOut } from "@/lib/admin-api";

export default function ServiceDetailPage() {
  const { serviceId } = useParams();
  const id = serviceId as string;
  const [svc, setSvc] = useState<ServiceOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState<Record<string, unknown>>({});
  const [saving, setSaving] = useState(false);
  const [unreadCount, setUnreadCount] = useState<number | undefined>();

  const load = useCallback(() => {
    setLoading(true);
    getService(id).then((s) => { setSvc(s); setForm({}); setLoading(false); })
      .catch((e) => { setError(e.message); setLoading(false); });
  }, [id]);

  useEffect(() => {
    queueMicrotask(() => { load(); getNotificationSummary().then((s) => setUnreadCount(s.unread_count)).catch(() => {}); });
  }, [load]);

  const handleSave = async () => {
    setSaving(true);
    try { const updated = await updateService(id, form); setSvc(updated); setEditing(false); }
    catch (e: unknown) { setError(e instanceof Error ? e.message : "Update failed"); }
    finally { setSaving(false); }
  };

  const handleStatus = async (action: "activate" | "deactivate" | "archive") => {
    try {
      const fn = action === "activate" ? activateService : action === "deactivate" ? deactivateService : archiveService;
      const updated = await fn(id); setSvc(updated);
    } catch (e: unknown) { setError(e instanceof Error ? e.message : "Status change failed"); }
  };

  if (loading) return <AdminShell active="services" eyebrow="Loading..." title="Service" subtitle=""><div className="loading-state">Loading...</div></AdminShell>;
  if (error || !svc) return <AdminShell active="services" eyebrow="Error" title="Service" subtitle=""><div className="error-state"><p>{error || "Not found"}</p></div></AdminShell>;

  return (
    <AdminShell active="services" unreadCount={unreadCount} eyebrow="Service Catalog" title={svc.name} subtitle={svc.positioning || ""}>
      <div className="detail-header">
        <Link className="button ghost" href="/admin/services">← 返回服务列表</Link>
        <span className={`stage-badge stage-${svc.status === "active" ? "qualified" : "lead"}`}>{svc.status}</span>
        <div>
          {svc.status !== "active" && <button className="button primary small" onClick={() => handleStatus("activate")}>Activate</button>}
          {svc.status === "active" && <button className="button ghost small" onClick={() => handleStatus("deactivate")}>Deactivate</button>}
          {svc.status !== "archived" && <button className="button ghost small" onClick={() => handleStatus("archive")}>Archive</button>}
        </div>
      </div>

      {error && <p className="error-msg">{error}</p>}

      <section className="detail-grid">
        <article>
          <div className="panel-heading"><h2>基本信息</h2>{!editing && <button className="button ghost small" onClick={() => { setForm({ positioning: svc.positioning, target_customer: svc.target_customer, typical_duration: svc.typical_duration, price_min: svc.price_min, price_max: svc.price_max, risk_notes: svc.risk_notes }); setEditing(true); }}>Edit</button>}</div>
          {editing ? (
            <div className="edit-form">
              <label>Positioning <textarea value={String(form.positioning || "")} onChange={(e) => setForm({...form, positioning: e.target.value})} rows={2} /></label>
              <label>Target Customer <textarea value={String(form.target_customer || "")} onChange={(e) => setForm({...form, target_customer: e.target.value})} rows={2} /></label>
              <label>Duration <input value={String(form.typical_duration || "")} onChange={(e) => setForm({...form, typical_duration: e.target.value})} /></label>
              <label>Price Min (CNY) <input type="number" value={String(form.price_min || "")} onChange={(e) => setForm({...form, price_min: parseInt(e.target.value) || null})} /></label>
              <label>Price Max (CNY) <input type="number" value={String(form.price_max || "")} onChange={(e) => setForm({...form, price_max: parseInt(e.target.value) || null})} /></label>
              <label>Risk Notes <textarea value={String(form.risk_notes || "")} onChange={(e) => setForm({...form, risk_notes: e.target.value})} rows={3} /></label>
              <div>
                <button className="button primary" onClick={handleSave} disabled={saving}>{saving ? "Saving..." : "Save"}</button>
                <button className="button ghost" onClick={() => setEditing(false)}>Cancel</button>
              </div>
            </div>
          ) : (
            <dl>
              <div><dt>Target Customer</dt><dd>{svc.target_customer || "N/A"}</dd></div>
              <div><dt>Duration</dt><dd>{svc.typical_duration || "N/A"}</dd></div>
              <div><dt>Price</dt><dd>{svc.price_min ? `¥${(svc.price_min/10000).toFixed(1)}w - ¥${(svc.price_max! /10000).toFixed(1)}w` : "N/A"}</dd></div>
              <div><dt>Risk Notes</dt><dd>{svc.risk_notes || "N/A"}</dd></div>
            </dl>
          )}
        </article>

        <article>
          <div className="panel-heading"><h2>Pain Points</h2></div>
          {svc.pain_points_json && Array.isArray(svc.pain_points_json) ? <ul>{(svc.pain_points_json as string[]).map((p: string, i: number) => <li key={i}>{p}</li>)}</ul> : <p>N/A</p>}
        </article>
        <article>
          <div className="panel-heading"><h2>Outcomes</h2></div>
          {svc.outcomes_json && Array.isArray(svc.outcomes_json) ? <ul>{(svc.outcomes_json as string[]).map((o: string, i: number) => <li key={i}>{o}</li>)}</ul> : <p>N/A</p>}
        </article>
      </section>
    </AdminShell>
  );
}
