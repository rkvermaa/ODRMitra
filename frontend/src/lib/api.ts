const API_BASE = "/api/v1";

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token =
    typeof window !== "undefined" ? localStorage.getItem("token") : null;

  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  // Don't set content-type for FormData (browser sets it with boundary)
  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || body.error || `Request failed: ${res.status}`);
  }

  return res.json();
}

// ─── Auth ────────────────────────────────────────────
export interface LoginResponse {
  access_token: string;
  token_type: string;
  user_id: string;
  name: string;
  role: string;
}

export interface UserProfile {
  id: string;
  mobile_number: string;
  name: string;
  email: string | null;
  role: string;
  organization_name: string | null;
  udyam_registration: string | null;
}

export function login(mobile_number: string) {
  return request<LoginResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ mobile_number }),
  });
}

export function loginWithUdyam(udyam_registration: string) {
  return request<LoginResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ udyam_registration }),
  });
}

export function getMe() {
  return request<UserProfile>("/auth/me");
}

// ─── Disputes ────────────────────────────────────────
export interface Dispute {
  id: string;
  case_number: string;
  title: string;
  description: string | null;
  category: string;
  sub_category: string | null;
  status: string;
  respondent_name: string | null;
  respondent_mobile: string | null;
  respondent_email: string | null;
  respondent_category: string | null;
  respondent_pan: string | null;
  respondent_gstin: string | null;
  respondent_state: string | null;
  respondent_district: string | null;
  respondent_pin_code: string | null;
  respondent_address: string | null;
  claimed_amount: number | null;
  invoice_amount: number | null;
  amount_received: number | null;
  principal_amount: number | null;
  interest_rate: number | null;
  interest_amount: number | null;
  total_amount_due: number | null;
  po_number: string | null;
  po_date: string | null;
  payment_terms: string | null;
  goods_services_description: string | null;
  cause_of_action: string | null;
  relief_sought: string | null;
  msefc_council: string | null;
  ai_classification: Record<string, unknown> | null;
  ai_missing_docs: Record<string, unknown> | null;
  ai_outcome_prediction: Record<string, unknown> | null;
  claimant_id: string;
  respondent_id: string | null;
  created_at: string;
  updated_at: string;
}

export function listDisputes() {
  return request<Dispute[]>("/disputes");
}

export function getDispute(id: string) {
  return request<Dispute>(`/disputes/${id}`);
}

export function createDispute(data: Record<string, unknown>) {
  return request<Dispute>("/disputes", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function updateDispute(id: string, data: Record<string, unknown>) {
  return request<Dispute>(`/disputes/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

// ─── Documents ───────────────────────────────────────
export interface Document {
  id: string;
  dispute_id: string;
  filename: string;
  original_filename: string;
  doc_type: string;
  file_url: string;
  file_size: number;
  analysis_status: string;
  analysis_result: Record<string, unknown> | null;
  extracted_amount: number | null;
  created_at: string;
}

export function listDocuments(disputeId: string) {
  return request<Document[]>(`/disputes/${disputeId}/documents`);
}

export function uploadDocument(
  disputeId: string,
  file: File,
  docType: string
) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("doc_type", docType);
  return request<Document>(`/disputes/${disputeId}/documents`, {
    method: "POST",
    body: formData,
  });
}

// ─── Chat ────────────────────────────────────────────
export interface ChatResponse {
  response: string;
  session_id: string;
  usage: Record<string, number>;
  tool_calls_made: Array<Record<string, unknown>>;
}

export function sendMessage(
  message: string,
  sessionId?: string,
  disputeId?: string,
  channel: string = "web"
) {
  return request<ChatResponse>("/chat/message", {
    method: "POST",
    body: JSON.stringify({
      message,
      session_id: sessionId,
      dispute_id: disputeId,
      channel,
    }),
  });
}

export interface ChatSession {
  id: string;
  dispute_id: string | null;
  channel: string;
  session_type: string;
  status: string;
  created_at: string;
  last_message_at: string | null;
}

export function listSessions(disputeId?: string) {
  const qs = disputeId ? `?dispute_id=${disputeId}` : "";
  return request<{ total: number; sessions: ChatSession[] }>(
    `/chat/sessions${qs}`
  );
}

export interface ChatMessage {
  id: string;
  role: string;
  content: string;
  tool_name: string | null;
  created_at: string;
}

export function getSessionMessages(sessionId: string) {
  return request<{ session_id: string; messages: ChatMessage[] }>(
    `/chat/sessions/${sessionId}/messages`
  );
}

// ─── Handoff (Voice → WhatsApp) ──────────────────────
export function handoffToWhatsApp(
  collectedFields: Record<string, string>,
  sessionId?: string,
  transcript?: { role: string; content: string }[]
) {
  return request<{ dispute_id: string; case_number: string }>("/chat/handoff", {
    method: "POST",
    body: JSON.stringify({
      collected_fields: collectedFields,
      session_id: sessionId,
      transcript: transcript,
    }),
  });
}

// ─── WhatsApp ────────────────────────────────────────
export interface WhatsAppStatus {
  status: string;
  connected: boolean;
  phone_number: string | null;
  qr_code: string | null;
}

export function connectWhatsApp() {
  return request<WhatsAppStatus>("/channel/whatsapp/connect", {
    method: "POST",
  });
}

export function getWhatsAppStatus() {
  return request<WhatsAppStatus>("/channel/whatsapp/status");
}

export function disconnectWhatsApp() {
  return request<{ success: boolean }>("/channel/whatsapp/disconnect", {
    method: "POST",
  });
}

export function sendWhatsAppMessage(to: string, message: string) {
  return request<{ success: boolean }>("/channel/whatsapp/send", {
    method: "POST",
    body: JSON.stringify({ to, message }),
  });
}

// ─── Admin ──────────────────────────────────────────

export interface AdminBot {
  id: string;
  label: string | null;
  phone_number: string | null;
  status: string;
  created_at: string | null;
}

export interface ConnectBotResponse {
  bot_id: string;
  connected: boolean;
  phone_number: string | null;
  qr_code: string | null;
}

export interface BotNumber {
  phone_number: string;
  label: string | null;
}

export function adminListBots() {
  return request<AdminBot[]>("/admin/bots");
}

export function adminConnectBot() {
  return request<ConnectBotResponse>("/admin/bots", { method: "POST" });
}

export function adminGetBotStatus(botId: string) {
  return request<{ connected: boolean; phone_number: string | null; status: string; qr_code: string | null }>(
    `/admin/bots/${botId}/status`
  );
}

export function adminDisconnectBot(botId: string) {
  return request<{ success: boolean }>(`/admin/bots/${botId}/disconnect`, {
    method: "POST",
  });
}

export function adminResetBot(botId: string) {
  return request<{ success: boolean }>(`/admin/bots/${botId}/reset`, {
    method: "POST",
  });
}

export function adminListCases() {
  return request<Dispute[]>("/admin/cases");
}

export function getBotNumbers() {
  return request<BotNumber[]>("/admin/bot-numbers");
}

// ─── Admin Knowledge Base ────────────────────────────

export interface KnowledgeDoc {
  id: string;
  filename: string;
  original_filename: string;
  file_url: string;
  file_size: number;
  doc_category: string;
  description: string | null;
  index_status: string;
  index_error: string | null;
  chunk_count: number;
  uploaded_by: string;
  created_at: string;
  updated_at: string;
}

export interface KnowledgeStats {
  total_documents: number;
  indexed_documents: number;
  failed_documents: number;
  pending_documents: number;
  total_chunks: number;
  legal_collection: Record<string, unknown>;
  case_docs_collection: Record<string, unknown>;
}

export function adminListKnowledgeDocs() {
  return request<KnowledgeDoc[]>("/admin/knowledge-base");
}

export function adminUploadKnowledgeDoc(
  file: File,
  category: string,
  description: string
) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("doc_category", category);
  formData.append("description", description);
  return request<KnowledgeDoc>("/admin/knowledge-base/upload", {
    method: "POST",
    body: formData,
  });
}

export function adminDeleteKnowledgeDoc(docId: string) {
  return request<{ success: boolean }>(`/admin/knowledge-base/${docId}`, {
    method: "DELETE",
  });
}

export function adminReindexKnowledgeDoc(docId: string) {
  return request<{ success: boolean }>(`/admin/knowledge-base/${docId}/reindex`, {
    method: "POST",
  });
}

export function adminGetKnowledgeStats() {
  return request<KnowledgeStats>("/admin/knowledge-base/stats");
}
