"""LLM Provider interface and implementations."""

from abc import ABC, abstractmethod
from app.config import settings


class LLMProvider(ABC):
    @abstractmethod
    def generate_json(self, prompt_name: str, input_payload: dict, output_schema: dict) -> dict:
        ...


class MockLLMProvider(LLMProvider):
    """Deterministic mock provider for testing and development."""

    def __init__(self, mode: str = "success"):
        self.mode = mode  # success | json_error | exception | delay

    def generate_json(self, prompt_name: str, input_payload: dict, output_schema: dict) -> dict:
        if self.mode == "exception":
            raise RuntimeError("Mock LLM exception")

        if self.mode == "delay":
            import time
            time.sleep(1)

        func = _mock_responses.get(prompt_name)
        if func is None:
            response = {"message": f"No mock response for prompt: {prompt_name}"}
        else:
            response = func(input_payload) if callable(func) else func

        if self.mode == "json_error":
            return {"_raw": "not valid json {{"}

        return response


def _diagnosis_response(payload: dict) -> dict:
    problem = payload.get("problem", "")
    return {
        "pain_summary": f"客户当前主要痛点是：{problem[:60]}...",
        "business_goal": "通过AI自动化降低重复性工作的人工成本",
        "workflow_candidates": ["智能客服 FAQ", "销售资料自动整理", "运营日报自动生成"],
        "recommended_first_poc": payload.get("desired_outcome", "企业知识库 / RAG 问答"),
        "suitability_score": 82,
        "risk_flags": ["现有资料质量未知", "权限边界需与客户确认", "历史数据格式可能不统一"],
        "missing_questions": [
            "现有知识库资料存放在哪里？格式是什么？",
            "谁负责审核AI生成的回复内容？",
            "预期每天处理多少问答量？"
        ],
        "next_step_recommendation": "建议先安排一次45分钟的业务流程诊断沟通",
    }


def _architecture_response(payload: dict) -> dict:
    return {
        "workflow_steps": ["用户提问", "RAG检索", "答案生成", "人工审核", "发布回复"],
        "agent_responsibilities": ["检索Agent：从知识库匹配相关文档", "生成Agent：基于检索结果生成答案草稿", "审核Agent：检查答案质量和合规性"],
        "required_data_sources": ["企业知识库文档（FAQ/制度/产品资料）", "历史客服对话记录", "权限和审批规则配置"],
        "required_tools": ["向量数据库（ChromaDB或Milvus）", "Embedding模型", "后台审核界面"],
        "human_approval_gates": ["回复内容审核", "新知识条目发布", "敏感问题升级"],
        "security_boundaries": ["Agent只能读取指定知识库", "不能直接操作生产数据库", "所有对外回复必须人工确认"],
        "integration_notes": "建议初期作为独立服务运行，通过API与现有客服系统对接",
        "scope_size": "small",
        "not_suitable_for_automation": None,
    }


def _proposal_response(payload: dict) -> dict:
    return {
        "proposal_summary": "建议从企业知识库问答PoC开始，用2-3周验证价值后再扩展",
        "discovery_agenda": [
            "梳理现有知识资料来源和格式",
            "定义TOP 20高频问题",
            "确认审核流程和责任人",
            "确定效果评估指标"
        ],
        "poc_scope": [
            "知识资料导入和向量化",
            "RAG问答原型（内部使用）",
            "后台审核界面",
            "效果追踪看板"
        ],
        "milestones": [
            "第1周：业务诊断 + 资料梳理 + 技术方案确认",
            "第2周：原型开发 + 内部测试",
            "第3-4周：试运行 + 效果评估"
        ],
        "acceptance_metrics": [
            "TOP 20问题回答准确率 ≥ 85%",
            "人工审核通过率趋势",
            "平均回复时间降低比例",
            "用户满意度评分"
        ],
        "out_of_scope": [
            "直接替代人工客服",
            "自动对外发送消息（需人工确认）",
            "对接企业微信/飞书客户联系（后续阶段）"
        ],
        "client_reply_draft": (
            "您好，感谢您对ChenForge AI的信任。\n\n"
            "根据您描述的业务问题，我们建议先从一个边界清晰的知识库问答PoC开始。\n\n"
            "这个PoC会帮您验证三件事：\n"
            "1. AI能否准确理解您的业务知识并给出有用回复\n"
            "2. 人工审核流程能否有效控制质量\n"
            "3. 实际使用中能节省多少人工时间\n\n"
            "下一步建议安排一次45分钟的业务流程诊断沟通，我们会准备好初步的问题清单。\n\n"
            "有任何问题随时联系。"
        ),
    }


def _intake_response(payload: dict) -> dict:
    problem = payload.get("problem", "")
    company = payload.get("company", "")
    return {
        "requirement_summary": {
            "business_context": f"客户{company}希望解决以下问题：{problem[:80]}...",
            "main_problem": problem[:100],
            "likely_ai_scenarios": ["RAG知识库问答", "业务流程Agent", "数据分析看板"],
            "missing_information": ["现有系统和技术栈", "数据规模和格式", "团队技术能力"],
        },
        "customer_reply_draft": {
            "subject": f"ChenForge AI：关于您AI落地需求的初步理解",
            "body_markdown": (
                f"您好，\n\n"
                f"我们已经收到您提交的关于「{problem[:40]}...」的业务需求。\n\n"
                f"基于初步分析，您的场景在AI自动化适配度上评分较高。"
                f"我们建议从以下方向切入：\n\n"
                f"- 企业知识库 / RAG 问答\n"
                f"- 业务流程 Agent\n\n"
                f"下一步建议安排一次45分钟的业务诊断沟通，"
                f"我们会准备好针对您行业和场景的具体问题清单。\n\n"
                f"期待与您进一步交流。"
            ),
        },
        "proposal_draft": {
            "recommended_first_poc": payload.get("desired_outcome", "企业知识库 / RAG 问答"),
            "scope": ["业务诊断", "资料梳理", "原型开发", "效果验证"],
            "timeline": "建议2-3周完成PoC验证",
            "risks": ["需求细节需进一步确认", "与现有系统集成方式待定"],
            "next_step": "安排45分钟诊断沟通",
        },
    }


def _quality_review(payload: dict) -> dict:
    return {
        "quality_score": 78,
        "clarity_issues": ["客户回复草稿中可以更具体地提到行业场景"],
        "overclaim_risks": ["避免使用'保证'、'一定'等绝对化表述"],
        "missing_business_context": ["客户团队规模和技术能力未确认"],
        "security_or_privacy_notes": ["注意不要暴露内部技术细节"],
        "recommended_action": "approve_with_minor_edits",
    }


_mock_responses = {
    "lead_diagnosis": _diagnosis_response,
    "solution_architect": _architecture_response,
    "proposal": _proposal_response,
    "intake_response": _intake_response,
    "quality_reviewer": _quality_review,
    "delivery_planner": lambda p: {
        "workstreams": ["数据准备", "模型搭建", "应用开发", "测试验证", "上线部署"],
        "week_1_tasks": ["环境搭建", "数据导入", "基准测试"],
        "dependencies": ["知识库资料完成整理", "审核流程确认"],
        "risks": ["资料整理可能超预期", "Embedding效果需验证"],
        "test_plan": ["单元测试", "检索准确性测试", "端到端流程测试"],
        "handoff_notes": "所有代码和配置纳入版本管理，提供部署文档",
    },
}


def get_llm_provider() -> LLMProvider:
    if settings.llm_provider == "mock":
        return MockLLMProvider()
    # Future: OpenAI-compatible provider
    return MockLLMProvider()
