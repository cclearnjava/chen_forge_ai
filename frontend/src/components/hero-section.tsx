import ForgeMap from "./forge-map";
import Link from "next/link";

export default function HeroSection() {
  return (
    <section className="hero">
      <ForgeMap />
      <div className="hero-copy">
        <p className="eyebrow">Human-led AI implementation studio</p>
        <h1>为企业锻造可落地的 AI Agent 系统</h1>
        <p className="hero-text">
          ChenForge AI
          由资深软件工程师主导，帮助企业把重复流程、知识问答、数据查询和运营动作，改造成可监控、可审批、可持续迭代的
          AI Agent 系统。先从一个高频业务场景做可验证 PoC，再逐步进入真实流程。
        </p>
        <div className="hero-actions">
          <Link className="button primary" href="#contact">提交业务问题</Link>
          <Link className="button ghost" href="#method">查看落地方法</Link>
        </div>
      </div>
      <aside className="hero-panel" aria-label="Operating model summary">
        <div>
          <span className="metric">1</span>
          <span className="metric-label">个高频流程切入，不做空泛平台</span>
        </div>
        <div>
          <span className="metric">3</span>
          <span className="metric-label">类边界：权限、安全、人工审批</span>
        </div>
        <div>
          <span className="metric">30</span>
          <span className="metric-label">天内交付可评估 PoC 方案</span>
        </div>
      </aside>
    </section>
  );
}
