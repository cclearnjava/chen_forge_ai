import Link from "next/link";
import AdminShell from "@/components/admin/admin-shell";
import ConversationThread from "@/components/admin/conversation-thread";
import OpportunityInspector from "@/components/admin/opportunity-inspector";
import StageBadge from "@/components/admin/stage-badge";
import { getOpportunity, opportunities } from "@/lib/admin-mock";

export function generateStaticParams() {
  return opportunities.map((opportunity) => ({
    opportunityId: opportunity.id,
  }));
}

export default async function OpportunityDetailPage({
  params,
}: {
  params: Promise<{ opportunityId: string }>;
}) {
  const { opportunityId } = await params;
  const opportunity = getOpportunity(opportunityId);

  return (
    <AdminShell
      eyebrow="Company Cockpit / Opportunity"
      title={opportunity.title}
      subtitle={`${opportunity.companyName} · ${opportunity.desiredOutcome}`}
    >
      <div className="detail-header">
        <Link className="button ghost" href="/admin/opportunities">← 返回机会列表</Link>
        <StageBadge stage={opportunity.stage} />
        <span>{opportunity.updatedAt}</span>
      </div>

      <section className="opportunity-summary">
        <article>
          <span>Next Step</span>
          <strong>{opportunity.nextStep || "未设置下一步"}</strong>
        </article>
        <article>
          <span>Estimated Value</span>
          <strong>{opportunity.estimatedValue}</strong>
        </article>
        <article>
          <span>Probability</span>
          <strong>{opportunity.probability}%</strong>
        </article>
      </section>

      <section className="opportunity-detail-grid">
        <ConversationThread messages={opportunity.messages} />
        <OpportunityInspector opportunity={opportunity} />
      </section>
    </AdminShell>
  );
}
