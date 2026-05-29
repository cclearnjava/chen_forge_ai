# ChenForge AI 消费方清单

## API 消费方

| 契约 | 生产方 | 消费方 | 语义 |
| --- | --- | --- | --- |
| `POST /api/v1/leads` | 后端 Lead API | 公开官网 `LeadIntakeForm` | 创建线索 |
| `GET /api/v1/leads` | 后端 Lead API | 后台 `LeadInbox` | 查看线索列表 |
| `GET /api/v1/leads/{lead_id}` | 后端 Lead API | 后台 `LeadDetail` | 查看线索详情 |
| `PATCH /api/v1/leads/{lead_id}` | 后端 Lead API | 后台状态控制 | 更新线索状态 |
| `POST /api/v1/leads/{lead_id}/run-diagnosis` | Agent API | 后台线索详情 | 触发诊断工作流 |
| `POST /api/v1/leads/{lead_id}/run-proposal` | Agent API | 后台线索详情 | 触发 Proposal 工作流 |
| `GET /api/v1/agent-tasks/{task_id}` | Agent API | 后台任务状态展示 | 查询 Agent 任务状态 |
| `GET /api/v1/leads/{lead_id}/artifacts` | Artifact API | 后台生成物列表 | 查询线索生成物 |
| `GET /api/v1/artifacts/{artifact_id}` | Artifact API | 后台生成物查看器 | 查看生成物详情 |
| `POST /api/v1/artifacts/{artifact_id}/approve` | Artifact API | 后台生成物查看器 | 批准生成物 |
| `GET /api/v1/decisions` | Decision API | 后台决策队列 | 查看待决策项 |
| `POST /api/v1/decisions/{decision_id}/approve` | Decision API | 后台决策动作 | 批准决策 |
| `POST /api/v1/decisions/{decision_id}/defer` | Decision API | 后台决策动作 | 暂缓决策 |
| `POST /api/v1/decisions/{decision_id}/request-rewrite` | Decision API | 后台决策动作 | 要求重写 |

## 数据消费方

| 数据模型 | 数据消费方 | 行为消费方 | 可见性消费方 |
| --- | --- | --- | --- |
| Lead | 后台列表、线索详情、Agent workflow | 状态更新、运行诊断 | 后台筛选、搜索、详情页 |
| AgentTask | 后台任务状态、审计日志 | workflow runner、失败重试 | 线索详情任务记录 |
| Artifact | 生成物查看器、Quality Reviewer | 审批、复制、导出 | 线索详情、artifact list |
| Decision | 决策队列、线索详情 | approve/defer/rewrite | 后台决策队列 |
| AuditLog | 线索详情、后续复盘 | 记录动作 | 后台审计时间线 |

## 接缝责任

| 接缝 | 生产端 owner | 消费端 owner | 验证 owner |
| --- | --- | --- | --- |
| 公开表单 -> Lead API | 后端 WP | 前端 WP | 联调 WP |
| Lead API -> Dashboard | 后端 WP | 前端后台 WP | 联调 WP |
| Agent workflow -> Artifact | Agent WP | 前端后台 WP | 联调 WP |
| Artifact -> Decision | Agent WP | 前端后台 WP | 联调 WP |
| Decision action -> AuditLog | 后端 WP | 前端后台 WP | 联调 WP |

