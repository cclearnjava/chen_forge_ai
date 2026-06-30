"use client";

import type { AuditLogOut } from "@/lib/admin-api";

export default function AuditTrail({ logs }: { logs: AuditLogOut[] }) {
  if (logs.length === 0) {
    return (
      <section className="audit-trail" aria-label="Audit trail">
        <div className="panel-heading">
          <h2>Audit Trail</h2>
        </div>
        <div className="empty-state small">
          <p>暂无审计记录</p>
        </div>
      </section>
    );
  }

  return (
    <section className="audit-trail" aria-label="Audit trail">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Accountability</p>
          <h2>Audit Trail</h2>
        </div>
        <span>{logs.length} records</span>
      </div>
      <div className="timeline">
        {logs.map((log) => (
          <div className="timeline-item" key={log.id}>
            <div className="timeline-dot" />
            <div>
              <strong>{log.action}</strong>
              <small>by {log.actor}</small>
              {log.details_json && (
                <small className="mono">
                  {Object.entries(log.details_json)
                    .slice(0, 3)
                    .map(([k, v]) => `${k}: ${typeof v === "string" ? v.slice(0, 12) : JSON.stringify(v)}`)
                    .join(" · ")}
                </small>
              )}
              <small>{new Date(log.created_at).toLocaleString()}</small>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
