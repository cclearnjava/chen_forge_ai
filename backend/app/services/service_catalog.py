"""Service Catalog — workspace-scoped service management."""

from sqlalchemy.orm import Session
from app.models import Service, ServiceStatus


def list_services(db: Session, workspace_id: str, status: str = None, q: str = None) -> list:
    query = db.query(Service).filter(Service.workspace_id == workspace_id)
    if status:
        query = query.filter(Service.status == status)
    if q:
        query = query.filter(Service.name.ilike(f"%{q}%"))
    return query.order_by(Service.sort_order, Service.name).all()


def get_service_or_none(db: Session, workspace_id: str, service_id: str) -> Service | None:
    return db.query(Service).filter(
        Service.id == service_id, Service.workspace_id == workspace_id,
    ).first()


def create_service(db: Session, workspace_id: str, data: dict) -> Service:
    svc = Service(workspace_id=workspace_id, **data)
    db.add(svc)
    db.flush()
    return svc


def update_service(db: Session, workspace_id: str, service_id: str, data: dict) -> Service | None:
    svc = get_service_or_none(db, workspace_id, service_id)
    if not svc:
        return None
    for k, v in data.items():
        if v is not None and hasattr(svc, k):
            setattr(svc, k, v)
    db.flush()
    return svc


def set_service_status(db: Session, workspace_id: str, service_id: str, status: ServiceStatus) -> Service | None:
    svc = get_service_or_none(db, workspace_id, service_id)
    if not svc:
        return None
    svc.status = status
    db.flush()
    return svc


DEFAULT_SERVICES = [
    {"name": "AI Agent 落地咨询", "slug": "ai-agent-consulting", "positioning": "为企业梳理 AI Agent 落地场景，设计 Agent 流程与架构，输出可执行 PoC 方案", "target_customer": "希望用 AI Agent 替代重复人工流程的中型企业和成长型团队", "pain_points_json": ["人工流程效率低", "缺乏 AI 落地经验", "不确定从哪里开始"], "outcomes_json": ["AI 落地诊断报告", "Agent 流程设计图", "PoC 方案与路线图"], "required_inputs_json": ["当前业务流程描述", "痛点和期望目标", "数据样本或系统访问权限"], "typical_duration": "2-4 周", "price_min": 30000, "price_max": 80000, "risk_notes": "如果客户没有任何内部数据或流程文档，建议先从诊断版开始，不要直接承诺完整系统交付"},
    {"name": "RAG 知识库系统", "slug": "rag-knowledge-base", "positioning": "基于客户私有知识库构建 RAG 问答系统，让员工和客户能自助查询", "target_customer": "拥有大量文档、制度、FAQ、产品手册的企业", "pain_points_json": ["信息分散在多个系统", "员工重复回答相同问题", "知识传承依赖老员工"], "outcomes_json": ["RAG 原型系统", "知识库结构设计", "PoC 验收报告"], "required_inputs_json": ["现有文档、FAQ、制度文件", "典型用户问题样例", "期望的问答准确率"], "typical_duration": "4-8 周", "price_min": 50000, "price_max": 150000, "risk_notes": "如果客户文档质量差、格式混乱或数量极少，RAG 效果会受限，需提前说明"},
    {"name": "ChatBI 数据问答", "slug": "chatbi-data-qa", "positioning": "让管理层用自然语言查询经营数据，替代手工报表和重复取数", "target_customer": "管理层需要快速获取经营数据但不懂 SQL 的企业", "pain_points_json": ["报表依赖人工整理", "数据口径不一致", "管理层无法自助查数"], "outcomes_json": ["ChatBI 原型系统", "数据源接入与口径梳理", "常用问题与回答样例集"], "required_inputs_json": ["数据库或数据仓库访问权限", "常用经营问题列表", "数据字典或表结构说明"], "typical_duration": "6-10 周", "price_min": 80000, "price_max": 200000, "risk_notes": "如果数据质量差、口径混乱或缺乏数据字典，ChatBI 效果会打折扣"},
    {"name": "企业数据治理", "slug": "data-governance", "positioning": "帮助企业建立数据标准、质量规则和治理流程，为 AI 应用打基础", "target_customer": "数据分散、口径不统一、准备上 AI 的中大型企业", "pain_points_json": ["数据质量不可信", "缺乏统一数据标准", "AI 项目因数据问题延期"], "outcomes_json": ["数据治理诊断报告", "数据标准与质量规则", "治理流程与组织建议"], "required_inputs_json": ["现有数据资产清单", "核心业务数据样例", "数据使用痛点与期望"], "typical_duration": "8-12 周", "price_min": 100000, "price_max": 300000, "risk_notes": "数据治理是长期工程，PoC 阶段只输出标准和规则，不承诺全企业落地"},
    {"name": "MLOps 平台建设", "slug": "mlops-platform", "positioning": "为企业搭建模型训练、部署、监控和迭代的 MLOps 基础设施", "target_customer": "已经有数据团队、需要把 AI 模型工程化的企业", "pain_points_json": ["模型上线慢", "实验管理混乱", "缺乏模型监控"], "outcomes_json": ["MLOps 平台架构设计", "核心流水线原型", "部署与运维手册"], "required_inputs_json": ["当前模型和实验管理方式", "技术栈和基础设施信息", "期望的 MLOps 能力"], "typical_duration": "8-16 周", "price_min": 120000, "price_max": 400000, "risk_notes": "如果企业没有内部数据团队或已有成熟 MLOps 平台，建议先做诊断评估"},
]


def ensure_default_services(db: Session, workspace_id: str) -> list[Service]:
    """Idempotent: seed default services if none exist. Returns list of services."""
    existing = db.query(Service).filter(Service.workspace_id == workspace_id).first()
    if existing:
        return list_services(db, workspace_id)
    services = []
    for i, d in enumerate(DEFAULT_SERVICES):
        svc = Service(workspace_id=workspace_id, status=ServiceStatus.active, sort_order=i, **d)
        db.add(svc)
        services.append(svc)
    db.flush()
    return services
