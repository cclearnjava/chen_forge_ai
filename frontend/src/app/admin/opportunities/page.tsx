"use client";

import { useEffect, useState } from "react";
import AdminShell from "@/components/admin/admin-shell";
import OpportunityTable from "@/components/admin/opportunity-table";
import { getOpportunities, stageLabels, type Stage, type OpportunityListItem } from "@/lib/admin-api";

const stages: Array<"all" | Stage> = [
  "all", "lead", "qualified", "proposal", "negotiation", "won", "lost", "archived",
];

export default function OpportunitiesPage() {
  const [items, setItems] = useState<OpportunityListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [stageFilter, setStageFilter] = useState<string>("all");
  const [search, setSearch] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getOpportunities({ stage: stageFilter === "all" ? undefined : stageFilter, q: search || undefined })
      .then((res) => {
        if (!cancelled) {
          setItems(res.items);
          setTotal(res.total);
        }
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      });
    return () => { cancelled = true; };
  }, [stageFilter, search]);

  const qualified = items.filter((i) => i.stage === "qualified").length;
  const proposal = items.filter((i) => i.stage === "proposal").length;
  const missingNextStep = items.filter((i) => !i.next_step).length;

  return (
    <AdminShell
      active="opportunities"
      eyebrow="Company Cockpit / Pipeline"
      title="Opportunities"
      subtitle={error ? `API error: ${error}` : `${total} opportunities from API`}
    >
      <section className="admin-metrics" aria-label="Pipeline metrics">
        <article><span>Total</span><strong>{total}</strong><small>from API</small></article>
        <article><span>Qualified</span><strong>{qualified}</strong><small>ready for discovery</small></article>
        <article><span>Proposal</span><strong>{proposal}</strong><small>needs review</small></article>
        <article className={missingNextStep ? "attention" : ""}><span>No next step</span><strong>{missingNextStep}</strong><small>requires owner action</small></article>
      </section>

      <section className="admin-toolbar" aria-label="Opportunity controls">
        <label>
          Search
          <input placeholder="搜索公司、机会、业务问题" value={search} onChange={(e) => setSearch(e.target.value)} />
        </label>
        <div className="stage-filter" aria-label="Stage filter">
          {stages.map((s) => (
            <button className={s === stageFilter ? "active" : ""} key={s} type="button" onClick={() => setStageFilter(s)}>
              {s === "all" ? "All" : stageLabels[s]}
            </button>
          ))}
        </div>
      </section>

      <OpportunityTable opportunities={items} />
    </AdminShell>
  );
}
