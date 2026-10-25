// Alerts, actions, watches and the "thinking" logs — the co-pilot's working memory, one click from the chat.

import clsx from "clsx";
import { BellRing, CheckCheck, Undo2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { api } from "../api";
import { Badge, Button, Empty, EvidenceChip, SectionTitle, fmtTime } from "../components/ui";
import type { AuditEntry, Notification, PendingAction, TraceEvent, TurnSummary, Watch } from "../types";

function useLoad<T>(fn: () => Promise<T>, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const load = useCallback(() => { fn().then(setData).catch((e) => setErr(e.message)); }, deps); // eslint-disable-line
  useEffect(load, [load]);
  return { data, err, load };
}

const Page = ({ children }: { children: React.ReactNode }) => (
  <div className="h-full overflow-y-auto"><div className="mx-auto max-w-3xl px-4 py-8 sm:px-6">{children}</div></div>
);

export function AlertsView({ onEvidence, onChanged }: { onEvidence: (id: string) => void; onChanged: () => void }) {
  const { data, err, load } = useLoad(api.notifications);
  const readAll = async () => { await api.markRead(); load(); onChanged(); };
  return (
    <Page>
      <SectionTitle right={<Button variant="outline" onClick={readAll}><CheckCheck size={16} /> Mark all read</Button>}>Alerts</SectionTitle>
      <p className="mb-4 text-sm text-ink-3">P1 interrupts are pushed (your own watches, severe drops at onset, large orders newly overdue). P2 waits for the briefing. A daily cap keeps interruptions rare.</p>
      {err && <p className="text-sm text-bad">{err}</p>}
      {data && data.length === 0 && <Empty>No alerts yet. Advance the clock to let new days arrive.</Empty>}
      <ul className="space-y-2">
        {data?.map((n: Notification) => (
          <li key={n.notification_id} className={clsx("rounded-2xl border p-4", n.read ? "border-line" : "border-accent/40 bg-accent-soft/30")}>
            <div className="mb-1 flex flex-wrap items-center gap-2">
              <Badge tone={n.priority === "P1" ? "bad" : "neutral"}>{n.priority}</Badge>
              <span className="font-medium text-ink">{n.title}</span>
              <span className="ml-auto text-xs text-ink-3">{fmtTime(n.created_at)}</span>
            </div>
            <p className="text-[15px] text-ink-2">{n.body}</p>
            {n.evidence_ids.length > 0 && <div className="mt-2 flex gap-1.5">{n.evidence_ids.map((e) => <EvidenceChip key={e} id={e} onOpen={onEvidence} />)}</div>}
          </li>
        ))}
      </ul>
    </Page>
  );
}

export function ActionsView({ onChanged }: { onChanged: () => void }) {
  const pending = useLoad(api.proposals);
  const audit = useLoad(api.audit);
  const outbox = useLoad(api.outbox);
  const refresh = () => { pending.load(); audit.load(); outbox.load(); onChanged(); };
  const run = async (fn: () => Promise<unknown>) => { try { await fn(); } finally { refresh(); } };
  return (
    <Page>
      <SectionTitle>Actions</SectionTitle>
      <p className="mb-4 text-sm text-ink-3">The co-pilot can only propose. Nothing happens until you confirm here or in the chat; every executed action is logged and can be undone.</p>
      <h3 className="mb-2 mt-6 text-sm font-medium uppercase tracking-wide text-ink-3">Awaiting your confirmation</h3>
      {pending.data?.length === 0 && <Empty>No proposals waiting.</Empty>}
      <ul className="space-y-2">
        {pending.data?.map((p: PendingAction) => (
          <li key={p.action_id} className="rounded-2xl border border-line p-4">
            <div className="mb-1 text-xs uppercase tracking-wide text-ink-3">{p.kind.replace("_", " ")} · {p.action_id} · {fmtTime(p.created_at)}</div>
            <p className="text-[15px] text-ink">{p.preview}</p>
            <div className="mt-3 flex gap-2">
              <Button variant="filled" onClick={() => run(() => api.confirm(p.action_id))}>Confirm</Button>
              <Button variant="outline" onClick={() => run(() => api.cancel(p.action_id))}>Cancel</Button>
            </div>
          </li>
        ))}
      </ul>
      <h3 className="mb-2 mt-8 text-sm font-medium uppercase tracking-wide text-ink-3">Audit log</h3>
      {audit.data?.length === 0 && <Empty>No actions executed yet.</Empty>}
      <ul className="divide-y divide-line rounded-2xl border border-line">
        {audit.data?.map((a: AuditEntry) => (
          <li key={a.audit_id} className="flex items-start gap-3 px-4 py-3">
            <div className="flex-1">
              <p className={clsx("text-[15px]", a.undone_at ? "text-ink-3 line-through" : "text-ink")}>{a.summary}</p>
              <p className="text-xs text-ink-3">{a.audit_id} · {fmtTime(a.executed_at)}{a.undone_at && ` · undone ${fmtTime(a.undone_at)}`}</p>
            </div>
            {!a.undone_at && <Button variant="text" onClick={() => run(() => api.undo(a.audit_id))}><Undo2 size={16} /> Undo</Button>}
          </li>
        ))}
      </ul>
      <h3 className="mb-2 mt-8 text-sm font-medium uppercase tracking-wide text-ink-3">Outbox (never sent to a real channel)</h3>
      {outbox.data?.length === 0 && <Empty>No messages.</Empty>}
      <ul className="space-y-2">
        {outbox.data?.map((m: any) => (
          <li key={m.message_id} className="rounded-2xl bg-surface-2 p-4 text-[15px]">
            <div className="mb-1 flex items-center gap-2 text-xs text-ink-3">To {m.recipient_role.replace("_", " ")} · {m.order_id} · {fmtTime(m.created_at)}
              <Badge tone={m.status === "retracted" ? "neutral" : "good"}>{m.status.replace("_", " ")}</Badge></div>
            <p className={clsx(m.status === "retracted" && "line-through text-ink-3")}>{m.body}</p>
          </li>
        ))}
      </ul>
    </Page>
  );
}

export function WatchesView() {
  const { data } = useLoad(api.watches);
  const tone = (s: string) => (s === "active" ? "accent" : s === "fired" ? "bad" : s === "satisfied" ? "good" : "neutral") as any;
  return (
    <Page>
      <SectionTitle>Watches</SectionTitle>
      <p className="mb-4 text-sm text-ink-3">Standing checks you asked for. They are evaluated on every tick of the clock and fire on their own.</p>
      {data?.length === 0 && <Empty>No watches. Try “Tell me if ORD-120 hasn't moved by Friday.”</Empty>}
      <ul className="space-y-2">
        {data?.map((w: Watch) => (
          <li key={w.watch_id} className="flex items-start gap-3 rounded-2xl border border-line p-4">
            <BellRing size={18} className="mt-0.5 text-ink-2" />
            <div className="flex-1">
              <p className="text-[15px] text-ink">{w.description}</p>
              <p className="text-xs text-ink-3">{w.watch_id} · set {fmtTime(w.created_at)} · expires {fmtTime(w.expires_at)}{w.fired_at && ` · fired ${fmtTime(w.fired_at)}`}</p>
            </div>
            <Badge tone={tone(w.status)}>{w.status}</Badge>
          </li>
        ))}
      </ul>
    </Page>
  );
}

const SYMBOL: Record<string, string> = { question: "▶", plan: "·", action: "·", llm: "·", draft: "·", verifier: "✓",
  critic: "·", repair: "↻", fallback: "!", reply: "■", error: "!" };

function line(e: TraceEvent): string {
  const d = e.data;
  if (e.kind === "question") return `"${d.text}"`;
  if (e.kind === "action") return `use tool ${d.tool} ${JSON.stringify(d.args)} → ${d.ok ? "ok" : "ERROR " + d.error_code} ${d.summary ?? ""}${d.evidence?.length ? " [" + d.evidence.join(", ") + "]" : ""} (${Math.round(d.ms)} ms)`;
  if (e.kind === "llm") return `${d.purpose} · ${d.model} · ${d.prompt ?? ""} · in ${d.input_tokens} (cached ${d.cached_tokens}) · out ${d.output_tokens} · $${(d.cost_usd ?? 0).toFixed(5)} · ${d.latency_ms} ms`;
  return d.message ?? JSON.stringify(d);
}

export function LogsView() {
  const { data } = useLoad(api.traces);
  const [sel, setSel] = useState<string | null>(null);
  const [events, setEvents] = useState<TraceEvent[] | null>(null);
  useEffect(() => { if (sel) api.trace(sel).then(setEvents); }, [sel]);
  return (
    <Page>
      <SectionTitle>Thinking logs</SectionTitle>
      <p className="mb-4 text-sm text-ink-3">Every AI execution, step by step: the plan, each tool call, the verifier's verdict, cost and latency. The same lines are written to the server console and to backend/var/logs.</p>
      {data?.length === 0 && <Empty>No turns yet.</Empty>}
      <ul className="divide-y divide-line rounded-2xl border border-line">
        {data?.map((t: TurnSummary) => (
          <li key={t.turn_id}>
            <button onClick={() => setSel(sel === t.turn_id ? null : t.turn_id)} className="flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-surface-2">
              <span className="flex-1 truncate text-[15px] text-ink">{t.first.text ?? t.turn_id}</span>
              <span className="shrink-0 text-xs text-ink-3">{t.steps} steps · {t.duration_s}s · {new Date(t.started * 1000).toLocaleTimeString()}</span>
            </button>
            {sel === t.turn_id && events && (
              <pre className="whitespace-pre-wrap break-all bg-[#1f1f1f] px-4 py-3 font-mono text-[12px] leading-relaxed text-[#e3e3e3]">
                {events.map((e) => `[turn ${t.turn_id.slice(0, 6)}] ${e.kind === "verifier" && !e.data.ok ? "✗" : SYMBOL[e.kind] ?? "·"} ${e.kind.padEnd(9)} ${line(e)}`).join("\n")}
              </pre>
            )}
          </li>
        ))}
      </ul>
    </Page>
  );
}
