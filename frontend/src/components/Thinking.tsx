import clsx from "clsx";
import { AlertTriangle, Brain, CheckCircle2, ChevronDown, LayoutList, PenLine, RotateCcw, ShieldCheck, Wrench, XCircle } from "lucide-react";
import { useState } from "react";
import type { TraceEvent } from "../types";
import { EvidenceChip } from "./ui";

const SHOWN = new Set(["plan", "action", "draft", "render", "status_contract", "verifier", "repair", "critic", "fallback"]);

function short(v: unknown, n = 90): string {
  const s = typeof v === "string" ? v : JSON.stringify(v);
  return s.length > n ? s.slice(0, n - 1) + "…" : s;
}

function Step({ e, onEvidence }: { e: TraceEvent; onEvidence: (id: string) => void }) {
  const d = e.data;
  const row = (icon: React.ReactNode, body: React.ReactNode, tone = "text-ink-2") => (
    <li className={clsx("flex gap-2.5 py-1 text-[13.5px] leading-snug", tone)}>
      <span className="mt-0.5 shrink-0">{icon}</span>
      <span className="min-w-0">{body}</span>
    </li>
  );
  switch (e.kind) {
    case "plan":
      return row(<Brain size={15} />, <><span className="font-medium text-ink">Plan</span> · {d.message}</>);
    case "action":
      return row(<Wrench size={15} />, <>
        <span className="font-medium text-ink">Use tool</span>{" "}
        <code className="font-mono text-[12.5px]">{d.tool}</code>{" "}
        <span className="font-mono text-[12px] text-ink-3">{short(d.args)}</span>{" "}
        → {d.ok ? <span className="text-good">ok</span> : <span className="text-bad">{d.error_code}</span>}
        {d.summary ? <span className="text-ink-3"> · {short(d.summary, 80)}</span> : null}
        {(d.evidence ?? []).map((id: string) => <span key={id} className="ml-1"><EvidenceChip id={id} onOpen={onEvidence} /></span>)}
        <span className="text-ink-3"> · {Math.round(d.ms ?? 0)} ms</span>
      </>);
    case "draft":
      return row(<PenLine size={15} />, <><span className="font-medium text-ink">Draft</span> · {short(d.headline, 140)}</>);
    case "render":
    case "status_contract":
      return row(<LayoutList size={15} />, <><span className="font-medium text-ink">Formatted</span> · {d.message}</>);
    case "verifier":
      return d.ok
        ? row(<CheckCircle2 size={15} className="text-good" />, <><span className="font-medium text-ink">Verified</span> · {d.checked} facts traced to tool outputs</>)
        : row(<XCircle size={15} className="text-bad" />, <><span className="font-medium text-ink">Rejected by verifier</span> · {short(d.message, 200)}</>);
    case "repair":
      return row(<RotateCcw size={15} />, <><span className="font-medium text-ink">Revising</span> · {d.message}</>);
    case "critic":
      return row(<ShieldCheck size={15} />, <><span className="font-medium text-ink">Reviewer</span> · {d.verdict}{d.issues?.length ? `: ${d.issues.join("; ")}` : ""}</>);
    case "fallback":
      return row(<AlertTriangle size={15} className="text-warn" />, <><span className="font-medium text-ink">No verified answer</span> · {short(d.message, 200)}</>);
    default:
      return null;
  }
}

export function Thinking({ steps, running, onEvidence }: { steps: TraceEvent[]; running: boolean;
  onEvidence: (id: string) => void }) {
  const [open, setOpen] = useState(false);
  const visible = steps.filter((s) => SHOWN.has(s.kind));
  const last = visible[visible.length - 1];
  const label = running ? (last ? lastLabel(last) : "Thinking") : "Show thinking";
  return (
    <div className="mb-2">
      <button onClick={() => setOpen((o) => !o)} aria-expanded={open}
        className="inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-sm text-ink-2 hover:bg-surface-2">
        <span className={clsx(running && "gem-shimmer font-medium")}>{label}</span>
        <ChevronDown size={16} className={clsx("transition-transform", open && "rotate-180")} />
      </button>
      {open && visible.length > 0 && (
        <ol className="ml-3 mt-1 border-l-2 border-line pl-4">
          {visible.map((e) => <Step key={e.seq} e={e} onEvidence={onEvidence} />)}
        </ol>
      )}
    </div>
  );
}

function lastLabel(e: TraceEvent): string {
  if (e.kind === "action") return `Checking ${e.data.tool?.replaceAll("_", " ")}…`;
  if (e.kind === "verifier") return e.data.ok ? "Verified · finishing…" : "Fixing an unsupported figure…";
  if (e.kind === "draft") return "Verifying the answer…";
  if (e.kind === "critic") return "Reviewing…";
  return "Thinking…";
}
