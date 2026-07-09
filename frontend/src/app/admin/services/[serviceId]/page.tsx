"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import AdminShell from "@/components/admin/admin-shell";
import ServiceSubResourcePanel from "@/components/admin/service-catalog/service-sub-resource-panel";
import ServicePackageForm, { emptyPackageDraft, type PackageDraft } from "@/components/admin/service-catalog/service-package-form";
import ServiceDeliverableForm, { emptyDeliverableDraft, type DeliverableDraft } from "@/components/admin/service-catalog/service-deliverable-form";
import ServiceRiskRuleForm, { emptyRiskRuleDraft, type RiskRuleDraft } from "@/components/admin/service-catalog/service-risk-rule-form";
import {
  activateService, archiveService, createServiceDeliverable, createServicePackage,
  createServiceRiskRule, deactivateService, deleteServiceDeliverable, deleteServicePackage,
  deleteServiceRiskRule, getNotificationSummary, getService, getServiceDeliverables,
  getServicePackages, getServiceRiskRules, updateService, updateServiceDeliverable,
  updateServicePackage, updateServiceRiskRule,
  type ServiceDeliverableOut, type ServiceOut, type ServicePackageOut, type ServiceRiskRuleOut,
} from "@/lib/admin-api";

const numOrNull = (s: string): number | null => (s.trim() === "" ? null : Number(s));
const intOr0 = (s: string): number => {
  const n = parseInt(s, 10);
  return Number.isNaN(n) ? 0 : n;
};
const numStr = (n: number | null | undefined): string => (n == null ? "" : String(n));
const priceRange = (min: number | null, max: number | null): string => {
  if (min == null && max == null) return "价格未设置";
  const fmt = (v: number) => `¥${(v / 10000).toFixed(1)}w`;
  if (min != null && max != null) return `${fmt(min)} - ${fmt(max)}`;
  return fmt((min ?? max) as number);
};

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
  const [packages, setPackages] = useState<ServicePackageOut[]>([]);
  const [deliverables, setDeliverables] = useState<ServiceDeliverableOut[]>([]);
  const [riskRules, setRiskRules] = useState<ServiceRiskRuleOut[]>([]);

  const load = useCallback(() => {
    setLoading(true);
    Promise.all([getService(id), getServicePackages(id), getServiceDeliverables(id), getServiceRiskRules(id)])
      .then(([s, p, d, r]) => { setSvc(s); setPackages(p.items); setDeliverables(d.items); setRiskRules(r.items); setForm({}); setLoading(false); })
      .catch((e) => { setError(e.message); setLoading(false); });
  }, [id]);

  useEffect(() => {
    queueMicrotask(() => { load(); getNotificationSummary().then((s) => setUnreadCount(s.unread_count)).catch(() => {}); });
  }, [load]);

  const handleSave = async () => {
    setSaving(true);
    try { const updated = await updateService(id, form); setSvc(updated); setEditing(false); }
    catch (e: unknown) { setError(e instanceof Error ? e.message : "更新失败"); }
    finally { setSaving(false); }
  };

  const handleStatus = async (action: "activate" | "deactivate" | "archive") => {
    try {
      const fn = action === "activate" ? activateService : action === "deactivate" ? deactivateService : archiveService;
      const updated = await fn(id); setSvc(updated);
    } catch (e: unknown) { setError(e instanceof Error ? e.message : "状态变更失败"); }
  };

  const statusLabels: Record<string, string> = { active: "已启用", inactive: "已停用", draft: "草稿", archived: "已归档" };
  const sevLabels: Record<string, string> = { low: "低", medium: "中", high: "高", critical: "严重" };

  if (loading) return <AdminShell active="services" eyebrow="加载中..." title="服务详情" subtitle=""><div className="loading-state">Loading...</div></AdminShell>;
  if (error || !svc) return <AdminShell active="services" eyebrow="错误" title="服务详情" subtitle=""><div className="error-state"><p>{error || "未找到"}</p></div></AdminShell>;

  return (
    <AdminShell active="services" unreadCount={unreadCount} eyebrow="服务目录" title={svc.name} subtitle={svc.positioning || ""}>
      <div className="detail-header">
        <Link className="button ghost" href="/admin/services">← 返回服务列表</Link>
        <span className={`stage-badge stage-${svc.status === "active" ? "qualified" : "lead"}`}>{statusLabels[svc.status] || svc.status}</span>
        <div>
          {svc.status !== "active" && <button className="button primary small" onClick={() => handleStatus("activate")}>启用</button>}
          {svc.status === "active" && <button className="button ghost small" onClick={() => handleStatus("deactivate")}>停用</button>}
          {svc.status !== "archived" && <button className="button ghost small" onClick={() => handleStatus("archive")}>归档</button>}
        </div>
      </div>

      {error && <p className="error-msg">{error}</p>}

      <section className="service-summary">
        <span>{priceRange(svc.price_min, svc.price_max)}</span>
        <span>{svc.typical_duration || "周期未设置"}</span>
        <span>{svc.risk_notes ? svc.risk_notes.slice(0, 80) : "无风险说明"}</span>
        <span>更新于 {new Date(svc.updated_at).toLocaleDateString()}</span>
      </section>

      <section className="detail-grid">
        <article>
          <div className="panel-heading"><h2>基本信息</h2>{!editing && <button className="button ghost small" onClick={() => { setForm({ positioning: svc.positioning, target_customer: svc.target_customer, typical_duration: svc.typical_duration, price_min: svc.price_min, price_max: svc.price_max, risk_notes: svc.risk_notes }); setEditing(true); }}>编辑</button>}</div>
          {editing ? (
            <div className="edit-form">
              <label>定位 <textarea value={String(form.positioning || "")} onChange={(e) => setForm({...form, positioning: e.target.value})} rows={2} /></label>
              <label>目标客户 <textarea value={String(form.target_customer || "")} onChange={(e) => setForm({...form, target_customer: e.target.value})} rows={2} /></label>
              <label>周期 <input value={String(form.typical_duration || "")} onChange={(e) => setForm({...form, typical_duration: e.target.value})} /></label>
              <label>最低价 (CNY) <input type="number" value={String(form.price_min || "")} onChange={(e) => setForm({...form, price_min: parseInt(e.target.value) || null})} /></label>
              <label>最高价 (CNY) <input type="number" value={String(form.price_max || "")} onChange={(e) => setForm({...form, price_max: parseInt(e.target.value) || null})} /></label>
              <label>风险说明 <textarea value={String(form.risk_notes || "")} onChange={(e) => setForm({...form, risk_notes: e.target.value})} rows={3} /></label>
              <div><button className="button primary" onClick={handleSave} disabled={saving}>{saving ? "保存中..." : "保存"}</button><button className="button ghost" onClick={() => setEditing(false)}>取消</button></div>
            </div>
          ) : (
            <dl>
              <div><dt>目标客户</dt><dd>{svc.target_customer || "N/A"}</dd></div>
              <div><dt>周期</dt><dd>{svc.typical_duration || "N/A"}</dd></div>
              <div><dt>价格</dt><dd>{priceRange(svc.price_min, svc.price_max)}</dd></div>
              <div><dt>风险说明</dt><dd>{svc.risk_notes || "N/A"}</dd></div>
            </dl>
          )}
        </article>
        <article><div className="panel-heading"><h2>痛点</h2></div>{svc.pain_points_json && Array.isArray(svc.pain_points_json) ? <ul>{(svc.pain_points_json as string[]).map((p, i) => <li key={i}>{p}</li>)}</ul> : <p>N/A</p>}</article>
        <article><div className="panel-heading"><h2>交付成果</h2></div>{svc.outcomes_json && Array.isArray(svc.outcomes_json) ? <ul>{(svc.outcomes_json as string[]).map((o, i) => <li key={i}>{o}</li>)}</ul> : <p>N/A</p>}</article>
      </section>

      <section className="detail-grid">
        <ServiceSubResourcePanel<ServicePackageOut, PackageDraft>
          title="服务包"
          addLabel="新增服务包"
          items={packages}
          emptyDraft={emptyPackageDraft}
          getId={(p) => p.id}
          getLabel={(p) => p.name}
          isValid={(d) => d.name.trim() !== ""}
          toDraft={(p) => ({ name: p.name, description: p.description ?? "", price_min: numStr(p.price_min), price_max: numStr(p.price_max), duration: p.duration ?? "", currency: p.currency || "CNY", sort_order: numStr(p.sort_order) })}
          renderForm={(draft, set) => <ServicePackageForm draft={draft} set={set} />}
          renderItem={(p) => (
            <>
              <strong>{p.name}</strong>
              {p.description && <small>{p.description.slice(0, 60)}</small>}
              <span className="subresource-meta">
                <span>{priceRange(p.price_min, p.price_max)}</span>
                {p.duration && <span>{p.duration}</span>}
                <span>#{p.sort_order}</span>
              </span>
            </>
          )}
          onCreate={async (d) => { await createServicePackage(id, { name: d.name.trim(), description: d.description || null, price_min: numOrNull(d.price_min), price_max: numOrNull(d.price_max), duration: d.duration || null, currency: d.currency || "CNY", sort_order: intOr0(d.sort_order) }); setPackages((await getServicePackages(id)).items); }}
          onUpdate={async (pid, d) => { await updateServicePackage(id, pid, { name: d.name.trim(), description: d.description || null, price_min: numOrNull(d.price_min), price_max: numOrNull(d.price_max), duration: d.duration || null, currency: d.currency || "CNY", sort_order: intOr0(d.sort_order) }); setPackages((await getServicePackages(id)).items); }}
          onDelete={async (pid) => { await deleteServicePackage(id, pid); setPackages((await getServicePackages(id)).items); }}
        />

        <ServiceSubResourcePanel<ServiceDeliverableOut, DeliverableDraft>
          title="交付物"
          addLabel="新增交付物"
          items={deliverables}
          emptyDraft={emptyDeliverableDraft}
          getId={(d) => d.id}
          getLabel={(d) => d.title}
          isValid={(d) => d.title.trim() !== ""}
          toDraft={(d) => ({ title: d.title, description: d.description ?? "", format: d.format ?? "", sort_order: numStr(d.sort_order) })}
          renderForm={(draft, set) => <ServiceDeliverableForm draft={draft} set={set} />}
          renderItem={(d) => (
            <>
              <strong>{d.title}</strong>
              {d.description && <small>{d.description.slice(0, 60)}</small>}
              <span className="subresource-meta">
                {d.format && <span>{d.format}</span>}
                <span>#{d.sort_order}</span>
              </span>
            </>
          )}
          onCreate={async (d) => { await createServiceDeliverable(id, { title: d.title.trim(), description: d.description || null, format: d.format || null, sort_order: intOr0(d.sort_order) }); setDeliverables((await getServiceDeliverables(id)).items); }}
          onUpdate={async (did, d) => { await updateServiceDeliverable(id, did, { title: d.title.trim(), description: d.description || null, format: d.format || null, sort_order: intOr0(d.sort_order) }); setDeliverables((await getServiceDeliverables(id)).items); }}
          onDelete={async (did) => { await deleteServiceDeliverable(id, did); setDeliverables((await getServiceDeliverables(id)).items); }}
        />

        <ServiceSubResourcePanel<ServiceRiskRuleOut, RiskRuleDraft>
          title="风险规则"
          addLabel="新增风险规则"
          items={riskRules}
          emptyDraft={emptyRiskRuleDraft}
          getId={(r) => r.id}
          getLabel={(r) => r.title}
          isValid={(d) => d.title.trim() !== ""}
          toDraft={(r) => ({ title: r.title, description: r.description ?? "", severity: r.severity, disqualifies: r.disqualifies, suggested_response: r.suggested_response ?? "", sort_order: numStr(r.sort_order) })}
          renderForm={(draft, set) => <ServiceRiskRuleForm draft={draft} set={set} />}
          renderItem={(r) => (
            <>
              <strong>{r.title}</strong>
              <span className="subresource-meta">
                <span className={`severity-badge severity-${r.severity}`}>{sevLabels[r.severity] || r.severity}</span>
                {r.disqualifies && <span className="severity-badge severity-critical">不建议承接</span>}
                <span>#{r.sort_order}</span>
              </span>
              {r.suggested_response && <small>{r.suggested_response.slice(0, 60)}</small>}
            </>
          )}
          onCreate={async (d) => { await createServiceRiskRule(id, { title: d.title.trim(), description: d.description || null, severity: d.severity, disqualifies: d.disqualifies, suggested_response: d.suggested_response || null, sort_order: intOr0(d.sort_order) }); setRiskRules((await getServiceRiskRules(id)).items); }}
          onUpdate={async (rid, d) => { await updateServiceRiskRule(id, rid, { title: d.title.trim(), description: d.description || null, severity: d.severity, disqualifies: d.disqualifies, suggested_response: d.suggested_response || null, sort_order: intOr0(d.sort_order) }); setRiskRules((await getServiceRiskRules(id)).items); }}
          onDelete={async (rid) => { await deleteServiceRiskRule(id, rid); setRiskRules((await getServiceRiskRules(id)).items); }}
        />
      </section>
    </AdminShell>
  );
}
