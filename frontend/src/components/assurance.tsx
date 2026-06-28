const ASSURANCES = [
  {
    title: "人工审批",
    desc: "关键动作、外部发送、价格、合同和生产变更必须人工确认。",
  },
  {
    title: "权限边界",
    desc: "Agent 只能访问被授权的数据、工具和流程，不做越权操作。",
  },
  {
    title: "效果指标",
    desc: "每个 PoC 都绑定准确率、效率、成本、使用率或转化指标。",
  },
  {
    title: "可审计日志",
    desc: "保留输入、输出、工具调用、失败原因和人工决策记录。",
  },
];

export default function Assurance() {
  return (
    <section className="section assurance-section">
      <div className="section-heading">
        <p className="eyebrow">Delivery assurance</p>
        <h2>老板关心的不是 AI 多聪明，而是能不能可靠上线。</h2>
      </div>
      <div className="assurance-grid">
        {ASSURANCES.map((a) => (
          <article key={a.title}>
            <strong>{a.title}</strong>
            <span>{a.desc}</span>
          </article>
        ))}
      </div>
    </section>
  );
}
