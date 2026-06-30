import type { Opportunity } from "@/lib/admin-mock";
import StageBadge from "./stage-badge";

export default function OpportunityInspector({ opportunity }: { opportunity: Opportunity }) {
  return (
    <aside className="opportunity-inspector" aria-label="Opportunity inspector">
      <section>
        <div className="inspector-title">
          <span>Customer</span>
          <strong>{opportunity.companyName}</strong>
        </div>
        <dl>
          <div><dt>Owner email</dt><dd>{opportunity.ownerEmail}</dd></div>
          <div><dt>Industry</dt><dd>{opportunity.industry}</dd></div>
          <div><dt>Company size</dt><dd>{opportunity.companySize}</dd></div>
        </dl>
      </section>

      <section>
        <div className="inspector-title">
          <span>Contact</span>
          <strong>{opportunity.contactName}</strong>
        </div>
        <dl>
          <div><dt>Method</dt><dd>{opportunity.contactMethod}</dd></div>
          <div><dt>Updated</dt><dd>{opportunity.updatedAt}</dd></div>
        </dl>
      </section>

      <section>
        <div className="inspector-title">
          <span>Opportunity</span>
          <StageBadge stage={opportunity.stage} />
        </div>
        <dl>
          <div><dt>Value</dt><dd>{opportunity.estimatedValue}</dd></div>
          <div><dt>Probability</dt><dd>{opportunity.probability}%</dd></div>
          <div><dt>Budget</dt><dd>{opportunity.budgetRange}</dd></div>
        </dl>
      </section>

      <section>
        <div className="inspector-title">
          <span>Next step</span>
          <strong>{opportunity.nextStep || "未设置"}</strong>
        </div>
        <p>{opportunity.problemSummary}</p>
      </section>
    </aside>
  );
}
