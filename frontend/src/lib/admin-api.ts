/* ── Admin API client for Agent OS backend ── */

const BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000/api/v1";
const ADMIN_TOKEN = process.env.NEXT_PUBLIC_ADMIN_TOKEN || "admin-dev-token";

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${ADMIN_TOKEN}`,
      ...init?.headers,
    },
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status}: ${body || res.statusText}`);
  }
  return res.json();
}

/* ── Types ── */

export type Stage = "lead" | "qualified" | "proposal" | "negotiation" | "won" | "lost" | "archived";

export type MessageSource = "lead_form" | "manual" | "agent_draft" | "system";
export type MessageSenderType = "customer" | "owner" | "agent" | "system";

export interface ContactOut {
  id: string;
  name: string | null;
  email: string | null;
  contact_method: string | null;
  is_primary: boolean;
}

export interface CustomerOut {
  id: string;
  name: string;
  owner_email: string;
  industry: string | null;
  company_size: string | null;
}

export interface ConversationMessage {
  id: string;
  sender_type: MessageSenderType;
  sender_label: string;
  body_markdown: string;
  source: string;
  created_at: string;
}

export interface AgentRunOut {
  id: string;
  agent_profile_id: string;
  status: string;
  input_json: Record<string, unknown> | null;
  output_json: Record<string, unknown> | null;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface ArtifactOut {
  id: string;
  agent_run_id: string | null;
  type: string;
  title: string;
  content_markdown: string | null;
  content_json: Record<string, unknown> | null;
  model: string;
  requires_approval: boolean;
  created_at: string;
}

export interface DecisionOut {
  id: string;
  agent_run_id: string | null;
  artifact_id: string | null;
  question: string;
  recommendation: string | null;
  status: string;
  operator_note: string | null;
  created_at: string;
  resolved_at: string | null;
}

export interface AuditLogOut {
  id: string;
  actor: string;
  action: string;
  details_json: Record<string, unknown> | null;
  created_at: string;
}

export interface OpportunityListItem {
  id: string;
  customer_id: string;
  lead_id: string | null;
  title: string;
  stage: Stage;
  desired_outcome: string | null;
  problem_summary: string | null;
  budget_range: string | null;
  estimated_value: number | null;
  probability: number | null;
  next_step: string | null;
  company_name: string;
  created_at: string;
  updated_at: string;
}

export interface OpportunityDetail {
  id: string;
  title: string;
  stage: Stage;
  desired_outcome: string | null;
  problem_summary: string | null;
  budget_range: string | null;
  estimated_value: number | null;
  probability: number | null;
  next_step: string | null;
  created_at: string;
  updated_at: string;
  customer: CustomerOut | null;
  primary_contact: ContactOut | null;
  conversation: { id: string; title: string; channel: string; status: string } | null;
  recent_messages: ConversationMessage[];
  agent_runs: AgentRunOut[];
  artifacts: ArtifactOut[];
  decisions: DecisionOut[];
  audit_logs: AuditLogOut[];
}

export interface SalesReplyResponse {
  agent_runs: AgentRunOut[];
  artifacts: ArtifactOut[];
  quality_review: {
    risk_level: "low" | "medium" | "high";
    risk_flags: Array<{ type: string; keyword?: string; detail?: string }>;
    summary: string;
    recommendation: string;
  };
  decision: { id: string; question: string; recommendation: string | null; status: string };
}

/* ── API functions ── */

export async function getOpportunities(params?: { stage?: string; q?: string }): Promise<{ items: OpportunityListItem[]; total: number }> {
  const sp = new URLSearchParams();
  if (params?.stage) sp.set("stage", params.stage);
  if (params?.q) sp.set("q", params.q);
  const qs = sp.toString();
  return api(`/admin/opportunities${qs ? `?${qs}` : ""}`);
}

export async function getOpportunityDetail(id: string): Promise<{ opportunity: OpportunityDetail }> {
  return api(`/admin/opportunities/${id}`);
}

export async function runSalesReplyAgent(opportunityId: string): Promise<SalesReplyResponse> {
  return api("/admin/agent-runs/sales-reply", {
    method: "POST",
    body: JSON.stringify({ opportunity_id: opportunityId }),
  });
}

export async function updateOpportunity(id: string, data: { stage?: string; next_step?: string }): Promise<void> {
  return api(`/admin/opportunities/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function approveDecision(decisionId: string, note?: string): Promise<{ decision: DecisionOut }> {
  return api(`/decisions/${decisionId}/approve`, {
    method: "POST",
    body: JSON.stringify({ operator_note: note || "" }),
  });
}

export async function requestRewrite(decisionId: string, note?: string): Promise<{ decision: DecisionOut }> {
  return api(`/decisions/${decisionId}/request-rewrite`, {
    method: "POST",
    body: JSON.stringify({ operator_note: note || "" }),
  });
}

export async function getCustomers(params?: { q?: string }): Promise<{ items: CustomerOut[]; total: number }> {
  const sp = new URLSearchParams();
  if (params?.q) sp.set("q", params.q);
  const qs = sp.toString();
  return api(`/admin/customers${qs ? `?${qs}` : ""}`);
}

/* ── Cockpit types ── */

export interface AdminOpportunityCockpit {
  opportunity: CockpitOpportunity;
  customer: CockpitCustomer | null;
  contact: CockpitContact | null;
  conversation: CockpitConversation | null;
  messages: CockpitMessage[];
  artifacts: CockpitArtifact[];
  decisions: CockpitDecision[];
  delivery_jobs: CockpitDeliveryJob[];
  audit_logs: CockpitAuditLog[];
  agent_runs: CockpitAgentRun[];
}

export interface CockpitOpportunity {
  id: string; customer_id: string; lead_id: string | null;
  primary_contact_id: string | null; conversation_id: string | null;
  title: string; stage: Stage; desired_outcome: string | null;
  problem_summary: string | null; budget_range: string | null;
  estimated_value: number | null; probability: number | null;
  next_step: string | null; created_at: string; updated_at: string;
}

export interface CockpitCustomer {
  id: string; name: string; owner_email: string;
  industry: string | null; company_size: string | null;
}

export interface CockpitContact {
  id: string; name: string | null; email: string | null;
  contact_method: string | null; is_primary: boolean;
}

export interface CockpitConversation {
  id: string; title: string; channel: string; status: string;
}

export interface CockpitMessage {
  id: string; sender_type: MessageSenderType; sender_label: string | null;
  body_markdown: string; source: string; created_at: string;
}

export interface CockpitArtifact {
  id: string; agent_run_id: string | null; type: string; title: string;
  content_markdown: string | null; content_json: Record<string, unknown> | null;
  model: string; requires_approval: boolean; created_at: string;
}

export interface CockpitDecision {
  id: string; agent_run_id: string | null; artifact_id: string | null;
  question: string; recommendation: string | null; status: string;
  operator_note: string | null; created_at: string; resolved_at: string | null;
}

export interface CockpitDeliveryJob {
  id: string; artifact_id: string; channel: string; recipient: string;
  subject: string; body_markdown: string; status: string;
  created_at: string; sent_at: string | null;
}

export interface CockpitAuditLog {
  id: string; actor: string; action: string;
  details_json: Record<string, unknown> | null; created_at: string;
}

export interface CockpitAgentRun {
  id: string; agent_profile_id: string; status: string;
  input_json: Record<string, unknown> | null;
  output_json: Record<string, unknown> | null;
  error_message: string | null;
  started_at: string | null; completed_at: string | null; created_at: string;
}

export async function getOpportunityCockpit(id: string): Promise<AdminOpportunityCockpit> {
  return api(`/admin/opportunities/${id}/cockpit`);
}

export type RecordCustomerReplyInput = {
  body_markdown: string;
  sender_label?: string;
};

export async function recordCustomerReply(
  opportunityId: string,
  input: RecordCustomerReplyInput,
): Promise<{ message: CockpitMessage; opportunity: CockpitOpportunity }> {
  return api(`/admin/opportunities/${opportunityId}/messages`, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export type ProposalDraftResponse = {
  agent_run: CockpitAgentRun;
  artifact: CockpitArtifact;
  decision: CockpitDecision;
};

export async function runProposalDraftAgent(
  opportunityId: string,
): Promise<ProposalDraftResponse> {
  return api("/admin/agent-runs/proposal-draft", {
    method: "POST",
    body: JSON.stringify({ opportunity_id: opportunityId }),
  });
}

export type ApprovedProposalData = {
  opportunity_id: string;
  artifact_id: string;
  decision_id: string;
  approved_at: string | null;
  title: string;
  markdown: string;
  customer_name: string;
  opportunity_title: string;
};

export async function getApprovedProposal(
  opportunityId: string,
): Promise<ApprovedProposalData> {
  return api(`/admin/opportunities/${opportunityId}/approved-proposal`);
}

export function getApprovedProposalPdfUrl(opportunityId: string): string {
  const base = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000/api/v1";
  const token = process.env.NEXT_PUBLIC_ADMIN_TOKEN || "admin-dev-token";
  return `${base}/admin/opportunities/${opportunityId}/approved-proposal.pdf?token=${token}`;
}

export async function markDeliveryJobSent(
  deliveryJobId: string,
  operatorNote?: string,
): Promise<{ delivery_job: CockpitDeliveryJob }> {
  return api(`/delivery-jobs/${deliveryJobId}/mark-sent`, {
    method: "POST",
    body: JSON.stringify({ operator_note: operatorNote || "" }),
  });
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
