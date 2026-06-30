import AdminShell from "@/components/admin/admin-shell";
import OpportunityTable from "@/components/admin/opportunity-table";
import { opportunities, stageLabels, type Stage } from "@/lib/admin-mock";

const stages: Array<"all" | Stage> = [
  "all",
  "lead",
  "qualified",
  "proposal",
  "negotiation",
  "won",
  "lost",
  "archived",
];

export default function OpportunitiesPage() {
  const qualified = opportunities.filter((item) => item.stage === "qualified").length;
  const proposal = opportunities.filter((item) => item.stage === "proposal").length;
  const missingNextStep = opportunities.filter((item) => !item.nextStep).length;

  return (
    <AdminShell
      active="opportunities"
      eyebrow="Company Cockpit / Pipeline"
      title="Opportunities"
      subtitle="静态 UI mock：查看客户机会、阶段、下一步动作和预算范围。"
    >
      <section className="admin-metrics" aria-label="Pipeline metrics">
        <article>
          <span>Total</span>
          <strong>{opportunities.length}</strong>
          <small>active records</small>
        </article>
        <article>
          <span>Qualified</span>
          <strong>{qualified}</strong>
          <small>ready for discovery</small>
        </article>
        <article>
          <span>Proposal</span>
          <strong>{proposal}</strong>
          <small>needs review</small>
        </article>
        <article className={missingNextStep ? "attention" : ""}>
          <span>No next step</span>
          <strong>{missingNextStep}</strong>
          <small>requires owner action</small>
        </article>
      </section>

      <section className="admin-toolbar" aria-label="Opportunity controls">
        <label>
          Search
          <input placeholder="搜索公司、机会、业务问题" defaultValue="AI" />
        </label>
        <div className="stage-filter" aria-label="Stage filter">
          {stages.map((stage) => (
            <button className={stage === "all" ? "active" : ""} key={stage} type="button">
              {stage === "all" ? "All" : stageLabels[stage]}
            </button>
          ))}
        </div>
      </section>

      <OpportunityTable />
    </AdminShell>
  );
}
