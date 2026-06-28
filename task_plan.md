# ChenForge AI 一周 MVP 任务计划

## 目标

在一周内把 ChenForge AI 做成一个可用的一人 AI 咨询公司门户：包括面向 ToB 老板的高质量官网、邮箱验证码登录、需求提交入口、私有运营后台，以及第一个能把客户业务问题转成需求理解、客户回复草稿、方案草案和 PoC 建议的 Agent 工作流。

## MVP 范围

### 必须实现

- 面向企业老板的公开官网。
- 展示 AI Agent 工作流、RAG、ChatBI、AI 软件 MVP 交付等服务。
- 邮箱验证码登录或注册。
- 需求提交表单，并把数据保存到后端数据库。
- 文档和截图附件上传，视频使用链接形式提交。
- 私有后台，用来查看线索、诊断摘要、决策项和生成物。
- 一条可运行的 Agent 工作流：需求理解 -> 客户回复草稿 -> 方案草案 -> PoC 建议。
- 所有对外输出前必须有人类审批，审批后 MVP 通过邮件发送给客户。
- 内部提醒通过飞书或企业微信群机器人通知负责人。
- 有基本的本地启动和部署路径。

### 本周可纳入但不阻塞 MVP

- 生成物版本历史。
- 客户回复草稿的多版本对比。
- 案例占位内容。
- CTA 和表单转化事件统计。

### 本周不做

- 完整自治的多 Agent 公司。
- 支付集成。
- 客户门户。
- 手机号验证码。
- 视频大文件上传和转码。
- 复杂 CRM。
- 实时协作。
- 通用 Agent Builder。

## 推荐技术栈

- 前端：Next.js + TypeScript + Tailwind CSS 或 CSS Modules。
- 后端：FastAPI + Python。
- 数据库：本地 MVP 用 SQLite，模型设计保持 Postgres 迁移友好。
- ORM：SQLAlchemy。
- Agent 工作流：第一版锁定为轻量自定义流程；LangGraph 不进入本周 MVP。
- LLM 供应商：OpenAI-compatible adapter，通过环境变量配置。
- 邮箱验证码和客户发送：MVP 使用 SMTP 或邮件服务 provider，后续可替换。
- 内部通知：飞书或企业微信群机器人 Webhook。
- 附件存储：本地开发使用 `backend/storage/uploads`，正式环境预留对象存储适配。
- 部署：本周锁定为前端 Vercel、后端 Render。单 VPS 不进入本周 MVP。

## 工程策略

### 测试策略

- [ ] 采用“关键路径 TDD + 页面快速迭代后补测试”的混合策略。
- [ ] 后端核心逻辑必须先写测试再实现：
  - [ ] 数据模型和 repository。
  - [ ] Lead API。
  - [ ] 邮箱验证码登录。
  - [ ] 附件上传。
  - [ ] Agent workflow。
  - [ ] mock LLM provider。
  - [ ] 决策审批。
  - [ ] Delivery Center 邮件发送。
- [ ] 前端公共官网允许先实现再补组件测试，但线索提交和后台审批链路必须有测试。
- [ ] 后端测试框架：
  - [ ] `pytest`。
  - [ ] `pytest-asyncio`，如使用异步接口。
  - [ ] `httpx` 或 FastAPI `TestClient` 做 API 测试。
  - [ ] SQLite 临时测试库。
- [ ] 前端测试框架：
  - [ ] Vitest 或 Jest。
  - [ ] React Testing Library。
  - [ ] Playwright 用于端到端冒烟测试。
- [ ] 每天结束前至少跑：
  - [ ] 后端单测。
  - [ ] 前端 typecheck/lint。
  - [ ] 一条端到端手工或 Playwright 冒烟流程。

### Git 分支策略

- [ ] 初始化 git 仓库，若尚未初始化。
- [ ] 主分支保留为 `main`。
- [ ] 开发分支统一使用 `codex/` 前缀。
- [ ] 本周建议分支：
  - [ ] `codex/chenforge-mvp-shell`：Next.js/项目骨架。
  - [ ] `codex/chenforge-backend-api`：FastAPI、数据库、Lead API。
  - [ ] `codex/chenforge-dashboard`：后台页面。
  - [ ] `codex/chenforge-agent-workflow`：mock LLM 和 Agent 工作流。
  - [ ] `codex/chenforge-integration-polish`：前后端联调、测试、部署。
- [ ] 每个分支合并前必须满足：
  - [ ] 对应测试通过。
  - [ ] README 或计划文件同步更新。
  - [ ] 没有提交 `.env`、数据库文件、密钥或临时日志。
- [ ] commit 粒度按可验证功能提交，不按“大量改完一起提交”。

### 前后端联调策略

- [ ] 第 3 天后端 Lead API 完成后，立即预留半天做第一次联调。
- [ ] 第 5 天 Agent 工作流完成后，预留半天做第二次联调。
- [ ] 第 7 天只做缺陷修复和部署准备，不再引入大功能。
- [ ] 前后端之间先定义 API contract：
  - [ ] 请求字段。
  - [ ] 响应字段。
  - [ ] 错误格式。
  - [ ] 状态枚举。
- [ ] 前端在后端未完成前使用 mock API 或静态 fixture。
- [ ] 后端完成后前端切换到真实 API。
- [ ] 联调必须覆盖：
  - [ ] 公开表单提交。
  - [ ] 后台线索列表。
  - [ ] 线索详情。
  - [ ] 运行诊断。
  - [ ] 展示生成物。
  - [ ] 批准或暂缓决策。
  - [ ] 批准并发送邮件。

## 一周排期

### 第 1 天：产品基础与前端升级

- [ ] 确认最终导航和页面区块。
- [ ] 把当前静态站迁移成 Next.js 应用。
- [ ] 创建可复用布局组件：头部、底部、区块标题、CTA、卡片。
- [ ] 继续打磨“精密 AI 工坊”的视觉系统。
- [ ] 检查桌面、平板、移动端响应式。
- [ ] 保留当前 canvas hero，或替换成更可控的 SVG/canvas 组件。

### 第 2 天：公开官网内容与转化漏斗

- [ ] 搭建首页区块：
  - [ ] Hero 首屏。
  - [ ] AI 落地痛点。
  - [ ] 服务说明。
  - [ ] 方法论。
  - [ ] Agent 团队。
  - [ ] 交付保障。
  - [ ] 线索提交 CTA。
- [ ] 增加服务详情页或可展开服务面板。
- [ ] 增加邮箱验证码登录入口。
- [ ] 增加“从一个业务流程开始”的需求提交表单。
- [ ] 增加文档和截图上传入口。
- [ ] 增加视频链接字段。
- [ ] 增加案例占位：
  - [ ] 企业知识库问答。
  - [ ] ChatBI 数据运营。
  - [ ] Agent 工作流自动化。
- [ ] 增加 SEO metadata 和 Open Graph metadata。

### 第 3 天：后端 API 与数据库

- [ ] 创建 FastAPI 后端。
- [ ] 创建数据库模型：
  - [ ] Lead，线索。
  - [ ] LeadAttachment，附件。
  - [ ] VerificationCode，邮箱验证码。
  - [ ] DiagnosisBrief，诊断摘要。
  - [ ] AgentTask，Agent 任务。
  - [ ] Decision，人工决策项。
  - [ ] Artifact，生成物。
  - [ ] DeliveryJob，对客发送任务。
  - [ ] NotificationEvent，内部通知事件。
- [ ] 实现线索提交 API。
- [ ] 实现邮箱验证码发送和校验 API。
- [ ] 实现附件上传 API。
- [ ] 实现后台用的线索列表和线索详情 API。
- [ ] 实现生成物创建和读取 API。
- [ ] 添加本地 SQLite 数据库。
- [ ] 添加 API 错误处理和请求校验。
- [ ] 定义前后端 API contract 文档。
- [ ] 做第一次前后端联调：邮箱验证码登录 -> 公开表单提交 -> 附件上传 -> 后端保存线索 -> 后台列表读取。

### 第 4 天：私有运营后台

- [ ] 创建后台路由。
- [ ] 添加基础管理员访问保护。
- [ ] 创建线索收件箱。
- [ ] 创建线索详情页。
- [ ] 创建附件列表和预览入口。
- [ ] 展示生成的诊断摘要。
- [ ] 展示客户回复草稿和方案草案。
- [ ] 展示人工决策队列。
- [ ] 展示生成物列表。
- [ ] 添加状态变更：新线索、审核中、已诊断、已出方案、已联系、已归档。
- [ ] 补齐 dashboard 与真实 API 的 loading、empty、error 状态。

### 第 5 天：第一条 Agent 工作流

- [ ] 定义诊断 prompt 和结构化输出 schema。
- [ ] 构建 LLM provider adapter。
- [ ] 先实现确定性的 mock LLM provider，并用它驱动测试和本地演示。
- [ ] 再接 OpenAI-compatible provider，保持同一接口。
- [ ] 构建工作流：
  - [ ] 标准化线索输入。
  - [ ] 读取附件元数据和视频链接。
  - [ ] 生成需求理解。
  - [ ] 诊断业务问题。
  - [ ] 推荐第一个 PoC。
  - [ ] 估算复杂度和风险。
  - [ ] 生成客户回复草稿。
  - [ ] 生成方案草案。
- [ ] 把所有 Agent 输出保存成生成物。
- [ ] 把客户可见输出标记为需要人工审批。
- [ ] 添加重试和失败状态。
- [ ] 做第二次前后端联调：后台触发需求分析 -> 后端生成需求理解、回复草稿、方案草案 -> 前端展示 artifact 和 decision。

### 第 6 天：人工审批与 Proposal 生成物

- [ ] 添加 approve / defer / request rewrite 决策动作。
- [ ] 添加 edit and approve 决策动作。
- [ ] 添加 Proposal 草稿生成物。
- [ ] 添加 discovery call agenda 生成物。
- [ ] 添加实施路线图生成物。
- [ ] 添加 Delivery Center 邮件发送。
- [ ] 添加邮件发送状态：draft、queued、sending、sent、failed。
- [ ] 添加飞书或企业微信内部通知。
- [ ] 添加导出 Markdown。
- [ ] 添加复制已审批客户回复。
- [ ] 添加基础审计日志。
- [ ] 联调审批链路：approve / edit and approve / defer / request rewrite。
- [ ] 联调发送链路：已审批 artifact -> DeliveryJob -> 邮件发送 -> 发送状态回写。
- [ ] 修复前后端字段不一致、状态不一致、错误格式不一致的问题。

### 第 7 天：打磨、测试、部署

- [ ] 做响应式设计检查。
- [ ] 做无障碍检查。
- [ ] 测试公开表单提交完整链路。
- [ ] 测试邮箱验证码登录完整链路。
- [ ] 测试附件上传限制和失败提示。
- [ ] 测试后台线索查看完整链路。
- [ ] 测试 Agent 工作流成功路径和失败路径。
- [ ] 测试审批后邮件发送成功路径和失败路径。
- [ ] 补充 README 本地启动说明。
- [ ] 添加环境变量模板。
- [ ] 部署，或准备部署说明。
- [ ] 写第一篇公开案例风格文章草稿。

## 前端任务清单

### 品牌与设计

- [ ] 最终确认视觉方向：精密 AI 工坊。
- [ ] 定义颜色 token。
- [ ] 定义字体层级。
- [ ] 定义按钮样式。
- [ ] 定义卡片样式。
- [ ] 定义表单样式。
- [ ] 定义后台表格和列表样式。
- [ ] 定义移动端间距规则。
- [ ] 定义视觉资产方向：
  - [ ] 保留 canvas hero，或转换成可控 SVG/canvas 组件。
  - [ ] 避免泛滥的 AI 光球、紫色渐变和模板化插画。
  - [ ] 使用蓝图线、工作流图、证据面板、精密工坊细节。
- [ ] 定义信任感视觉语言：
  - [ ] 结果指标模块。
  - [ ] 审批节点徽章。
  - [ ] 审计日志片段。
  - [ ] PoC 时间线模块。

### 公开官网

- [ ] 首页。
- [ ] 服务区块。
- [ ] 方法论区块。
- [ ] Agent 团队区块。
- [ ] 交付保障区块。
- [ ] 案例区块。
- [ ] 线索提交区块。
- [ ] 底部信息，包含联系方式和可信度说明。
- [ ] 首页首屏内容：
  - [ ] 主标题。
  - [ ] 副标题。
  - [ ] 主 CTA：提交业务问题。
  - [ ] 副 CTA：查看落地方法。
  - [ ] 三个信任指标。
- [ ] AI 落地痛点模块：
  - [ ] 场景太大。
  - [ ] 流程没拆透。
  - [ ] Demo 进不了生产。
  - [ ] 责任不清。
- [ ] 服务卡片：
  - [ ] Agent 工作流。
  - [ ] RAG 知识库问答。
  - [ ] ChatBI。
  - [ ] AI 软件 MVP。
- [ ] 方法论时间线：
  - [ ] Diagnose，诊断。
  - [ ] Design，设计。
  - [ ] Forge，构建。
  - [ ] Verify，验证。
  - [ ] Operate，运营。
- [ ] 交付保障卡片：
  - [ ] 人工审批。
  - [ ] 权限边界。
  - [ ] 可衡量结果。
  - [ ] 可审计日志。
- [ ] 案例占位：
  - [ ] 改造前后。
  - [ ] 业务问题。
  - [ ] AI 工作流。
  - [ ] 价值指标。
- [ ] 联系和线索转化模块：
  - [ ] 邮箱验证码登录。
  - [ ] 业务问题字段。
  - [ ] 期望第一阶段结果。
  - [ ] 联系人姓名。
  - [ ] 邮箱或微信。
  - [ ] 公司规模。
  - [ ] 预算和时间，可选。
  - [ ] 文档和截图上传。
  - [ ] 视频链接。

### 后台

- [ ] 登录或管理员访问保护。
- [ ] 后台整体 shell。
- [ ] 线索收件箱。
- [ ] 线索详情。
- [ ] 诊断摘要查看器。
- [ ] 决策队列。
- [ ] 生成物查看器。
- [ ] AI 回复草稿编辑器。
- [ ] 方案草案编辑器。
- [ ] 邮件发送预览。
- [ ] DeliveryJob 状态查看。
- [ ] 状态控制。
- [ ] 复制和导出操作。
- [ ] 后台概览：
  - [ ] 新线索数量。
  - [ ] 等待决策数量。
  - [ ] 草稿生成物数量。
  - [ ] 转化阶段数量。
- [ ] 线索收件箱筛选：
  - [ ] 状态。
  - [ ] 期望结果。
  - [ ] 创建日期。
  - [ ] 按公司或问题搜索。
- [ ] 线索详情面板：
  - [ ] 提交资料。
  - [ ] 诊断摘要。
  - [ ] 推荐 PoC。
  - [ ] 缺失问题。
  - [ ] 风险标记。
  - [ ] 下一步决策。
- [ ] 生成物查看器：
  - [ ] Markdown 渲染。
  - [ ] 版本列表。
  - [ ] 复制按钮。
  - [ ] 导出 Markdown 按钮。
- [ ] 决策工作流 UI：
  - [ ] 批准。
  - [ ] 修改后批准。
  - [ ] 暂缓。
  - [ ] 要求重写。
  - [ ] 批准并发送邮件。
  - [ ] 标记已联系。

### 体验细节

- [ ] 表单校验。
- [ ] 加载状态。
- [ ] 空状态。
- [ ] 错误状态。
- [ ] 成功状态。
- [ ] 移动端导航。
- [ ] 键盘焦点状态。
- [ ] 审批确认状态。
- [ ] Toast 通知。
- [ ] 保存中禁用提交按钮。
- [ ] API 失败后保留表单输入。
- [ ] 验证码发送后显示倒计时。
- [ ] 附件上传失败时明确显示原因。
- [ ] 邮件发送失败后允许后台重试。
- [ ] 只在后台展示后端或 Agent 错误细节，不在公开页面暴露。
- [ ] 公开表单提交成功后展示“接下来会发生什么”。
- [ ] 后台移动端降级布局。

## 后端任务清单

### API 基础

- [ ] FastAPI 应用脚手架。
- [ ] settings/config 配置模块。
- [ ] 为本地前端设置 CORS。
- [ ] 健康检查 endpoint。
- [ ] 统一错误响应。
- [ ] 请求校验。
- [ ] API 前缀：`/api/v1`。
- [ ] Request ID 中间件。
- [ ] 基础日志。
- [ ] 从 `.env` 加载环境变量。
- [ ] 本地开发启动命令。
- [ ] 后端测试命令。

### 数据库

- [ ] 本地 SQLite 数据库。
- [ ] SQLAlchemy 模型。
- [ ] 迁移路径或初始化脚本。
- [ ] Repository / service 层。
- [ ] Seed 示例线索。
- [ ] 定义枚举：
  - [ ] LeadStatus：new、reviewing、diagnosed、proposed、contacted、sent、archived。
  - [ ] TaskStatus：pending、running、succeeded、failed。
  - [ ] DecisionStatus：waiting、approved、edited_and_approved、deferred、rewrite_requested。
  - [ ] ArtifactType：diagnosis、architecture、proposal、email、roadmap、audit、requirement_summary、customer_reply_draft、proposal_draft、discovery_questions、delivery_roadmap、sent_message。
  - [ ] DeliveryChannel：email、feishu、wecom、sms、client_portal、manual_copy。
  - [ ] DeliveryStatus：draft、queued、sending、sent、failed、cancelled。
- [ ] 添加时间戳：
  - [ ] created_at。
  - [ ] updated_at。
  - [ ] completed_at，按需使用。
- [ ] 添加线索软删除或归档能力。

### 核心资源

- [ ] Lead 创建、列表、详情、更新。
- [ ] LeadAttachment 创建、列表。
- [ ] VerificationCode 创建、校验、过期。
- [ ] DiagnosisBrief 创建、列表、详情。
- [ ] AgentTask 创建、列表、更新。
- [ ] Decision 创建、列表、更新。
- [ ] Artifact 创建、列表、详情。
- [ ] DeliveryJob 创建、发送、查询、重试。
- [ ] NotificationEvent 创建、发送、查询。
- [ ] AuditLog 创建、列表。
- [ ] Auth endpoints：
  - [ ] `POST /api/v1/auth/email/start`。
  - [ ] `POST /api/v1/auth/email/verify`。
- [ ] Lead endpoints：
  - [ ] `POST /api/v1/leads`。
  - [ ] `GET /api/v1/leads`。
  - [ ] `GET /api/v1/leads/{lead_id}`。
  - [ ] `PATCH /api/v1/leads/{lead_id}`。
  - [ ] `POST /api/v1/leads/{lead_id}/attachments`。
- [ ] Agent endpoints：
  - [ ] `POST /api/v1/leads/{lead_id}/run-intake-response`。
  - [ ] `POST /api/v1/leads/{lead_id}/run-diagnosis`。
  - [ ] `POST /api/v1/leads/{lead_id}/run-proposal`。
  - [ ] `GET /api/v1/agent-tasks/{task_id}`。
- [ ] Decision endpoints：
  - [ ] `GET /api/v1/decisions`。
  - [ ] `POST /api/v1/decisions/{decision_id}/approve`。
  - [ ] `POST /api/v1/decisions/{decision_id}/defer`。
  - [ ] `POST /api/v1/decisions/{decision_id}/request-rewrite`。
- [ ] Artifact endpoints：
  - [ ] `GET /api/v1/leads/{lead_id}/artifacts`。
  - [ ] `GET /api/v1/artifacts/{artifact_id}`。
  - [ ] `POST /api/v1/artifacts/{artifact_id}/approve`。
  - [ ] `PATCH /api/v1/artifacts/{artifact_id}`。
- [ ] Delivery endpoints：
  - [ ] `POST /api/v1/delivery-jobs`。
  - [ ] `POST /api/v1/delivery-jobs/{delivery_job_id}/send`。
  - [ ] `GET /api/v1/delivery-jobs/{delivery_job_id}`。

### Agent 工作流

- [ ] LLM provider interface。
- [ ] OpenAI-compatible 实现。
- [ ] Mock LLM provider 具体实现：
  - [ ] 定义统一接口 `generate_json(prompt_name, input_payload, output_schema)`。
  - [ ] 根据 `prompt_name` 返回固定结构化结果。
  - [ ] 支持成功场景：返回合法 JSON。
  - [ ] 支持失败场景：返回非法 JSON 或抛出模拟异常。
  - [ ] 支持延迟场景：可配置 sleep，测试 loading/running 状态。
  - [ ] 支持不同线索输入生成略有差异的 deterministic 输出，避免所有测试结果完全一样。
  - [ ] 不访问网络，不读取真实 LLM key。
  - [ ] 在测试环境默认使用 mock provider。
  - [ ] 在本地 demo 环境允许通过环境变量切换 mock / real provider。
- [ ] Prompt 模板。
- [ ] 结构化输出 schema。
- [ ] Workflow runner。
- [ ] 持久化 trace 和生成物。
- [ ] 失败处理。
- [ ] 手动重新运行 endpoint。
- [ ] Prompt 目录：
  - [ ] `prompts/lead_diagnosis.md`。
  - [ ] `prompts/intake_response.md`。
  - [ ] `prompts/solution_architect.md`。
  - [ ] `prompts/proposal.md`。
  - [ ] `prompts/delivery_planner.md`。
  - [ ] `prompts/quality_reviewer.md`。
- [ ] 每个生成物保存 prompt 版本。
- [ ] 每个生成物保存模型名称。
- [ ] 原始模型响应与解析后的结构化输出分开保存。
- [ ] 添加 JSON 结构化解析和失败兜底。
- [ ] 为测试添加确定性的 mock LLM provider。
- [ ] 为 mock LLM provider 添加单元测试：
  - [ ] diagnosis prompt 返回诊断 schema。
  - [ ] proposal prompt 返回 proposal schema。
  - [ ] failure mode 会创建 failed task。
  - [ ] mock provider 不依赖外部网络。

### 安全

- [ ] 后台管理员密码或 token 认证。
- [ ] 环境变量管理。
- [ ] 不把 LLM key 暴露到前端。
- [ ] 输入清洗。
- [ ] 公开表单限流或简单防刷。
- [ ] 对外消息必须人工审批。
- [ ] MVP 阶段 Agent 不允许直接创建已发送状态。
- [ ] 邮件发送必须基于已审批 Artifact。
- [ ] 验证码只保存哈希，不保存明文。
- [ ] 附件限制文件类型和大小。
- [ ] 公开表单防垃圾提交：
  - [ ] Honeypot 字段。
  - [ ] 最短提交时间。
  - [ ] IP/day 限制不进入本周 MVP，只实现 honeypot 字段和最短提交时间。
- [ ] 后台认证：
  - [ ] MVP 单管理员 token。
  - [ ] token 只保存在服务端环境变量。
  - [ ] 前端通过安全 admin session 或 header 访问后台 API。
- [ ] LLM 安全：
  - [ ] prompt 中不包含密钥。
  - [ ] prompt 上下文只包含线索数据和已批准模板。
  - [ ] MVP 阶段不允许 Agent 直接发邮件。

### Delivery Center

- [ ] 定义 DeliveryProvider interface。
- [ ] 实现 EmailDeliveryProvider。
- [ ] 定义邮件模板渲染。
- [ ] 创建 DeliveryJob。
- [ ] 发送前校验 Artifact 已审批。
- [ ] 保存最终发送内容快照。
- [ ] 保存 provider message id。
- [ ] 保存失败原因。
- [ ] 支持后台重试失败发送。
- [ ] 写入 AuditLog。
- [ ] 为后续通道保留 provider registry：
  - [ ] feishu。
  - [ ] wecom。
  - [ ] sms。
  - [ ] client_portal。
  - [ ] manual_copy。

### 内部通知

- [ ] 定义 NotificationProvider interface。
- [ ] 实现飞书或企业微信群机器人 Webhook。
- [ ] 新 Lead 创建后通知负责人。
- [ ] Agent 生成失败后通知负责人。
- [ ] 有待审批 Decision 后通知负责人。
- [ ] DeliveryJob 发送失败后通知负责人。
- [ ] 保存 NotificationEvent。

## Agent 工作流清单

### MVP Agent 阵容

MVP 只保留 5 个 Agent。它们不是“自治员工”，而是确定性的工作流角色，用来为你这个人工负责人生成可审核的交付物。

1. 线索诊断 Agent。
2. 方案架构 Agent。
3. Proposal Agent。
4. 交付规划 Agent。
5. 质量审核 Agent。

### 线索诊断 Agent

- [ ] 输入：公司、业务问题、期望结果、联系方式、可选预算和时间。
- [ ] 输出：业务痛点摘要、自动化适配度、推荐 PoC、风险、缺失问题。
- [ ] 存储：诊断摘要生成物。
- [ ] 输出 schema：
  - [ ] `pain_summary`，痛点摘要。
  - [ ] `business_goal`，业务目标。
  - [ ] `workflow_candidates`，候选工作流。
  - [ ] `recommended_first_poc`，推荐第一个 PoC。
  - [ ] `suitability_score`，适配度评分。
  - [ ] `risk_flags`，风险标记。
  - [ ] `missing_questions`，缺失问题。
  - [ ] `next_step_recommendation`，下一步建议。
- [ ] 不允许承诺业务结果。
- [ ] 输入模糊时必须提出需要补充的问题。

### 方案架构 Agent

- [ ] 输入：诊断摘要。
- [ ] 输出：工作流地图、所需数据和工具、系统边界、审批节点。
- [ ] 存储：架构简报生成物。
- [ ] 输出 schema：
  - [ ] `workflow_steps`，流程步骤。
  - [ ] `agent_responsibilities`，Agent 职责。
  - [ ] `required_data_sources`，所需数据源。
  - [ ] `required_tools`，所需工具。
  - [ ] `human_approval_gates`，人工审批节点。
  - [ ] `security_boundaries`，安全边界。
  - [ ] `integration_notes`，集成说明。
- [ ] 必须把范围标记为 small、medium 或 large。
- [ ] 当需求不适合 Agent 自动化时，必须明确指出。

### Proposal Agent

- [ ] 输入：诊断摘要和架构简报。
- [ ] 输出：discovery agenda、PoC 范围、里程碑、验收指标、客户回复草稿。
- [ ] 存储：Proposal 生成物。
- [ ] 输出 schema：
  - [ ] `proposal_summary`，方案摘要。
  - [ ] `discovery_agenda`，访谈议程。
  - [ ] `poc_scope`，PoC 范围。
  - [ ] `milestones`，里程碑。
  - [ ] `acceptance_metrics`，验收指标。
  - [ ] `out_of_scope`，不包含范围。
  - [ ] `client_reply_draft`，客户回复草稿。
- [ ] 客户回复草稿必须标记为 `requires_human_approval`。

### 交付规划 Agent

- [ ] 输入：已批准的 Proposal。
- [ ] 输出：实施任务计划、时间线、依赖、测试清单。
- [ ] 存储：交付计划生成物。
- [ ] 输出 schema：
  - [ ] `workstreams`，工作流。
  - [ ] `week_1_tasks`，第一周任务。
  - [ ] `dependencies`，依赖。
  - [ ] `risks`，风险。
  - [ ] `test_plan`，测试计划。
  - [ ] `handoff_notes`，交付说明。
- [ ] 只有 Proposal Agent 输出被批准后才能运行。

### 质量审核 Agent

- [ ] 输入：任意生成物。
- [ ] 输出：质量评分、风险说明、重写建议、审批建议。
- [ ] 存储：审核生成物和决策项。
- [ ] 输出 schema：
  - [ ] `quality_score`，质量分。
  - [ ] `clarity_issues`，表达清晰度问题。
  - [ ] `overclaim_risks`，过度承诺风险。
  - [ ] `missing_business_context`，缺失业务上下文。
  - [ ] `security_or_privacy_notes`，安全或隐私说明。
  - [ ] `recommended_action`，建议动作。
- [ ] 必须标记夸大说法。
- [ ] 必须标记未经批准的对客表达。

## 前端实现拆解

### 应用结构

- [ ] 创建 `frontend/` 应用。
- [ ] 添加 `/` 公开官网路由。
- [ ] 添加 `/dashboard` 私有后台路由。
- [ ] 添加 `/dashboard/leads/[id]` 线索详情路由。
- [ ] 本周不创建 `/dashboard/artifacts/[id]` 独立路由；生成物详情在 `/dashboard/leads/[id]` 内展示。
- [ ] 添加共享布局。
- [ ] 添加全局样式和设计 token。

### 组件列表

- [ ] `SiteHeader`，官网头部。
- [ ] `SiteFooter`，官网底部。
- [ ] `HeroSection`，首屏。
- [ ] `PainPointsSection`，痛点区块。
- [ ] `ServicesSection`，服务区块。
- [ ] `MethodSection`，方法论区块。
- [ ] `AgentBenchSection`，Agent 团队区块。
- [ ] `AssuranceSection`，交付保障区块。
- [ ] `CaseStudySection`，案例区块。
- [ ] `LeadIntakeForm`，线索提交表单。
- [ ] `DashboardShell`，后台外壳。
- [ ] `LeadInbox`，线索收件箱。
- [ ] `LeadDetailHeader`，线索详情头部。
- [ ] `DiagnosisPanel`，诊断摘要面板。
- [ ] `DecisionQueue`，决策队列。
- [ ] `ArtifactList`，生成物列表。
- [ ] `ArtifactViewer`，生成物查看器。
- [ ] `StatusBadge`，状态徽章。
- [ ] `EmptyState`，空状态。
- [ ] `ErrorState`，错误状态。
- [ ] `LoadingState`，加载状态。

### 前端 API Client

- [ ] `createLead(payload)`，创建线索。
- [ ] `listLeads(filters)`，查询线索列表。
- [ ] `getLead(id)`，获取线索详情。
- [ ] `updateLead(id, patch)`，更新线索。
- [ ] `runDiagnosis(leadId)`，运行诊断。
- [ ] `runProposal(leadId)`，运行 Proposal。
- [ ] `listArtifacts(leadId)`，查询线索生成物。
- [ ] `getArtifact(id)`，获取生成物详情。
- [ ] `approveDecision(id)`，批准决策。
- [ ] `deferDecision(id)`，暂缓决策。
- [ ] `requestRewrite(id, note)`，要求重写。

### 前端校验

- [ ] 公司或项目必填。
- [ ] 业务问题必填并有最小长度。
- [ ] 期望结果必填。
- [ ] 真实提交时联系方式必填。
- [ ] 预算和时间为可选。
- [ ] Honeypot 隐藏字段必须为空。

### 前端测试

- [ ] 公开页面能渲染。
- [ ] 线索表单能校验必填字段。
- [ ] 线索表单能调用 API 并展示成功状态。
- [ ] 后台列表能展示空状态。
- [ ] 后台列表能展示线索。
- [ ] 线索详情能展示生成物和决策项。
- [ ] 审批动作能更新 UI 状态。

## 后端实现拆解

### 文件结构

- [ ] `backend/app/main.py`。
- [ ] `backend/app/config.py`。
- [ ] `backend/app/db.py`。
- [ ] `backend/app/models.py`。
- [ ] `backend/app/schemas.py`。
- [ ] `backend/app/api/leads.py`。
- [ ] `backend/app/api/agents.py`。
- [ ] `backend/app/api/decisions.py`。
- [ ] `backend/app/api/artifacts.py`。
- [ ] `backend/app/services/leads.py`。
- [ ] `backend/app/services/agent_workflow.py`。
- [ ] `backend/app/services/llm.py`。
- [ ] `backend/app/services/artifacts.py`。
- [ ] `backend/app/services/decisions.py`。
- [ ] `backend/app/prompts/*.md`。
- [ ] `backend/tests/`。

### 数据模型字段

- [ ] Lead，线索：
  - [ ] id。
  - [ ] company，公司。
  - [ ] contact_name，联系人。
  - [ ] contact_method，联系方式。
  - [ ] problem，业务问题。
  - [ ] desired_outcome，期望结果。
  - [ ] company_size，公司规模。
  - [ ] budget_range，预算范围。
  - [ ] timeline，时间计划。
  - [ ] status，状态。
  - [ ] created_at。
  - [ ] updated_at。
- [ ] Artifact，生成物：
  - [ ] id。
  - [ ] lead_id。
  - [ ] type，类型。
  - [ ] title，标题。
  - [ ] content_markdown，Markdown 内容。
  - [ ] content_json，结构化内容。
  - [ ] model，模型名称。
  - [ ] prompt_version，prompt 版本。
  - [ ] requires_approval，是否需要审批。
  - [ ] approved_at。
  - [ ] created_at。
- [ ] AgentTask，Agent 任务：
  - [ ] id。
  - [ ] lead_id。
  - [ ] agent_name。
  - [ ] status。
  - [ ] input_json。
  - [ ] output_json。
  - [ ] error_message。
  - [ ] started_at。
  - [ ] completed_at。
- [ ] Decision，决策项：
  - [ ] id。
  - [ ] lead_id。
  - [ ] artifact_id。
  - [ ] question，待决策问题。
  - [ ] recommendation，建议。
  - [ ] status。
  - [ ] operator_note，人工备注。
  - [ ] created_at。
  - [ ] resolved_at。
- [ ] AuditLog，审计日志：
  - [ ] id。
  - [ ] lead_id。
  - [ ] actor，操作者。
  - [ ] action，动作。
  - [ ] details_json。
  - [ ] created_at。

### 后端测试

- [ ] 测试策略：
  - [ ] repository、service、agent workflow 采用 TDD。
  - [ ] API endpoint 在实现时同步补测试。
  - [ ] LLM 相关测试全部默认使用 mock provider。
  - [ ] 真实 LLM provider 只做手工 smoke test，不进入默认 CI。
- [ ] 健康检查 endpoint 测试。
- [ ] 创建线索测试。
- [ ] 线索校验测试。
- [ ] 查询线索列表测试。
- [ ] 查询线索详情测试。
- [ ] 使用 mock LLM 运行诊断测试。
- [ ] 生成物持久化测试。
- [ ] 决策项创建测试。
- [ ] 批准决策测试。
- [ ] LLM 失败时创建 failed task 测试。
- [ ] 公开 API 未认证时不能访问后台数据测试。

## 前后端联调清单

### API Contract

- [ ] 创建 `docs/api-contract.md`。
- [ ] 写清楚 `POST /api/v1/leads` 请求和响应。
- [ ] 写清楚 `GET /api/v1/leads` 请求和响应。
- [ ] 写清楚 `GET /api/v1/leads/{lead_id}` 请求和响应。
- [ ] 写清楚 `POST /api/v1/leads/{lead_id}/run-diagnosis` 请求和响应。
- [ ] 写清楚 artifact、decision、agent task 的状态枚举。
- [ ] 统一错误响应格式：
  - [ ] `code`。
  - [ ] `message`。
  - [ ] `details`。
  - [ ] `request_id`。

### 第一次联调：线索提交

- [ ] 前端填写公开表单。
- [ ] 后端创建 Lead。
- [ ] 前端展示成功状态。
- [ ] 后台列表出现新线索。
- [ ] 刷新页面后线索仍存在。
- [ ] 失败时公开页面展示温和错误，不暴露后端细节。

### 第二次联调：诊断工作流

- [ ] 后台进入线索详情。
- [ ] 点击运行诊断。
- [ ] 后端创建 AgentTask。
- [ ] mock LLM provider 返回诊断结果。
- [ ] 后端创建 diagnosis artifact。
- [ ] 后端创建等待人工审批的 decision。
- [ ] 前端展示 artifact、decision 和 task 状态。

### 第三次联调：审批和 Proposal

- [ ] 操作员批准诊断结果。
- [ ] 操作员运行 Proposal。
- [ ] 后端创建 proposal artifact。
- [ ] 前端展示客户回复草稿，并标记需要人工审批。
- [ ] 操作员复制已审批内容。
- [ ] AuditLog 记录审批动作。

## 验收标准

- [ ] 访问者能在首屏理解 ChenForge AI 的价值。
- [ ] 访问者能提交一个业务问题。
- [ ] 线索能保存到后端。
- [ ] 后台能看到线索。
- [ ] 操作员能运行诊断。
- [ ] 生成的诊断摘要能保存为生成物。
- [ ] 操作员能批准或暂缓下一步动作。
- [ ] 网站在移动端和桌面端都能正常使用。
- [ ] 前端代码不暴露 LLM secret。
- [ ] README 说明本地启动方式。

## 风险

- 范围膨胀成完整 SaaS 产品。
- 前端打磨占用太多后端时间。
- LLM 输出太空泛，不能真正服务咨询场景。
- 因为是 MVP 而跳过认证和安全边界。
- 官网访客到咨询转化路径不够清晰。

## 已做决策

- 从一条高价值流程开始：线索提交 -> 诊断摘要 -> PoC Proposal。
- 把人工审批作为产品概念的一等公民。
- 优先做克制、可信的 ToB 门户，不做炫技型 AI 页面。
- 本地使用 SQLite，同时保持模型字段、枚举和 repository 边界与 Postgres 兼容。
