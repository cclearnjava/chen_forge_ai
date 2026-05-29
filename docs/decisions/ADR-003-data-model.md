# ADR-003：核心数据模型

## 状态

Accepted

## 背景

MVP 的核心价值链是：访问者提交业务问题，系统保存线索，Agent 生成诊断和 proposal，人工负责人审核并决定下一步。数据模型必须服务这个闭环，而不是提前扩展成完整 CRM。

## 决策

MVP 锁定 5 个核心模型：

1. `Lead`
   - 表示客户提交的业务问题。
   - 是诊断、proposal 和交付计划的根实体。

2. `AgentTask`
   - 表示一次 Agent 执行。
   - 保存输入、输出、状态、错误、开始和完成时间。

3. `Artifact`
   - 表示 Agent 或人工产出的生成物。
   - 内容同时支持 Markdown 和 JSON。
   - 对客生成物必须有 `requires_approval`。

4. `Decision`
   - 表示人工审批动作。
   - 状态包括 waiting、approved、deferred、rewrite_requested。

5. `AuditLog`
   - 表示关键动作记录。
   - 用于复盘和追踪责任边界。

## 消费方

- 公开官网消费 `Lead create`。
- 后台线索列表消费 `Lead list`。
- 后台线索详情消费 `Lead detail`、`Artifact list`、`Decision list`。
- Agent workflow 消费 `Lead`，生产 `AgentTask`、`Artifact`、`Decision`、`AuditLog`。
- Quality Reviewer 消费 `Artifact`，生产 review artifact 和 decision recommendation。

## 不纳入 MVP 的模型

- ClientAccount。
- Payment。
- Contract。
- ClientPortalUser。
- NotificationSubscription。
- Full CRM pipeline。

## 后果

- 后台不是完整 CRM，只是运营控制台。
- 线索状态足够表达 MVP，但不能承载复杂销售流程。
- 后续扩展客户门户时，需要新增用户、权限和客户组织模型。

