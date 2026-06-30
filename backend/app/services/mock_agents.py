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
