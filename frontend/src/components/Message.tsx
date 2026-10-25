import clsx from "clsx";
import { Check, Copy, ShieldCheck, Undo2, Volume2, X } from "lucide-react";
import { useState } from "react";
import { api } from "../api";
import type { Proposal, Reply, TraceEvent } from "../types";
import { Sparkle } from "./Sparkle";
import { Thinking } from "./Thinking";
import { Badge, Button, Chip, EvidenceChip, IconButton, Markdown } from "./ui";

export type ChatItem =
  | { id: string; role: "user"; text: string }
  | { id: string; role: "assistant"; running: boolean; steps: TraceEvent[]; reply?: Reply; error?: string };

const KIND_LABEL: Record<string, { label: string; tone: "neutral" | "good" | "warn" | "bad" | "accent" }> = {
  estimate: { label: "Estimate", tone: "accent" }, clarify: { label: "Needs your choice", tone: "accent" },
  refuse: { label: "Not in the data", tone: "warn" }, propose: { label: "Proposal", tone: "accent" },
  reject: { label: "Cannot do", tone: "bad" }, fallback: { label: "Unverified — raw tool output", tone: "warn" },
};

export function UserBubble({ text }: { text: string }) {
  return (
    <div className="flex justify-end">
      <div className="max-w-[85%] whitespace-pre-wrap rounded-3xl rounded-tr-md bg-surface-3 px-5 py-3 text-[15px] text-ink">
        {text}
      </div>
    </div>
  );
}

function ProposalCard({ p, onChanged }: { p: Proposal; onChanged: () => void }) {
  const [state, setState] = useState<{ status: string; audit?: string; msg?: string }>({ status: p.status });
  const [busy, setBusy] = useState(false);
  const act = async (fn: () => Promise<any>, next: (r: any) => typeof state) => {
    setBusy(true);
    try { setState(next(await fn())); onChanged(); } catch (e: any) { setState({ ...state, msg: e.message }); }
    finally { setBusy(false); }
  };
  return (
    <div className="mt-3 rounded-2xl border border-line bg-white p-4">
      <div className="mb-2 flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-ink-3">
        {p.kind.replace("_", " ")} · {p.action_id}
        {state.status === "pending" && <Badge tone="accent">pending</Badge>}
        {state.status === "executed" && <Badge tone="good">done</Badge>}
        {state.status === "cancelled" && <Badge>cancelled</Badge>}
        {state.status === "undone" && <Badge>undone</Badge>}
      </div>
      <p className="text-[15px] text-ink">{p.preview}</p>
      <div className="mt-3 flex flex-wrap gap-2">
        {state.status === "pending" && <>
          <Button variant="filled" disabled={busy}
            onClick={() => act(() => api.confirm(p.action_id), (r) => ({ status: "executed", audit: r.audit_id }))}>
            <Check size={16} /> Confirm
          </Button>
          <Button variant="outline" disabled={busy}
            onClick={() => act(() => api.cancel(p.action_id), () => ({ status: "cancelled" }))}>
            <X size={16} /> Cancel
          </Button>
        </>}
        {state.status === "executed" && state.audit && (
          <Button variant="text" disabled={busy}
            onClick={() => act(() => api.undo(state.audit!), () => ({ status: "undone" }))}>
            <Undo2 size={16} /> Undo
          </Button>
        )}
      </div>
      {state.msg && <p className="mt-2 text-sm text-bad">{state.msg}</p>}
    </div>
  );
}

export function AssistantMessage({ item, onSend, onEvidence, onChanged }: {
  item: Extract<ChatItem, { role: "assistant" }>; onSend: (t: string) => void; onEvidence: (id: string) => void;
  onChanged: () => void;
}) {
  const r = item.reply;
  const [copied, setCopied] = useState(false);
  const kind = r ? KIND_LABEL[r.kind] : undefined;
  const speak = () => {
    if (!r || !("speechSynthesis" in window)) return;
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(new SpeechSynthesisUtterance(r.headline));
  };
  const copy = async () => {
    if (!r) return;
    await navigator.clipboard.writeText([r.headline, r.details ?? ""].join("\n\n"));
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };
  return (
    <div className="flex gap-3 sm:gap-4">
      <div className="mt-0.5 shrink-0"><Sparkle size={26} spinning={item.running} /></div>
      <div className="min-w-0 flex-1">
        {(item.running || item.steps.length > 0) && <Thinking steps={item.steps} running={item.running} onEvidence={onEvidence} />}
        {item.error && <p className="rounded-2xl bg-bad-soft px-4 py-3 text-sm text-bad">{item.error}</p>}
        {r && (
          <div>
            {kind && <div className="mb-1.5"><Badge tone={kind.tone}>{kind.label}</Badge></div>}
            <p className={clsx("whitespace-pre-line text-[17px] leading-relaxed text-ink", r.kind !== "fallback" && "font-medium")}>
              {r.headline}
            </p>
            {r.details && <div className="mt-2"><Markdown>{r.details}</Markdown></div>}
            {r.clarification_question && r.kind === "clarify" && r.clarification_question !== r.headline &&
              <p className="mt-2 text-[15px] text-ink-2">{r.clarification_question}</p>}
            {r.options.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-2">
                {r.options.map((o) => <Chip key={o.value} onClick={() => onSend(o.value)}>{o.label}</Chip>)}
              </div>
            )}
            {r.proposals.map((p) => <ProposalCard key={p.action_id} p={p} onChanged={onChanged} />)}
            {r.evidence_ids.length > 0 && (
              <div className="mt-3 flex flex-wrap items-center gap-1.5 text-xs text-ink-3">
                Sources {r.evidence_ids.map((id) => <EvidenceChip key={id} id={id} onOpen={onEvidence} />)}
              </div>
            )}
            <div className="mt-2 flex flex-wrap items-center gap-1 text-xs text-ink-3">
              <IconButton label={copied ? "Copied" : "Copy"} onClick={copy} className="size-8">
                {copied ? <Check size={15} /> : <Copy size={15} />}
              </IconButton>
              <IconButton label="Read aloud" onClick={speak} className="size-8"><Volume2 size={15} /></IconButton>
              {r.grounded && r.kind !== "fallback" && (
                <span className="inline-flex items-center gap-1 text-good"><ShieldCheck size={14} /> verified against data</span>
              )}
              <span className="ml-1">
                · {r.tool_calls.length} tool call{r.tool_calls.length === 1 ? "" : "s"} · {r.latency_s}s
                {r.verifier_rejections > 0 && ` · ${r.verifier_rejections} draft${r.verifier_rejections > 1 ? "s" : ""} rejected`}
              </span>
            </div>
            {r.followups.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-2">
                {r.followups.map((f) => (
                  <button key={f} onClick={() => onSend(f)}
                    className="rounded-full border border-line px-3 py-1.5 text-sm text-ink-2 hover:bg-surface-2">{f}</button>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
