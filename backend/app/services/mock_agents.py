"""Deterministic mock agents for testing the Agent + Decision loop."""

OVERPROMISE_KEYWORDS = ["保证", "一定", "免费", "确定上线"]
SAFETY_PHRASES = ["需要确认", "建议先澄清", "PoC 验证", "以验收标准为准"]


def generate_sales_reply(context: dict) -> dict:
    """Generate a safe customer reply draft and discovery questions from context.

    Returns dict with: customer_reply_draft (str), discovery_questions (list[str]).

    If the context pack carries matched_services / relevant_knowledge_items / risk_notes,
    the reply reflects them naturally. Only service names and knowledge summaries/titles are
    surfaced — never raw content_markdown or price figures (those must not reach the customer).
    """
    customer = context.get("customer")
    contact = context.get("primary_contact")
    opp = context.get("opportunity")
    matched_services = context.get("matched_services") or []
    knowledge_items = context.get("relevant_knowledge_items") or []
    risk_notes = context.get("risk_notes") or []

    company_name = customer.name if customer else "贵公司"
    contact_name = contact.name if contact and contact.name else "负责人"
    problem = opp.problem_summary if opp and opp.problem_summary else "您提到的业务需求"
    outcome = opp.desired_outcome if opp and opp.desired_outcome else "AI 落地"

    reply = (
        f"{contact_name} 您好，\n\n"
        f"感谢 {company_name} 的信任。根据我们目前的理解，"
        f"您这边的核心痛点是：{problem}。\n\n"
        f"针对「{outcome}」这个目标，我们建议先通过一个 PoC 验证来确认技术可行性和业务价值，"
        f"再根据验证结果制定后续交付计划。具体方案和周期需要在澄清需求后以验收标准为准。"
    )

    # Service capability — reference service names and delivery direction (never prices)
    service_names = [s.get("name") for s in matched_services if s.get("name")][:2]
    if service_names:
        reply += (
            f"\n\n结合我们在「{'」「'.join(service_names)}」方向的交付经验，"
            f"这类需求通常可以从一个范围可控的 PoC 起步，逐步扩展。"
        )

    # Knowledge — weave in experience via summaries/titles (never raw content)
    knowledge_hint = ""
    for it in knowledge_items:
        hint = it.get("summary") or it.get("title")
        if hint:
            knowledge_hint = hint
            break
    if knowledge_hint:
        reply += f"\n\n基于类似项目的经验，我们建议特别关注：{knowledge_hint}。"

    # Risk boundary — cautious phrasing
    if risk_notes:
        reply += (
            f"\n\n需要提前说明的是：{risk_notes[0]}"
            f"，我们会在方案中把边界和前提写清楚，避免过度承诺。"
        )

    reply += "\n\n以下是我们建议先澄清的几个问题，方便的话可以先看一下。"

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


def generate_proposal_followup_reply(context: dict) -> dict:
    """Generate a follow-up reply draft responding to client proposal feedback."""
    fb = context.get("latest_proposal_feedback")
    proposal = context.get("approved_proposal", {})
    customer = context.get("customer")
    company = customer.name if customer else "贵公司"

    feedback_text = fb.body_markdown if fb else "客户反馈"
    title = proposal.get("opportunity_title", "PoC 方案")

    content_markdown = f"""# Proposal Follow-up 回复草稿

## 1. 对客户反馈的确认

感谢 {company} 对「{title}」的反馈。我们已认真阅读并就您关心的要点进行了分析。

## 2. 针对异议的回应

针对您的反馈（{feedback_text[:80]}...），我们理解您的核心顾虑。建议在接下来的一轮沟通中聚焦可调整的范围和交付节奏，以同时回应您的关注点与项目可行性。

## 3. 可调整的 PoC 范围

- 可以根据您的反馈适当缩小第一期 PoC 的交付范围，优先验证核心价值。
- 具体调整需要双方在会议上确认，以验收标准为准。

## 4. 需要客户确认的问题

- 您在反馈中最关心的优先事项是哪一项？（预算控制 / 交付速度 / 功能广度）
- 是否可以在近期安排一次 30 分钟的对齐会议？
- 是否有其他决策人需要参与后续讨论？

## 5. 下一步建议

建议本周内安排一次需求对齐会议，聚焦 PoC 范围调整和下一步时间线。"""

    content_json = {
        "acknowledgement": f"已收到 {company} 对 {title} 的反馈",
        "objection_response": "将在对齐会议中讨论范围调整",
        "scope_adjustment": ["优先验证核心价值", "缩小第一期交付范围"],
        "questions_for_customer": ["最关心的优先事项", "是否可安排对齐会议", "是否有其他决策人"],
        "next_step": "本周安排需求对齐会议",
    }
    return {"content_markdown": content_markdown, "content_json": content_json}


def generate_objection_analysis(context: dict) -> dict:
    """Analyze client objections to the proposal."""
    fb = context.get("latest_proposal_feedback")
    proposal = context.get("approved_proposal", {})
    feedback_text = fb.body_markdown if fb else "客户反馈"
    risk_level = "medium"
    if "预算" in feedback_text or "价格" in feedback_text:
        risk_level = "medium"
    if "不接受" in feedback_text or "不做了" in feedback_text:
        risk_level = "high"

    content_markdown = f"""# 异议分析

## 1. 客户核心顾虑

基于客户反馈，主要顾虑集中在：{feedback_text[:100]}

## 2. 风险等级

**{risk_level}** — {"需要重点关注并及时回应" if risk_level != "low" else "属于正常商务沟通范围"}

## 3. 可让步空间

- PoC 范围可根据客户反馈适当调整，缩小第一期交付物但保留核心验证能力。
- 时间计划建议保持弹性，以双方确认的验收标准为准。

## 4. 不应承诺的内容

- 不应承诺免费交付或大幅降价。
- 不应承诺跳过 PoC 直接进入生产部署。
- 不应承诺不经验收标准确认的上线日期。

## 5. 建议沟通策略

以"理解顾虑 + 提供调整方案 + 邀请对齐会议"为主线推进。"""

    content_json = {
        "core_concern": feedback_text[:100],
        "risk_level": risk_level,
        "concession_space": ["缩小范围", "弹性时间"],
        "no_commitments": ["免费交付", "跳过PoC", "确定上线日期"],
        "strategy": "理解顾虑 + 调整方案 + 对齐会议",
    }
    return {"content_markdown": content_markdown, "content_json": content_json}


def generate_next_step_recommendation(context: dict) -> dict:
    """Generate next-step recommendations after proposal follow-up."""
    content_markdown = """# 下一步建议

## 建议动作

- 审批本回复草稿后，将内容发送给客户。
- 同时准备一份调整后的 PoC 范围说明，供对齐会议使用。

## 建议会议/沟通安排

- 本周内安排一次 30 分钟的视频或电话会议。
- 会议议程：确认调整后的 PoC 范围、时间线和验收标准。

## 需要准备的材料

- 当前已批准 Proposal PDF。
- 调整后的 PoC 范围草案（可基于本次反馈更新 Proposal）。

## Opportunity 更新建议

- 将 Opportunity 移至 negotiation 阶段。
- 更新 next_step 为 "Send follow-up reply and schedule alignment meeting"。
"""

    content_json = {
        "actions": ["审批并发送回复", "准备调整后范围说明"],
        "meeting": "本周 30 分钟对齐会议",
        "materials": ["Proposal PDF", "调整后范围草案"],
        "opportunity_update": {"stage": "negotiation", "next_step": "Send follow-up and schedule meeting"},
    }
    return {"content_markdown": content_markdown, "content_json": content_json}


def generate_quote_draft(context: dict) -> dict:
    proposal = context.get("approved_proposal", {})
    fb = context.get("latest_proposal_feedback")
    fb_text = fb.body_markdown if fb else "客户反馈"
    title = proposal.get("opportunity_title", "PoC")
    content_markdown = f"""# Quote Draft

## 建议价格区间
**CNY 30,000 - 50,000**
（草案需负责人确认后才可对客发送，不构成最终报价承诺。）

## 定价假设
- 第一期 PoC 聚焦核心场景验证。
- 客户提供必要数据和对接人。
- 不包含第三方系统集成和长期 SLA。

## 建议付款节点
- 启动：30%
- PoC 中期评审通过：40%
- 最终验收通过：30%"""
    content_json = {"title": "PoC Quote Draft", "currency": "CNY", "price_range": "30000-50000", "pricing_assumptions": ["第一期 PoC 聚焦核心场景", "客户提供数据和对接人", "不含第三方集成和长期SLA"], "payment_milestones": ["启动30%", "中期40%", "验收30%"], "validity_note": "草案需负责人确认后才可对客发送"}
    return {"content_markdown": content_markdown, "content_json": content_json}


def generate_sow_draft(context: dict) -> dict:
    proposal = context.get("approved_proposal", {})
    title = proposal.get("opportunity_title", "PoC")
    content_markdown = f"""# Statement of Work Draft

## 项目名称
{title} — PoC 阶段

## 范围
- 聚焦 {title} 的核心场景验证。
- 在受控数据范围内完成 AI 辅助业务流程。
- 输出 PoC 验证报告。

## 不包含范围
- 生产环境部署与运维。
- 全量数据迁移。
- 第三方系统深度集成。
- 后续长期维护和 SLA。

## 交付物
- PoC 验证环境。
- PoC 运行报告。
- 下一步实施建议。

## 建议时间线
- 第 1 周：需求确认与数据准备。
- 第 2-3 周：PoC 开发与内部测试。
- 第 4 周：客户验证与报告输出。

## 验收标准
- PoC 达到双方约定的核心指标。

## 客户责任
- 提供用于 PoC 的历史数据或知识库。
- 安排至少一位业务对接人。

## 假设条件
- 客户数据质量和完整性满足 PoC 最低要求。
- PoC 期间不要求对接生产系统。"""
    content_json = {"title": "Statement of Work Draft", "scope": ["核心场景验证", "PoC 验证报告"], "out_of_scope": ["生产部署", "全量数据迁移", "第三方深度集成", "长期SLA"], "deliverables": ["PoC 验证环境", "PoC 运行报告", "下一步建议"], "timeline": ["第1周需求确认", "第2-3周开发测试", "第4周客户验证"], "acceptance_criteria": ["核心指标达标"], "customer_responsibilities": ["提供数据", "安排对接人"], "assumptions": ["数据质量满足要求", "不要求对接生产系统"]}
    return {"content_markdown": content_markdown, "content_json": content_json}


def generate_commercial_review(context: dict) -> dict:
    content_markdown = """# Commercial Review

## 风险等级
**medium** — 建议负责人确认报价边界和 SOW 范围后再推进客户确认。

## 风险提示
- 价格为草案，不构成最终报价承诺。
- 付款节点为建议，需双方书面确认。
- 范围以双方确认的 SOW 为准。
- 第三方系统集成默认不包含。

## 建议下一步
负责人确认报价和 SOW 边界后，准备客户确认材料。"""
    content_json = {"risk_level": "medium", "risk_flags": ["价格草案", "付款节点建议", "范围边界", "第三方系统默认不包含"], "approval_notes": ["需负责人审批", "审批不代表报价生效"], "recommended_next_step": "负责人确认报价和SOW边界后，准备客户确认材料"}
    return {"content_markdown": content_markdown, "content_json": content_json}
