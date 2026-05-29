# ADR-004：测试、Mock LLM 与分支策略

## 状态

Accepted

## 背景

MVP 一周内要完成前端、后端、Agent workflow 和联调。如果没有确定性的测试和分支策略，真实 LLM 的随机性、前后端字段漂移和大批量修改会快速放大风险。

## 决策

- 测试策略采用“关键路径 TDD + 页面快速迭代后补测试”。
- 后端 repository、service、Agent workflow、mock LLM provider、审批链路采用 TDD。
- 前端公共官网允许先实现再补测试；线索提交、后台审批和 artifact 展示必须有测试。
- 默认测试只使用 mock LLM provider。
- 真实 LLM provider 只做手工 smoke test，不进入默认测试路径。
- 开发分支使用 `codex/` 前缀。

## Mock LLM Provider

Mock provider 必须满足：

- 实现统一接口 `generate_json(prompt_name, input_payload, output_schema)`。
- 根据 `prompt_name` 返回固定结构。
- 支持成功、非法 JSON、模拟异常、模拟延迟四类模式。
- 不访问网络。
- 不读取真实 LLM key。
- 测试环境默认使用 mock provider。

## 分支

- `codex/chenforge-mvp-shell`
- `codex/chenforge-backend-api`
- `codex/chenforge-dashboard`
- `codex/chenforge-agent-workflow`
- `codex/chenforge-integration-polish`

## 验收

- 后端测试能在无网络、无真实 LLM key 的环境下通过。
- 前端能用 mock/fixture 在后端未完成前开发。
- 第 3 天和第 5 天必须做前后端联调，不把集成风险堆到第 7 天。

