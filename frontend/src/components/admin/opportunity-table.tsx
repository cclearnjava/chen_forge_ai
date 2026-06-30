import Link from "next/link";
import { type OpportunityListItem } from "@/lib/admin-api";
import StageBadge from "./stage-badge";

export default function OpportunityTable({ opportunities }: { opportunities: OpportunityListItem[] }) {
  return (
    <div className="opportunity-table" role="table" aria-label="Opportunity list">
      <div className="opportunity-row table-head" role="row">
        <span>Opportunity</span>
        <span>Stage</span>
        <span>Outcome</span>
        <span>Next step</span>
        <span>Budget</span>
      </div>
      {opportunities.map((o) => (
        <Link
          className={`opportunity-row ${o.next_step ? "" : "needs-step"}`}
          href={`/admin/opportunities/${o.id}`}
          key={o.id}
          role="row"
        >
          <span>
            <strong>{o.title}</strong>
            <small>{o.company_name} · {new Date(o.updated_at).toLocaleDateString()}</small>
          </span>
          <span><StageBadge stage={o.stage} /></span>
          <span>{o.desired_outcome}</span>
          <span>{o.next_step || "未设置下一步"}</span>
          <span>{o.budget_range || "N/A"}</span>
        </Link>
      ))}
    </div>
  );
}
