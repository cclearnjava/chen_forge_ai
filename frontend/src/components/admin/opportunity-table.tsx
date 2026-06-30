import Link from "next/link";
import { opportunities } from "@/lib/admin-mock";
import StageBadge from "./stage-badge";

export default function OpportunityTable() {
  return (
    <div className="opportunity-table" role="table" aria-label="Opportunity list">
      <div className="opportunity-row table-head" role="row">
        <span>Opportunity</span>
        <span>Stage</span>
        <span>Outcome</span>
        <span>Next step</span>
        <span>Budget</span>
      </div>
      {opportunities.map((opportunity) => (
        <Link
          className={`opportunity-row ${opportunity.nextStep ? "" : "needs-step"}`}
          href={`/admin/opportunities/${opportunity.id}`}
          key={opportunity.id}
          role="row"
        >
          <span>
            <strong>{opportunity.title}</strong>
            <small>{opportunity.companyName} · {opportunity.updatedAt}</small>
          </span>
          <span><StageBadge stage={opportunity.stage} /></span>
          <span>{opportunity.desiredOutcome}</span>
          <span>{opportunity.nextStep || "未设置下一步"}</span>
          <span>{opportunity.budgetRange}</span>
        </Link>
      ))}
    </div>
  );
}
