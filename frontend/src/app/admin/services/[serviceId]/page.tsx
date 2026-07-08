"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import AdminShell from "@/components/admin/admin-shell";
import {
  activateService, archiveService, createServiceDeliverable, createServicePackage,
  createServiceRiskRule, deactivateService, deleteServiceDeliverable, deleteServicePackage,
  deleteServiceRiskRule, getNotificationSummary, getService, getServiceDeliverables,
  getServicePackages, getServiceRiskRules, updateService, updateServiceDeliverable,
  updateServicePackage, updateServiceRiskRule,
  type ServiceDeliverableOut, type ServiceOut, type ServicePackageOut, type ServiceRiskRuleOut,
} from "@/lib/admin-api";

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
  const [newPkg, setNewPkg] = useState(""); const [newDel, setNewDel] = useState(""); const [newRule, setNewRule] = useState("");
  const [editId, setEditId] = useState<string | null>(null); const [editVal, setEditVal] = useState("");
  const [confirmDel, setConfirmDel] = useState<string | null>(null);
  const [subError, setSubError] = useState<string | null>(null);

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

  const addPackage = async () => { if (!newPkg.trim()) return; await createServicePackage(id, { name: newPkg }); setNewPkg(""); const p = await getServicePackages(id); setPackages(p.items); };
  const addDeliverable = async () => { if (!newDel.trim()) return; await createServiceDeliverable(id, { title: newDel }); setNewDel(""); const d = await getServiceDeliverables(id); setDeliverables(d.items); };
  const addRiskRule = async () => { if (!newRule.trim()) return; await createServiceRiskRule(id, { title: newRule }); setNewRule(""); const r = await getServiceRiskRules(id); setRiskRules(r.items); };
  const startEdit = (eid: string, val: string) => { setEditId(eid); setEditVal(val); };
  const saveEdit = async (type: string, eid: string) => {
    if (!editVal.trim()) return;
    try {
      if (type === "pkg") { await updateServicePackage(id, eid, { name: editVal }); setPackages((await getServicePackages(id)).items); }
      else if (type === "del") { await updateServiceDeliverable(id, eid, { title: editVal }); setDeliverables((await getServiceDeliverables(id)).items); }
      else { await updateServiceRiskRule(id, eid, { title: editVal }); setRiskRules((await getServiceRiskRules(id)).items); }
      setEditId(null); setSubError(null);
    } catch (e: unknown) { setSubError(e instanceof Error ? e.message : "编辑失败"); }
  };
  const confirmRemove = async (type: string, rid: string) => {
    try {
      if (type === "pkg") { await deleteServicePackage(id, rid); setPackages(packages.filter(p => p.id !== rid)); }
      else if (type === "del") { await deleteServiceDeliverable(id, rid); setDeliverables(deliverables.filter(d => d.id !== rid)); }
      else { await deleteServiceRiskRule(id, rid); setRiskRules(riskRules.filter(r => r.id !== rid)); }
      setConfirmDel(null); setSubError(null);
    } catch (e: unknown) { setSubError(e instanceof Error ? e.message : "删除失败"); }
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
        <span>{svc.price_min ? `¥${(svc.price_min/10000).toFixed(1)}w - ¥${(svc.price_max! /10000).toFixed(1)}w` : "价格未设置"}</span>
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
              <div><dt>价格</dt><dd>{svc.price_min ? `¥${(svc.price_min/10000).toFixed(1)}w - ¥${(svc.price_max! /10000).toFixed(1)}w` : "N/A"}</dd></div>
              <div><dt>风险说明</dt><dd>{svc.risk_notes || "N/A"}</dd></div>
            </dl>
          )}
        </article>
        <article><div className="panel-heading"><h2>痛点</h2></div>{svc.pain_points_json && Array.isArray(svc.pain_points_json) ? <ul>{(svc.pain_points_json as string[]).map((p, i) => <li key={i}>{p}</li>)}</ul> : <p>N/A</p>}</article>
        <article><div className="panel-heading"><h2>交付成果</h2></div>{svc.outcomes_json && Array.isArray(svc.outcomes_json) ? <ul>{(svc.outcomes_json as string[]).map((o, i) => <li key={i}>{o}</li>)}</ul> : <p>N/A</p>}</article>
      </section>

      <section className="detail-grid">
        <article className="subresource-panel">
          <div className="panel-heading"><h2>服务包</h2></div>
          {subError && <p className="error-msg">{subError}</p>}
          <div className="subresource-form"><input value={newPkg} onChange={(e) => setNewPkg(e.target.value)} placeholder="新增服务包名称" /><button className="button primary small" onClick={addPackage}>新增</button></div>
          <div className="subresource-list">
            {packages.map((p) => (
              <div key={p.id} className="subresource-item">
                {confirmDel === p.id ? (
                  <span className="confirm-actions">确认删除「{p.name}」？<button className="button primary small" onClick={() => confirmRemove("pkg", p.id)}>确认</button><button className="button ghost small" onClick={() => setConfirmDel(null)}>取消</button></span>
                ) : editId === p.id ? (
                  <span className="subresource-actions"><input value={editVal} onChange={(e) => setEditVal(e.target.value)} /><button className="button primary small" onClick={() => saveEdit("pkg", p.id)}>保存</button><button className="button ghost small" onClick={() => setEditId(null)}>取消</button></span>
                ) : (
                  <span className="subresource-actions">
                    <strong>{p.name}</strong>
                    {p.description && <small>{p.description.slice(0, 60)}</small>}
                    {p.price_min && <small>¥{(p.price_min/10000).toFixed(1)}w-¥{(p.price_max||0)/10000}w</small>}
                    <span><button className="button ghost small" onClick={() => startEdit(p.id, p.name)}>编辑</button><button className="button ghost small" onClick={() => setConfirmDel(p.id)}>删除</button></span>
                  </span>
                )}
              </div>
            ))}
          </div>
        </article>

        <article className="subresource-panel">
          <div className="panel-heading"><h2>交付物</h2></div>
          <div className="subresource-form"><input value={newDel} onChange={(e) => setNewDel(e.target.value)} placeholder="新增交付物标题" /><button className="button primary small" onClick={addDeliverable}>新增</button></div>
          <div className="subresource-list">
            {deliverables.map((d) => (
              <div key={d.id} className="subresource-item">
                {confirmDel === d.id ? (
                  <span className="confirm-actions">确认删除「{d.title}」？<button className="button primary small" onClick={() => confirmRemove("del", d.id)}>确认</button><button className="button ghost small" onClick={() => setConfirmDel(null)}>取消</button></span>
                ) : editId === d.id ? (
                  <span className="subresource-actions"><input value={editVal} onChange={(e) => setEditVal(e.target.value)} /><button className="button primary small" onClick={() => saveEdit("del", d.id)}>保存</button><button className="button ghost small" onClick={() => setEditId(null)}>取消</button></span>
                ) : (
                  <span className="subresource-actions">
                    <strong>{d.title}</strong>
                    {d.format && <small>{d.format}</small>}
                    <span><button className="button ghost small" onClick={() => startEdit(d.id, d.title)}>编辑</button><button className="button ghost small" onClick={() => setConfirmDel(d.id)}>删除</button></span>
                  </span>
                )}
              </div>
            ))}
          </div>
        </article>

        <article className="subresource-panel">
          <div className="panel-heading"><h2>风险规则</h2></div>
          <div className="subresource-form"><input value={newRule} onChange={(e) => setNewRule(e.target.value)} placeholder="新增风险规则标题" /><button className="button primary small" onClick={addRiskRule}>新增</button></div>
          <div className="subresource-list">
            {riskRules.map((r) => (
              <div key={r.id} className="subresource-item">
                {confirmDel === r.id ? (
                  <span className="confirm-actions">确认删除「{r.title}」？<button className="button primary small" onClick={() => confirmRemove("rule", r.id)}>确认</button><button className="button ghost small" onClick={() => setConfirmDel(null)}>取消</button></span>
                ) : editId === r.id ? (
                  <span className="subresource-actions"><input value={editVal} onChange={(e) => setEditVal(e.target.value)} /><button className="button primary small" onClick={() => saveEdit("rule", r.id)}>保存</button><button className="button ghost small" onClick={() => setEditId(null)}>取消</button></span>
                ) : (
                  <span className="subresource-actions">
                    <strong>{r.title}</strong>
                    <span className={`severity-badge severity-${r.severity}`}>{sevLabels[r.severity] || r.severity}</span>
                    {r.disqualifies && <span className="severity-badge severity-critical">不建议承接</span>}
                    <span><button className="button ghost small" onClick={() => startEdit(r.id, r.title)}>编辑</button><button className="button ghost small" onClick={() => setConfirmDel(r.id)}>删除</button></span>
                  </span>
                )}
              </div>
            ))}
          </div>
        </article>
      </section>
    </AdminShell>
  );
}
