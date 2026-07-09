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
  workspace_id?: string | null;
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
  workspace_id?: string | null;
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
  workspace_id?: string | null;
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

export async function recordProposalFeedback(
  opportunityId: string,
  input: RecordCustomerReplyInput,
): Promise<{ message: CockpitMessage; opportunity: CockpitOpportunity }> {
  return api(`/admin/opportunities/${opportunityId}/proposal-feedback`, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export async function runProposalFollowupAgent(
  opportunityId: string,
): Promise<ProposalDraftResponse> {
  return api("/admin/agent-runs/proposal-followup", {
    method: "POST",
    body: JSON.stringify({ opportunity_id: opportunityId }),
  });
}

export interface ApprovedQuoteSowData {
  opportunity_id: string; quote_artifact_id: string; sow_artifact_id: string;
  quote_markdown: string; sow_markdown: string; approved_at: string;
}

export async function getApprovedQuoteSow(id: string): Promise<ApprovedQuoteSowData> {
  return api(`/admin/opportunities/${id}/approved-quote-sow`);
}

export async function createApprovedQuoteSowDeliveryJob(
  opportunityId: string,
): Promise<{ delivery_job: CockpitDeliveryJob }> {
  return api(`/admin/opportunities/${opportunityId}/approved-quote-sow/delivery-job`, {
    method: "POST",
  });
}

export async function runQuoteSowAgent(
  opportunityId: string,
): Promise<ProposalDraftResponse> {
  return api("/admin/agent-runs/quote-sow", {
    method: "POST",
    body: JSON.stringify({ opportunity_id: opportunityId }),
  });
}

export async function createApprovedProposalDeliveryJob(
  opportunityId: string,
): Promise<{ delivery_job: CockpitDeliveryJob }> {
  return api(`/admin/opportunities/${opportunityId}/approved-proposal/delivery-job`, {
    method: "POST",
  });
}

export async function downloadApprovedProposalPdf(opportunityId: string): Promise<Blob> {
  const base = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000/api/v1";
  const token = process.env.NEXT_PUBLIC_ADMIN_TOKEN || "admin-dev-token";
  const res = await fetch(`${base}/admin/opportunities/${opportunityId}/approved-proposal.pdf`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status}: ${body || res.statusText}`);
  }
  return res.blob();
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

export interface WorkspaceOut {
  id: string; name: string; slug: string;
  industry: string | null; business_type: string | null;
  positioning: string | null; is_default: boolean;
  created_at: string; updated_at: string;
}

export async function getCurrentWorkspace(): Promise<WorkspaceOut> {
  return api("/admin/workspace/current");
}

export interface NotificationOut {
  id: string; kind: string; title: string; body: string | null;
  severity: string; status: string;
  target_type: string | null; target_id: string | null; target_url: string | null;
  created_at: string;
}

export interface NotificationSummaryOut {
  unread_count: number; critical_count: number;
  latest: NotificationOut[];
}

export async function getNotifications(params?: { status?: string; kind?: string; severity?: string }): Promise<{ items: NotificationOut[]; total: number }> {
  const sp = new URLSearchParams();
  if (params?.status) sp.set("status", params.status);
  if (params?.kind) sp.set("kind", params.kind);
  if (params?.severity) sp.set("severity", params.severity);
  const qs = sp.toString();
  return api(`/admin/notifications${qs ? `?${qs}` : ""}`);
}

export async function getNotificationSummary(): Promise<NotificationSummaryOut> {
  return api("/admin/notifications/summary");
}

export async function markNotificationRead(id: string): Promise<void> {
  await api(`/admin/notifications/${id}/read`, { method: "POST" });
}

export async function markAllNotificationsRead(): Promise<void> {
  await api("/admin/notifications/read-all", { method: "POST" });
}

export async function archiveNotification(id: string): Promise<void> {
  await api(`/admin/notifications/${id}/archive`, { method: "POST" });
}

export interface ServiceOut {
  id: string; workspace_id?: string | null; name: string; slug: string; status: string;
  positioning: string | null; target_customer: string | null;
  pain_points_json: Record<string, unknown> | null;
  outcomes_json: Record<string, unknown> | null;
  required_inputs_json: Record<string, unknown> | null;
  success_criteria_json: Record<string, unknown> | null;
  typical_duration: string | null; price_min: number | null; price_max: number | null;
  currency: string; risk_notes: string | null;
  created_at: string; updated_at: string;
}

export async function getServices(params?: { status?: string; q?: string }): Promise<{ items: ServiceOut[]; total: number }> {
  const sp = new URLSearchParams();
  if (params?.status) sp.set("status", params.status);
  if (params?.q) sp.set("q", params.q);
  const qs = sp.toString();
  return api(`/admin/services${qs ? `?${qs}` : ""}`);
}

export async function getService(id: string): Promise<ServiceOut> {
  return api(`/admin/services/${id}`);
}

export async function createService(input: Record<string, unknown>): Promise<ServiceOut> {
  return api("/admin/services", { method: "POST", body: JSON.stringify(input) });
}

export async function updateService(id: string, input: Record<string, unknown>): Promise<ServiceOut> {
  return api(`/admin/services/${id}`, { method: "PATCH", body: JSON.stringify(input) });
}

export async function deactivateService(id: string): Promise<ServiceOut> {
  return api(`/admin/services/${id}/deactivate`, { method: "POST" });
}

export async function activateService(id: string): Promise<ServiceOut> {
  return api(`/admin/services/${id}/activate`, { method: "POST" });
}

export async function archiveService(id: string): Promise<ServiceOut> {
  return api(`/admin/services/${id}/archive`, { method: "POST" });
}

export async function seedDefaultServices(): Promise<{ count: number }> {
  return api("/admin/services/seed-defaults", { method: "POST" });
}



export interface ServicePackageOut {
  id: string; service_id: string; workspace_id?: string | null; name: string;
  description: string | null; price_min: number | null; price_max: number | null;
  currency: string; duration: string | null; sort_order: number; is_active: boolean;
  created_at: string; updated_at: string;
}
export interface ServiceDeliverableOut {
  id: string; service_id: string; workspace_id?: string | null; package_id: string | null;
  title: string; description: string | null; format: string | null; sort_order: number;
  created_at: string; updated_at: string;
}
export interface ServiceRiskRuleOut {
  id: string; service_id: string; workspace_id?: string | null; title: string;
  description: string | null; severity: string; disqualifies: boolean;
  suggested_response: string | null; sort_order: number;
  created_at: string; updated_at: string;
}

export async function getServicePackages(serviceId: string): Promise<{ items: ServicePackageOut[] }> {
  return api(`/admin/services/${serviceId}/packages`);
}
export async function getServiceDeliverables(serviceId: string): Promise<{ items: ServiceDeliverableOut[] }> {
  return api(`/admin/services/${serviceId}/deliverables`);
}
export async function getServiceRiskRules(serviceId: string): Promise<{ items: ServiceRiskRuleOut[] }> {
  return api(`/admin/services/${serviceId}/risk-rules`);
}
export async function createServicePackage(serviceId: string, data: Record<string, unknown>): Promise<ServicePackageOut> {
  return api(`/admin/services/${serviceId}/packages`, { method: "POST", body: JSON.stringify(data) });
}
export async function updateServicePackage(serviceId: string, pkgId: string, data: Record<string, unknown>): Promise<ServicePackageOut> {
  return api(`/admin/services/${serviceId}/packages/${pkgId}`, { method: "PATCH", body: JSON.stringify(data) });
}
export async function deleteServicePackage(serviceId: string, pkgId: string): Promise<void> {
  await api(`/admin/services/${serviceId}/packages/${pkgId}`, { method: "DELETE" });
}
export async function createServiceDeliverable(serviceId: string, data: Record<string, unknown>): Promise<ServiceDeliverableOut> {
  return api(`/admin/services/${serviceId}/deliverables`, { method: "POST", body: JSON.stringify(data) });
}
export async function updateServiceDeliverable(serviceId: string, delId: string, data: Record<string, unknown>): Promise<ServiceDeliverableOut> {
  return api(`/admin/services/${serviceId}/deliverables/${delId}`, { method: "PATCH", body: JSON.stringify(data) });
}
export async function deleteServiceDeliverable(serviceId: string, delId: string): Promise<void> {
  await api(`/admin/services/${serviceId}/deliverables/${delId}`, { method: "DELETE" });
}
export async function createServiceRiskRule(serviceId: string, data: Record<string, unknown>): Promise<ServiceRiskRuleOut> {
  return api(`/admin/services/${serviceId}/risk-rules`, { method: "POST", body: JSON.stringify(data) });
}
export async function updateServiceRiskRule(serviceId: string, ruleId: string, data: Record<string, unknown>): Promise<ServiceRiskRuleOut> {
  return api(`/admin/services/${serviceId}/risk-rules/${ruleId}`, { method: "PATCH", body: JSON.stringify(data) });
}
export async function deleteServiceRiskRule(serviceId: string, ruleId: string): Promise<void> {
  await api(`/admin/services/${serviceId}/risk-rules/${ruleId}`, { method: "DELETE" });
}


/* ── Workspace Knowledge Engine (P3) ── */

export const KNOWLEDGE_SOURCE_TYPES = [
  "manual", "faq", "case_study", "methodology", "pricing_rule",
  "contract_boundary", "delivery_sop", "service_note", "external_doc",
] as const;
export type KnowledgeSourceType = (typeof KNOWLEDGE_SOURCE_TYPES)[number];
export type KnowledgeStatus = "draft" | "active" | "archived";

export interface KnowledgeSourceOut {
  id: string; workspace_id?: string | null; name: string;
  description: string | null; created_at: string; updated_at: string;
}

export interface KnowledgeItemOut {
  id: string; workspace_id?: string | null;
  source_id: string | null; service_id: string | null;
  title: string; summary: string | null; content_markdown: string;
  source_type: string; tags_json: string[]; status: string;
  visibility: string; confidence: number | null;
  metadata_json: Record<string, unknown> | null;
  archived_at: string | null; created_at: string; updated_at: string;
}

export interface KnowledgeItemInput {
  title: string; content_markdown: string; summary?: string | null;
  source_type?: string; source_id?: string | null; service_id?: string | null;
  tags_json?: string[]; status?: string; visibility?: string;
  confidence?: number | null;
}

export async function getKnowledgeItems(params?: {
  q?: string; status?: string; source_type?: string; tag?: string; service_id?: string;
}): Promise<{ items: KnowledgeItemOut[]; total: number }> {
  const sp = new URLSearchParams();
  if (params?.q) sp.set("q", params.q);
  if (params?.status) sp.set("status", params.status);
  if (params?.source_type) sp.set("source_type", params.source_type);
  if (params?.tag) sp.set("tag", params.tag);
  if (params?.service_id) sp.set("service_id", params.service_id);
  const qs = sp.toString();
  return api(`/admin/knowledge${qs ? `?${qs}` : ""}`);
}

export async function getKnowledgeItem(id: string): Promise<KnowledgeItemOut> {
  return api(`/admin/knowledge/${id}`);
}

export async function createKnowledgeItem(data: KnowledgeItemInput): Promise<KnowledgeItemOut> {
  return api("/admin/knowledge", { method: "POST", body: JSON.stringify(data) });
}

export async function updateKnowledgeItem(id: string, data: Partial<KnowledgeItemInput>): Promise<KnowledgeItemOut> {
  return api(`/admin/knowledge/${id}`, { method: "PATCH", body: JSON.stringify(data) });
}

export async function archiveKnowledgeItem(id: string): Promise<KnowledgeItemOut> {
  return api(`/admin/knowledge/${id}/archive`, { method: "POST" });
}

export async function getKnowledgeSources(): Promise<{ items: KnowledgeSourceOut[] }> {
  return api("/admin/knowledge/sources");
}

export async function createKnowledgeSource(data: { name: string; description?: string | null }): Promise<KnowledgeSourceOut> {
  return api("/admin/knowledge/sources", { method: "POST", body: JSON.stringify(data) });
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
