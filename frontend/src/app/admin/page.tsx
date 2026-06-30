import Link from "next/link";
import AdminShell from "@/components/admin/admin-shell";
import { opportunities } from "@/lib/admin-mock";

export default function AdminPage() {
  const needsFollowUp = opportunities.filter((item) => !item.nextStep || item.stage === "qualified");

  return (
    <AdminShell
      active="cockpit"
      eyebrow="Company Cockpit"
      title="今日经营台"
      subtitle="静态 UI mock：聚焦客户机会、待跟进动作和最近对话。"
    >
      <section className="admin-metrics" aria-label="Cockpit metrics">
        <article>
          <span>Customers</span>
          <strong>4</strong>
          <small>mock records</small>
        </article>
        <article>
          <span>Opportunities</span>
          <strong>{opportunities.length}</strong>
          <small>pipeline items</small>
        </article>
        <article className="attention">
          <span>Follow-up</span>
          <strong>{needsFollowUp.length}</strong>
          <small>owner actions</small>
        </article>
        <article>
          <span>Messages</span>
          <strong>{opportunities.reduce((sum, item) => sum + item.messages.length, 0)}</strong>
          <small>conversation notes</small>
        </article>
      </section>

      <section className="cockpit-grid">
        <article className="focus-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Focus</p>
              <h2>今天先推进这些机会</h2>
            </div>
            <Link className="button ghost" href="/admin/opportunities">查看全部</Link>
          </div>
          {needsFollowUp.map((item) => (
            <Link className="focus-item" href={`/admin/opportunities/${item.id}`} key={item.id}>
              <strong>{item.companyName}</strong>
              <span>{item.title}</span>
              <small>{item.nextStep || "未设置下一步动作"}</small>
            </Link>
          ))}
        </article>

        <article className="focus-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Recent</p>
              <h2>最近客户消息</h2>
            </div>
          </div>
          {opportunities.slice(0, 3).map((item) => (
            <Link className="focus-item" href={`/admin/opportunities/${item.id}`} key={item.id}>
              <strong>{item.companyName}</strong>
              <span>{item.messages[0]?.body}</span>
              <small>{item.messages[0]?.createdAt}</small>
            </Link>
          ))}
        </article>
      </section>
    </AdminShell>
  );
}
