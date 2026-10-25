// Thin client for the backend API. Every request carries the access code (if one is set) from localStorage.

import type {
  AppState, AuditEntry, Briefing, Conversation, Evidence, Notification, PendingAction, Reply, Scenario,
  Settings, StoredMessage, TraceEvent, TurnSummary, Watch,
} from "./types";

const BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? "";

export function accessCode(): string {
  try { return localStorage.getItem("gm.accessCode") ?? ""; } catch { return ""; }
}
export function setAccessCode(code: string): void {
  try { localStorage.setItem("gm.accessCode", code); } catch { /* private mode: keep in memory only */ }
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) { super(message); this.status = status; }
}

async function req<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(BASE + path, {
    ...init,
    headers: { "Content-Type": "application/json", "X-Access-Code": accessCode(), ...(init.headers ?? {}) },
  });
  if (!res.ok) {
    let detail = res.statusText;
    try { detail = (await res.json()).detail ?? detail; } catch { /* not JSON */ }
    throw new ApiError(res.status, String(detail));
  }
  return res.json() as Promise<T>;
}

const post = <T,>(path: string, body?: unknown) => req<T>(path, { method: "POST", body: JSON.stringify(body ?? {}) });

export const api = {
  state: () => req<AppState>("/api/state"),
  settings: () => req<Settings>("/api/settings"),
  patchSettings: (s: Partial<Settings>) => req<Settings>("/api/settings", { method: "PATCH", body: JSON.stringify(s) }),
  briefing: () => req<Briefing>("/api/briefing"),
  narrate: () => post<Briefing>("/api/briefing/narrate"),
  evidence: (id: string) => req<Evidence>(`/api/evidence/${id}`),
  proposals: () => req<PendingAction[]>("/api/proposals"),
  confirm: (id: string) => post<{ audit_id: string; summary: string }>(`/api/proposals/${id}/confirm`),
  cancel: (id: string) => post<{ status: string }>(`/api/proposals/${id}/cancel`),
  audit: () => req<AuditEntry[]>("/api/audit"),
  undo: (id: string) => post<{ summary: string }>(`/api/audit/${id}/undo`),
  outbox: () => req<any[]>("/api/outbox"),
  watches: () => req<Watch[]>("/api/watches"),
  notifications: () => req<Notification[]>("/api/notifications"),
  markRead: (ids?: number[]) => post("/api/notifications/read", { ids: ids ?? null }),
  advance: (days: number, hours = 0) => post<any>("/api/clock/advance", { days, hours }),
  setMode: (mode: "sim" | "real") => post<any>("/api/clock/mode", { mode }),
  reset: (scenario: string) => post<any>("/api/clock/reset", { scenario }),
  scenarios: () => req<Scenario[]>("/api/scenarios"),
  traces: () => req<TurnSummary[]>("/api/traces?limit=50"),
  trace: (turnId: string) => req<TraceEvent[]>(`/api/traces/${turnId}`),
  conversations: () => req<Conversation[]>("/api/conversations"),
  conversation: (id: string) => req<StoredMessage[]>(`/api/conversations/${id}`),
};

export interface StreamHandlers {
  onStep: (e: TraceEvent) => void;
  onReply: (r: Reply) => void;
  onError: (message: string, code?: string) => void;
}

/** POST /api/chat and read the Server-Sent Events stream (EventSource cannot POST). */
export async function chatStream(message: string, conversationId: string | null, h: StreamHandlers): Promise<void> {
  let res: Response;
  try {
    res = await fetch(BASE + "/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Access-Code": accessCode() },
      body: JSON.stringify({ message, conversation_id: conversationId }),
    });
  } catch {
    h.onError("Cannot reach the server. Is the backend running?");
    return;
  }
  if (!res.ok || !res.body) {
    let detail = res.statusText;
    try { detail = (await res.json()).detail ?? detail; } catch { /* ignore */ }
    h.onError(res.status === 401 ? "Access code required — set it in Settings." : String(detail), String(res.status));
    return;
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let idx: number;
    while ((idx = buffer.indexOf("\n\n")) >= 0) {
      const chunk = buffer.slice(0, idx);
      buffer = buffer.slice(idx + 2);
      const event = /^event: (.*)$/m.exec(chunk)?.[1];
      const data = /^data: (.*)$/m.exec(chunk)?.[1];
      if (!event || !data) continue;
      const payload = JSON.parse(data);
      if (event === "step") h.onStep(payload);
      else if (event === "reply") h.onReply(payload);
      else if (event === "error") h.onError(payload.message, payload.code);
    }
  }
}
