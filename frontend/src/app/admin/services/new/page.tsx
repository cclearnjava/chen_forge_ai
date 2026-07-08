"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import AdminShell from "@/components/admin/admin-shell";
import { createService, getNotificationSummary } from "@/lib/admin-api";

export default function NewServicePage() {
  const router = useRouter();
  const [saving, setSaving] = useState(false);
  const [unreadCount, setUnreadCount] = useState<number | undefined>();
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({ name: "", slug: "", positioning: "", target_customer: "", typical_duration: "", price_min: "", price_max: "", risk_notes: "" });

  useEffect(() => { getNotificationSummary().then((s) => setUnreadCount(s.unread_count)).catch(() => {}); }, []);

  const handleCreate = async () => {
    if (!form.name || !form.slug) { setError("Name and slug are required"); return; }
    setSaving(true); setError(null);
    try {
      const svc = await createService({
        name: form.name, slug: form.slug, positioning: form.positioning, target_customer: form.target_customer,
        typical_duration: form.typical_duration, price_min: form.price_min ? parseInt(form.price_min) : null,
        price_max: form.price_max ? parseInt(form.price_max) : null, risk_notes: form.risk_notes,
      });
      router.push(`/admin/services/${svc.id}`);
    } catch (e: unknown) { setError(e instanceof Error ? e.message : "Create failed"); }
    finally { setSaving(false); }
  };

  return (
    <AdminShell active="services" eyebrow="Service Catalog" title="New Service" subtitle="创建新服务">
      <Link className="button ghost" href="/admin/services">← 返回服务列表</Link>
      {error && <p className="error-msg">{error}</p>}
      <div className="edit-form">
        <label>Name <input value={form.name} onChange={(e) => setForm({...form, name: e.target.value})} placeholder="AI Agent 落地咨询" /></label>
        <label>Slug <input value={form.slug} onChange={(e) => setForm({...form, slug: e.target.value})} placeholder="ai-agent-consulting" /></label>
        <label>Positioning <textarea value={form.positioning} onChange={(e) => setForm({...form, positioning: e.target.value})} rows={2} /></label>
        <label>Target Customer <textarea value={form.target_customer} onChange={(e) => setForm({...form, target_customer: e.target.value})} rows={2} /></label>
        <label>Duration <input value={form.typical_duration} onChange={(e) => setForm({...form, typical_duration: e.target.value})} placeholder="2-4 周" /></label>
        <label>Price Min (CNY) <input type="number" value={form.price_min} onChange={(e) => setForm({...form, price_min: e.target.value})} /></label>
        <label>Price Max (CNY) <input type="number" value={form.price_max} onChange={(e) => setForm({...form, price_max: e.target.value})} /></label>
        <label>Risk Notes <textarea value={form.risk_notes} onChange={(e) => setForm({...form, risk_notes: e.target.value})} rows={3} /></label>
        <button className="button primary" onClick={handleCreate} disabled={saving}>{saving ? "Creating..." : "Create Service"}</button>
      </div>
    </AdminShell>
  );
}
