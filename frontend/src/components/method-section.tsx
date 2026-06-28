const STEPS = [
  {
    label: "Diagnose",
    title: "诊断业务流程",
    desc: "确认高频、低风险、价值清晰的切入点，避免从宏大概念开始。",
  },
  {
    label: "Design",
    title: "设计 Agent 边界",
    desc: "定义输入输出、工具权限、审批节点、异常兜底和效果指标。",
  },
  {
    label: "Forge",
    title: "构建可用 PoC",
    desc: "用真实样本、真实流程和可审计日志，交付能被业务试用的版本。",
  },
  {
    label: "Verify",
    title: "验证业务价值",
    desc: "用准确率、节省时间、使用率、成本和质量指标判断是否继续投入。",
  },
  {
    label: "Operate",
    title: "进入持续运营",
    desc: "沉淀知识、反馈、监控和迭代机制，让 Agent 系统越用越稳。",
  },
];

export default function MethodSection() {
  return (
    <section className="section method-section" id="method">
      <div className="section-heading">
        <p className="eyebrow">ChenForge method</p>
        <h2>一个克制的 AI 落地流程。</h2>
      </div>
      <div className="method-track">
        {STEPS.map((s) => (
          <article key={s.label}>
            <span>{s.label}</span>
            <h3>{s.title}</h3>
            <p>{s.desc}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
