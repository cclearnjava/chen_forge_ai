const AGENTS = [
  {
    code: "LA-01",
    name: "需求诊断 Agent",
    role: "把客户的模糊描述整理成业务目标、流程节点、风险点和 PoC 切入建议。",
    gate: "人工确认是否值得进入方案阶段",
  },
  {
    code: "SA-02",
    name: "方案架构 Agent",
    role: "生成系统边界、Agent 职责、数据流、工具权限和分阶段交付路线。",
    gate: "人工确认技术方向和安全边界",
  },
  {
    code: "PB-03",
    name: "Proposal Agent",
    role: "整理服务范围、里程碑、验收指标、报价结构和客户沟通材料。",
    gate: "人工确认报价和承诺范围",
  },
  {
    code: "FG-04",
    name: "构建 Agent",
    role: "根据批准的方案生成原型、脚本、测试清单、接口草案和部署说明。",
    gate: "人工审查代码和交付质量",
  },
  {
    code: "QA-05",
    name: "验证 Agent",
    role: "检查准确率、日志、异常路径、权限风险、回归问题和验收条件。",
    gate: "人工确认是否可以给客户试用",
  },
  {
    code: "CW-06",
    name: "案例沉淀 Agent",
    role: "把交付过程沉淀成案例、复盘、方法论和可复用的行业模板。",
    gate: "人工确认对外表达是否真实克制",
  },
  {
    code: "OP-07",
    name: "运营 Agent",
    role: "维护跟进提醒、会议纪要、待办列表、客户状态和决策摘要。",
    gate: "人工确认外部沟通内容",
  },
];

export default function AgentBench() {
  return (
    <section className="section" id="agents">
      <div className="section-heading">
        <p className="eyebrow">Supervised agent bench</p>
        <h2>ChenForge 的 Agent 团队服务于交付，不替代责任。</h2>
      </div>
      <div className="agent-grid">
        {AGENTS.map((agent) => (
          <article key={agent.code} className="agent-card">
            <div>
              <span>{agent.code}</span>
              <h3>{agent.name}</h3>
              <p>{agent.role}</p>
            </div>
            <footer>{agent.gate}</footer>
          </article>
        ))}
      </div>
    </section>
  );
}
