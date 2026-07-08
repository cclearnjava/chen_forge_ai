import Link from "next/link";
import type { ReactNode } from "react";

const navItems = [
  { href: "/admin", label: "Cockpit", mark: "⌂", key: "cockpit" },
  { href: "/admin/opportunities", label: "Opportunities", mark: "◎", key: "opportunities" },
  { href: "/admin/customers", label: "Customers", mark: "◇", key: "customers" },
  { href: "/admin/leads", label: "Leads", mark: "□", key: "leads" },
  { href: "/admin/decisions", label: "Decisions", mark: "!", key: "decisions" },
  { href: "/admin/notifications", label: "Notifications", mark: "ⓘ", key: "notifications" },
];

export default function AdminShell({
  active,
  eyebrow,
  title,
  subtitle,
  children,
  workspaceName,
  unreadCount,
}: {
  active: string;
  eyebrow: string;
  title: string;
  subtitle: string;
  children: ReactNode;
  workspaceName?: string;
  unreadCount?: number;
}) {
  return (
    <main className="admin-shell">
      <aside className="admin-sidebar" aria-label="Admin navigation">
        <Link className="admin-brand" href="/">
          <span className="brand-mark">CF</span>
          <span>
            <strong>ChenForge</strong>
            <small>Company OS</small>
          </span>
        </Link>
        <nav>
          {navItems.map((item) => (
            <Link
              href={item.href}
              key={item.href}
              className={item.key === active ? "active" : ""}
            >
              <span aria-hidden="true">{item.mark}</span>
              {item.label}
            </Link>
          ))}
        </nav>
      </aside>
      <section className="admin-main">
        <header className="admin-topbar">
          <div>
            <p className="eyebrow">{eyebrow}</p>
            <h1>{title}</h1>
            <p>{subtitle}</p>
          </div>
          <div className="admin-topbar-status">
            <span>{workspaceName || "Admin"}</span>
            <strong>{unreadCount != null ? (unreadCount > 0 ? `${unreadCount} 待处理` : "无待处理通知") : "通知状态不可用"}</strong>
          </div>
        </header>
        {children}
      </section>
    </main>
  );
}
