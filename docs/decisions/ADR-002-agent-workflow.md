# ADR-002：Agent 工作流架构

## 状态

Accepted

## 背景

ChenForge AI 的 Agent 不是完全自治员工，而是用于生成可审核交付物的工作流角色。MVP 必须证明“线索 -> 诊断 -> Proposal -> 人工审批”的闭环，同时避免真实 LLM 的不稳定性阻塞开发和测试。

## 决策

- MVP 使用轻量自定义 workflow runner，不引入 LangGraph。
- MVP Agent 阵容固定为 5 个：
  - 线索诊断 Agent。
  - 方案架构 Agent。
  - Proposal Agent。
  - 交付规划 Agent。
  - 质量审核 Agent。
- 所有 Agent 输出都写入 Artifact。
- 所有对客输出都必须创建 Decision，并标记为需要人工审批。
- LLM provider 必须先实现 mock provider，再接 OpenAI-compatible provider。
- Agent 不能直接修改业务状态，所有状态变更必须通过 workflow runner。

## 方案比较

### 轻量 workflow runner vs LangGraph

- LangGraph 更适合复杂状态机和多 Agent 编排，但第一周会增加学习和调试成本。
- 轻量 workflow runner 足够表达 MVP 的顺序流程和审批门禁。
- 当前系统最重要的是跑通业务闭环，而不是证明编排框架能力。

裁决：MVP 使用轻量 workflow runner；LangGraph 不进入本周范围。

### 真实 LLM 优先 vs mock LLM 优先

- 真实 LLM 能更早看到质量，但会引入网络、成本、随机性和 key 管理问题。
- mock LLM 能保证测试、联调和 demo 稳定。
- 真实 provider 可以在 mock provider 接口稳定后接入。

裁决：先实现 mock LLM provider。

## 不变量

- Agent 输出建议，不拥有最终决策权。
- 对客表达不能绕过 ApprovalGate。
- prompt 版本、模型名称、原始响应、解析结果必须随 Artifact 保存。
- 测试默认使用 mock provider，真实 provider 不进入默认测试路径。

