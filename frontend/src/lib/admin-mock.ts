export type Stage =
  | "lead"
  | "qualified"
  | "proposal"
  | "negotiation"
  | "won"
  | "lost"
  | "archived";

export type MessageType = "customer" | "owner" | "agent" | "system";

export type ConversationMessage = {
  id: string;
  senderType: MessageType;
  senderLabel: string;
  source: "lead_form" | "manual" | "agent_draft" | "system";
  body: string;
  createdAt: string;
};

export type Opportunity = {
  id: string;
  title: string;
  stage: Stage;
  companyName: string;
  ownerEmail: string;
  industry: string;
  companySize: string;
  contactName: string;
  contactMethod: string;
  desiredOutcome: string;
  problemSummary: string;
  budgetRange: string;
  estimatedValue: string;
  probability: number;
  nextStep: string;
  updatedAt: string;
  messages: ConversationMessage[];
};

export const opportunities: Opportunity[] = [
  {
    id: "opp-rag-retail",
    title: "企业知识库 / RAG 问答 PoC",
    stage: "qualified",
    companyName: "陈记连锁门店",
    ownerEmail: "chen@example.com",
    industry: "连锁零售",
    companySize: "50-200",
    contactName: "陈总",
    contactMethod: "wechat: chen",
    desiredOutcome: "把客服、销售、门店 SOP 统一进企业知识库",
    problemSummary: "客服重复问答多，门店销售资料整理慢，老板希望先从一个低风险流程验证 AI Agent 价值。",
    budgetRange: "3-5w",
    estimatedValue: "¥48,000",
    probability: 62,
    nextStep: "确认知识库资料范围，并生成第一轮澄清问题",
    updatedAt: "今天 10:42",
    messages: [
      {
        id: "msg-1",
        senderType: "customer",
        senderLabel: "陈总",
        source: "lead_form",
        body: "我们门店客服每天都在重复回答会员权益、退换货、活动规则，销售也经常找不到最新资料。希望先做一个内部问答 PoC。",
        createdAt: "09:18",
      },
      {
        id: "msg-2",
        senderType: "system",
        senderLabel: "ChenForge",
        source: "system",
        body: "系统已从 Lead 自动生成 Customer、Conversation 和 Opportunity。",
        createdAt: "09:19",
      },
      {
        id: "msg-3",
        senderType: "agent",
        senderLabel: "Sales Agent",
        source: "agent_draft",
        body: "建议先确认三类资料：客服 FAQ、门店 SOP、销售活动资料。随后用 30 天 PoC 验证检索命中率和人工节省时间。",
        createdAt: "09:26",
      },
    ],
  },
  {
    id: "opp-chatbi-manufacturing",
    title: "ChatBI 经营问数助手",
    stage: "proposal",
    companyName: "华东精密制造",
    ownerEmail: "ops@example.com",
    industry: "制造业",
    companySize: "200-500",
    contactName: "运营负责人",
    contactMethod: "email",
    desiredOutcome: "老板能直接问库存、产能、异常订单",
    problemSummary: "运营日报依赖人工整理，跨部门数据口径不一致，管理层需要更快看到异常。",
    budgetRange: "8-15w",
    estimatedValue: "¥120,000",
    probability: 48,
    nextStep: "补一版数据源清单和权限边界，准备 proposal",
    updatedAt: "昨天 18:03",
    messages: [
      {
        id: "msg-4",
        senderType: "customer",
        senderLabel: "运营负责人",
        source: "lead_form",
        body: "老板经常问库存、异常订单、交付延误，但数据分散在 ERP 和 Excel，运营同事每天手工整理。",
        createdAt: "昨天 16:14",
      },
      {
        id: "msg-5",
        senderType: "owner",
        senderLabel: "Admin",
        source: "manual",
        body: "先不要承诺全量 BI，第一版只做三类高频经营问题。",
        createdAt: "昨天 17:02",
      },
    ],
  },
  {
    id: "opp-agent-saas",
    title: "销售跟进 Agent 工作流",
    stage: "negotiation",
    companyName: "北辰 SaaS 团队",
    ownerEmail: "founder@example.com",
    industry: "B2B SaaS",
    companySize: "20-50",
    contactName: "创始人",
    contactMethod: "wechat: founder",
    desiredOutcome: "减少销售顾问手动整理线索和跟进计划的时间",
    problemSummary: "线索质量参差不齐，销售跟进动作不稳定，管理者缺少可审计的跟进记录。",
    budgetRange: "5-10w",
    estimatedValue: "¥86,000",
    probability: 71,
    nextStep: "确认合同边界和首月交付节奏",
    updatedAt: "周一 14:36",
    messages: [
      {
        id: "msg-6",
        senderType: "customer",
        senderLabel: "创始人",
        source: "lead_form",
        body: "我们希望销售拿到客户需求后，系统能自动生成跟进计划、邮件草稿和内部备注。",
        createdAt: "周一 11:20",
      },
    ],
  },
  {
    id: "opp-support-finance",
    title: "财务制度问答助手",
    stage: "lead",
    companyName: "启明咨询集团",
    ownerEmail: "finance@example.com",
    industry: "专业服务",
    companySize: "100-200",
    contactName: "财务主管",
    contactMethod: "email",
    desiredOutcome: "员工能自助查询报销、合同和付款制度",
    problemSummary: "财务群每天重复回答制度问题，政策版本多，容易口径不一致。",
    budgetRange: "未确认",
    estimatedValue: "待估算",
    probability: 24,
    nextStep: "",
    updatedAt: "周日 20:11",
    messages: [
      {
        id: "msg-7",
        senderType: "customer",
        senderLabel: "财务主管",
        source: "lead_form",
        body: "想先试一个内部制度问答，不确定我们现在的文档是否足够。",
        createdAt: "周日 20:11",
      },
    ],
  },
];

export function getOpportunity(id: string) {
  return opportunities.find((item) => item.id === id) ?? opportunities[0];
}

export const stageLabels: Record<Stage, string> = {
  lead: "Lead",
  qualified: "Qualified",
  proposal: "Proposal",
  negotiation: "Negotiation",
  won: "Won",
  lost: "Lost",
  archived: "Archived",
};
