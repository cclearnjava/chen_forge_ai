"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import AdminShell from "@/components/admin/admin-shell";
import { getServices, seedDefaultServices, type ServiceOut } from "@/lib/admin-api";

export default function ServicesPage() {
  const [items, setItems] = useState<ServiceOut[]>([]);
  const [total, setTotal] = useState(0);
  const [status, setStatus] = useState<string>("all");
  const [search, setSearch] = useState("");
  const [seeding, setSeeding] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [unreadCount] = useState<number | undefined>();

  const load = () => {
    getServices({ status: status === "all" ? undefined : status, q: search || undefined })
      .then((r) => { setItems(r.items); setTotal(r.total); })
      .catch((e) => setError(e.message));
  };

  useEffect(load, [status, search]);

  const handleSeed = async () => {
    setSeeding(true);
    try { await seedDefaultServices(); load(); }
    catch (e: unknown) { setError(e instanceof Error ? e.message : "Seed failed"); }
    finally { setSeeding(false); }
  };

  const statusFilters = ["all", "active", "inactive", "draft", "archived"];

  return (
    <AdminShell active="services" unreadCount={unreadCount} eyebrow="Service Catalog" title="服务目录" subtitle={`${total} services`}>
      {error && <p className="error-msg">{error}</p>}
      <section className="admin-toolbar">
        <label>Search <input placeholder="搜索服务" value={search} onChange={(e) => setSearch(e.target.value)} /></label>
        <div className="stage-filter">
          {statusFilters.map((s) => <button key={s} className={s === status ? "active" : ""} onClick={() => setStatus(s)}>{s === "all" ? "All" : s}</button>)}
        </div>
        <button className="button primary" onClick={handleSeed} disabled={seeding}>{seeding ? "Seeding..." : "Seed Defaults"}</button>
      </section>
      <div className="opportunity-table">
        <div className="opportunity-row table-head">
          <span>Service</span><span>Status</span><span>Price</span><span>Duration</span>
        </div>
        {items.map((s) => (
          <Link className="opportunity-row" href={`/admin/services/${s.id}`} key={s.id}>
            <span><strong>{s.name}</strong><small>{s.positioning?.slice(0, 80)}</small></span>
            <span><span className={`stage-badge stage-${s.status === "active" ? "qualified" : "lead"}`}>{s.status}</span></span>
            <span>{s.price_min ? `¥${(s.price_min/10000).toFixed(1)}-${(s.price_max! /10000).toFixed(1)}w` : "N/A"}</span>
            <span>{s.typical_duration || "N/A"}</span>
          </Link>
        ))}
      </div>
    </AdminShell>
  );
}
