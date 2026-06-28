const PAIN_POINTS = [
  {
    index: "01",
    title: "场景太大",
    desc: "一上来就想做全公司 AI 平台，结果目标不清、周期过长、很难证明价值。",
  },
  {
    index: "02",
    title: "流程没拆透",
    desc: "没有明确输入、输出、权限、异常处理和人工审批，Agent 很难进入真实业务。",
  },
  {
    index: "03",
    title: "只有 Demo",
    desc: "演示能跑，但没有效果指标、日志追踪、质量评估和持续优化机制。",
  },
  {
    index: "04",
    title: "责任不清",
    desc: `企业真正需要的是"AI 提效，人来负责"，而不是把风险交给黑盒系统。`,
  },
];

export default function PainPoints() {
  return (
    <section className="section strip" id="pain">
      <div className="section-heading">
        <p className="eyebrow">Why AI projects stall</p>
        <h2>企业 AI 落地失败，通常不是模型不够强。</h2>
      </div>
      <div className="pain-grid">
        {PAIN_POINTS.map((p) => (
          <article key={p.index}>
            <span>{p.index}</span>
            <h3>{p.title}</h3>
            <p>{p.desc}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
