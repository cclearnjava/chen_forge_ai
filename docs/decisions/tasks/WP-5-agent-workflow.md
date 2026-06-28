# WP-5: Agent Workflow — Mock LLM + 5 Agents

- **Goal**: 确定性 mock LLM provider、轻量 workflow runner、5 个 Agent 角色（线索诊断、方案架构、Proposal、交付规划、质量审核）+ intake_response agent。
- **Write set**: `backend/app/services/llm.py`, `backend/app/services/agent_workflow.py`, `backend/app/services/mock_llm.py`, `backend/app/prompts/lead_diagnosis.md`, `backend/app/prompts/solution_architect.md`, `backend/app/prompts/proposal.md`, `backend/app/prompts/delivery_planner.md`, `backend/app/prompts/quality_reviewer.md`, `backend/app/prompts/intake_response.md`, `backend/tests/test_agent_workflow.py`
- **Depends on**: WP-1 (AgentTask, Artifact, Decision models)
- **Parallel with**: WP-2, WP-4
- **Seam owner**: WP-5 负责 AgentTask/Artifact/Decision 的生产端契约，WP-6 消费这些数据
- **Acceptance test**:
  - Mock LLM provider 根据 prompt_name 返回确定性 output_json
  - `POST /api/v1/leads/{id}/run-diagnosis` 触发诊断 Agent，创建 AgentTask(succeeded) + Artifact(diagnosis) + Decision(waiting)
  - `POST /api/v1/leads/{id}/run-proposal` 触发 Proposal Agent
  - `POST /api/v1/leads/{id}/run-intake-response` 触发 intake_response Agent，生成 requirement_summary + customer_reply_draft + proposal_draft
  - Agent 失败时 AgentTask.status = failed，有 error_message
  - 所有 Agent 输出写入 AuditLog
  - 对客 Artifact 的 requires_approval = true
  - 测试在无网络、无真实 LLM key 环境下全部通过
