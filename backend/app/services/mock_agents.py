"""Deterministic mock agents for testing the Agent + Decision loop."""

OVERPROMISE_KEYWORDS = ["保证", "一定", "免费", "确定上线"]
SAFETY_PHRASES = ["需要确认", "建议先澄清", "PoC 验证", "以验收标准为准"]


def generate_sales_reply(context: dict) -> dict:
    """Generate a safe customer reply draft and discovery questions from context.

    Returns dict with: customer_reply_draft (str), discovery_questions (list[str]).
    """
    customer = context.get("customer")
    contact = context.get("primary_contact")
    opp = context.get("opportunity")

    company_name = customer.name if customer else "贵公司"
    contact_name = contact.name if contact and contact.name else "负责人"
    problem = opp.problem_summary if opp and opp.problem_summary else "您提到的业务需求"
    outcome = opp.desired_outcome if opp and opp.desired_outcome else "AI 落地"

    reply = (
        f"{contact_name} 您好，\n\n"
        f"感谢 {company_name} 的信任。根据我们目前的理解，"
        f"您这边的核心痛点是：{problem}。\n\n"
        f"针对「{outcome}」这个目标，我们建议先通过一个 PoC 验证来确认技术可行性和业务价值，"
        f"再根据验证结果制定后续交付计划。具体方案和周期需要在澄清需求后以验收标准为准。\n\n"
        f"以下是我们建议先澄清的几个问题，方便的话可以先看一下。"
    )

    discovery_questions = [
        f"目前 {company_name} 内部谁负责主导这个项目的评估和决策？",
        f"对于「{outcome}」，您这边有没有已经试用过的工具或方案？效果如何？",
        f"如果做 PoC 验证，您觉得什么样的结果算成功？（例如：准确率、响应时间、人工节省）",
        f"有没有时间上的硬性要求，比如某个节点之前必须上线？",
        f"数据方面，目前是否有整理好的历史数据或知识库可以用于 PoC？",
    ]

    return {
        "customer_reply_draft": reply,
        "discovery_questions": discovery_questions,
    }


def review_sales_reply(reply_text: str) -> dict:
    """Review a sales reply draft for overpromise and unclear scope.

    Returns dict with: risk_level (low|medium|high), risk_flags (list),
    summary (str), recommendation (str).
    """
    risk_flags = []

    for kw in OVERPROMISE_KEYWORDS:
        if kw in reply_text:
            risk_flags.append({"type": "overpromise", "keyword": kw})

    has_safety = any(phrase in reply_text for phrase in SAFETY_PHRASES)
    if not has_safety:
        risk_flags.append({"type": "unclear_scope", "detail": "缺少安全表达（需要确认/建议先澄清/PoC 验证/以验收标准为准）"})

    if not risk_flags:
        risk_level = "low"
        summary = "未发现过度承诺或范围不清的风险。"
        recommendation = "approve"
    else:
        has_overpromise = any(f["type"] == "overpromise" for f in risk_flags)
        risk_level = "high" if has_overpromise else "medium"
        summary = f"发现 {len(risk_flags)} 个风险点。"
        recommendation = "review_before_approve"

    return {
        "risk_level": risk_level,
        "risk_flags": risk_flags,
        "summary": summary,
        "recommendation": recommendation,
    }


def generate_proposal_draft(context: dict) -> dict:
    """Generate a structured PoC proposal draft from opportunity context."""
    customer = context.get("customer")
    opp = context.get("opportunity")
    contact = context.get("primary_contact")
    messages = context.get("messages", [])
    draft = context.get("customer_reply_draft")
    questions = context.get("discovery_questions")

    company = customer.name if customer else "贵公司"
    contact_name = contact.name if contact and contact.name else "负责人"
    problem = opp.problem_summary if opp and opp.problem_summary else "业务需求"
    outcome = opp.desired_outcome if opp and opp.desired_outcome else "AI 落地"

    # Build a simple summary of conversation context
    msg_summary = ""
    if messages:
        recent = messages[-1]
        msg_summary = f"客户最近回复：{recent.body_markdown[:120]}"

    # Build confirmed goals from discovery questions if available
    goals = [outcome]
    if questions and questions.content_json:
        qs = questions.content_json.get("questions", [])
        if qs:
            goals.append(f"已澄清 {len(qs)} 个关键问题")

    risks = [
        "客户数据质量和完整性需要在 PoC 启动前确认。",
        "对接现有系统（如 CRM/ERP）的接口和时间依赖于客户侧的 IT 配合。",
        "PoC 的验收标准需客户与 ChenForge 双方书面确认。",
    ]

    content_markdown = f"""# PoC 方案草案

## 1. 客户背景

{company}（{contact_name}）当前面临的核心痛点是：{problem}

## 2. 已确认目标

{chr(10).join(f'- {g}' for g in goals)}

## 3. 建议 PoC 范围

- 聚焦 {outcome} 的核心场景验证。
- 在受控数据范围内完成一轮完整的 AI 辅助业务流程。
- 输出一份 PoC 验证报告，包含技术可行性、业务价值评估和下一步建议。

## 4. 不包含范围

- 不包含生产环境部署与运维。
- 不包含全量数据迁移。
- 不包含第三方系统深度集成（如 CRM/ERP 接口开发）。
- 不包含后续长期维护和 SLA 承诺。

## 5. 交付物

- PoC 验证环境（ChenForge 提供临时实例）。
- PoC 运行报告（含准确率、响应时间、人工节省等指标）。
- 下一步实施建议。

## 6. 建议时间计划

- 第 1 周：需求确认与数据准备。
- 第 2-3 周：PoC 开发与内部测试。
- 第 4 周：客户验证与报告输出。

（以上时间为初步建议，以双方确认的验收标准为准。）

## 7. 前置假设

- 客户可提供用于 PoC 的历史数据或知识库。
- 客户侧有至少一位对接人可参与需求确认和验证。
- PoC 期间不要求对接生产系统。

## 8. 风险与边界

{chr(10).join(f'- {r}' for r in risks)}

## 9. 需要客户确认的问题

- PoC 的验收标准是什么？（例如：准确率 ≥ X%、响应时间 ≤ Y 秒）
- 是否有明确的上线时间节点？
- 数据是否涉及敏感信息，需要额外的合规处理？
- 是否已有整理好的历史数据或知识库可直接用于 PoC？

## 10. 下一步建议

建议先安排一次需求对齐会议，确认 PoC 范围和验收标准后启动。"""

    content_json = {
        "customer_background": f"{company}，{problem}",
        "confirmed_goals": goals,
        "poc_scope": [f"聚焦 {outcome}", "受控数据范围验证", "输出 PoC 验证报告"],
        "out_of_scope": ["生产环境部署", "全量数据迁移", "第三方系统深度集成", "长期 SLA"],
        "deliverables": ["PoC 验证环境", "PoC 运行报告", "下一步建议"],
        "timeline": ["第1周：需求确认", "第2-3周：开发测试", "第4周：客户验证"],
        "assumptions": ["客户提供历史数据", "客户有对接人", "不要求对接生产系统"],
        "risks": risks,
        "questions_for_customer": [
            "PoC 验收标准是什么？", "是否有上线时间节点？",
            "数据是否涉及敏感信息？", "是否有可用的历史数据或知识库？",
        ],
        "next_step": "安排需求对齐会议，确认 PoC 范围和验收标准",
    }

    return {
        "content_markdown": content_markdown,
        "content_json": content_json,
    }
