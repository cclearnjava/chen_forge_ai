import Link from "next/link";

export default function SiteHeader() {
  return (
    <header className="site-header">
      <Link className="brand" href="/" aria-label="ChenForge AI home">
        <span className="brand-mark">CF</span>
        <span>
          <strong>ChenForge AI</strong>
          <small>AI agent systems for business operations</small>
        </span>
      </Link>
      <nav aria-label="Primary">
        <a href="#pain">落地难点</a>
        <a href="#services">服务</a>
        <a href="#method">方法论</a>
        <a href="#contact">诊断入口</a>
      </nav>
    </header>
  );
}
