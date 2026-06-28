# ChenForge AI 进度记录

## 2026-05-28

- 创建了一周 MVP 的计划文件。
- 将 MVP 定义为：公开 ToB 门户 + 私有运营后台。
- 选择第一条核心业务流程：线索提交 -> 诊断摘要 -> PoC Proposal。
- 拆分了前端、后端、数据库、后台、Agent 工作流、人工审批和部署任务。

## 2026-05-29

- 继续细化 MVP 任务计划。
- 增加了 Agent 阵容、前端实现拆解、后端实现拆解、API endpoint、数据模型字段和测试清单。
- 将 MVP Agent 范围控制在 5 个角色：线索诊断、方案架构、Proposal、交付规划、质量审核。
- 将规划文件改成中文版本，方便后续执行和复盘。
- 补充测试策略、mock LLM provider 具体实现计划、git 分支策略和前后端联调时间窗口。
- 填充 `.claude/skills/arch/SKILL.md` 的 6 个项目世界观槽位：核心使命、世界观、核心原语、分层架构、技术路径、关键约束。
- 创建 `docs/api-contract.md`，冻结 MVP 前后端接口契约。
- 初始化 git 仓库，并创建 `codex/chenforge-mvp-shell` 开发分支。
- 补充 `CLAUDE.md` 项目概述、技术路线、治理产物和 path-scoped rules 列表。

## 2026-05-31

- 确认 MVP 登录方案为邮箱验证码登录，手机号验证码不进入第一版。
- 确认客户正式发送渠道 MVP 先使用邮件，但通过 Delivery Center 保留多通道扩展能力。
- 新增登录、需求提交、AI 草案、人工审批和邮件发送闭环设计文档。
- 更新 API contract，加入邮箱验证码、附件、DeliveryJob、NotificationEvent、发送状态和新 Agent 输出契约。
- 更新 ADR-002 和 ADR-003，把“AI 生成方案，人工审批修改，批准后发送”纳入核心架构不变量。
- 更新一周任务计划，补充 Auth、附件上传、内部通知、Delivery Center 和邮件发送测试任务。
