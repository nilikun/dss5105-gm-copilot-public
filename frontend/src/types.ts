// Shapes returned by the FastAPI backend (backend/app/api).

export type ReplyKind = "answer" | "estimate" | "clarify" | "refuse" | "propose" | "reject" | "fallback";

export interface Option { label: string; value: string }

export interface Proposal { action_id: string; kind: string; preview: string; status: string }

export interface ToolCall { tool: string; args: Record<string, unknown>; ok: boolean; ms: number; error: string | null;
  summary: string; evidence: string[] }

export interface Reply {
  turn_id: string; conversation_id: string; kind: ReplyKind; headline: string; details: string | null;
  evidence_ids: string[]; clarification_question: string | null; options: Option[]; proposals: Proposal[];
  followups: string[]; grounded: boolean; verifier_rejections: number; critic: { verdict: string; issues: string[] } | null;
  llm_calls: number; cost_usd: number; latency_s: number; tool_calls: ToolCall[];
}

export interface TraceEvent { turn_id?: string; seq: number; ts: number; clock_time: string; kind: string;
  data: Record<string, any> }

export interface Usage { day_utc: string; calls: number; cost_usd: number; input_tokens: number; output_tokens: number;
  daily_budget_usd: number; remaining_usd: number }

export interface Settings { critic_enabled: boolean; interrupt_cap: number; model: string; reasoning_effort: string;
  daily_budget_usd: number }

export interface AppState { now: string; mode: "sim" | "real"; scenario: string; data_through: string;
  unread_alerts: number; unread_p1: number; pending_actions: number; active_watches: number; usage: Usage;
  settings: Settings }

export interface BriefingItem { type: string; text: string; evidence_id?: string; score?: number; action_id?: string }

export interface Briefing {
  date: string; created_at: string; narrative: string | null; narrative_status: string; narrative_note: string;
  structured: { date: string; generated_at: string; data_through: string; yesterday: BriefingItem[];
    at_risk: BriefingItem[]; decisions: BriefingItem[]; suppressed_findings: number; evidence_ids: string[] };
}

export interface Evidence { evidence_id: string; source: string; keys: string[]; description: string;
  rows: Record<string, any>[]; as_of: string; turn_id: string | null }

export interface Notification { notification_id: number; created_at: string; priority: "P1" | "P2"; kind: string;
  title: string; body: string; evidence_ids: string[]; read: number }

export interface Watch { watch_id: string; type: string; description: string; priority: string; created_at: string;
  expires_at: string; status: string; fired_at: string | null; params: Record<string, any> }

export interface AuditEntry { audit_id: string; action_id: string; kind: string; executed_at: string; summary: string;
  undone_at: string | null }

export interface PendingAction { action_id: string; kind: string; preview: string; status: string; created_at: string }

export interface Scenario { name: string; title: string; description: string }

export interface TurnSummary { turn_id: string; started: number; duration_s: number; steps: number;
  first: Record<string, any>; last: Record<string, any> }

export interface Conversation { conversation_id: string; created_at: number; title: string }

export interface StoredMessage { role: "user" | "assistant"; content: any; turn_id: string; created_at: number }
