---
status: open
prevention_status: open
mechanism_layer: convention
severity: P1
component: ChenForgeAI MVP
---

# ChenForge AI MVP Gate 0 问题锁定

## 问题陈述

ChenForge AI 需要在一周内从静态门户演进成一个可用的一人 AI 咨询公司 MVP。系统必须让 ToB 访问者提交业务问题，并让人工负责人在私有后台中查看线索、运行 Agent 诊断、审核生成物，并决定是否进入 PoC proposal。

## Change Classification

分类：`contract`

原因：

- 新增公开表单到后端 Lead API 的契约。
- 新增后台到后端 Lead / Artifact / Decision / AgentTask API 的契约。
- 新增 Agent workflow 输出 schema，前端和后端都要消费。
- 新增审批状态枚举和 artifact 类型枚举，属于跨模块共享协议。

最低门禁：

- Gate 1 必须有 ADR 和消费方清单。
- Gate 3 PLAN 必须映射到真实文件、路径、API contract。
- Gate 4 之前必须消除 plan-lock 口子词。
- Gate 5 必须按 write_set 拆 WP，并指定 seam owner。

## 成功标准

- 访问者能提交一个业务问题。
- 后端能保存线索。
- 后台能读取线索并触发诊断。
- mock LLM provider 能生成确定性诊断 artifact。
- 人工负责人能批准、暂缓或要求重写。
- 对客输出不能绕过人工审批。

## 非目标

- 本周不做完整 SaaS。
- 本周不做客户门户。
- 本周不做支付。
- 本周不做复杂 CRM。
- 本周不做实时协作。
- 本周不做通用 Agent Builder。

