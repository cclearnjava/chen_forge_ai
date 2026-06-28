const SERVICES = [
  {
    tag: "Agent Workflow",
    title: "业务流程 Agent",
    desc: "把线索跟进、内容生产、运营检查、资料整理等重复流程，改造成带审批的 Agent 工作流。",
  },
  {
    tag: "Knowledge/RAG",
    title: "企业知识库问答",
    desc: "把制度、产品资料、技术文档、FAQ 和销售话术，变成可追踪引用的内部问答系统。",
  },
  {
    tag: "ChatBI",
    title: "自然语言问数",
    desc: "围绕数据指标、口径和权限，构建让业务人员能直接提问的数据查询和分析入口。",
  },
  {
    tag: "MVP Delivery",
    title: "AI 软件原型交付",
    desc: "快速交付能验证价值的内部工具、自动化后台、管理驾驶舱和集成脚本。",
  },
];

export default function Services() {
  return (
    <section className="section" id="services">
      <div className="section-heading">
        <p className="eyebrow">What we build</p>
        <h2>从一个业务问题开始，交付能被使用的 AI 系统。</h2>
      </div>
      <div className="service-grid">
        {SERVICES.map((s) => (
          <article key={s.tag}>
            <span>{s.tag}</span>
            <h3>{s.title}</h3>
            <p>{s.desc}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
